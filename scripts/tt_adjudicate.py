# scripts/tt_adjudicate.py
"""The only model-calling step. Annotates unresolved forms (Stage A) and pending links (Stage B).

Usage:
  python scripts/tt_adjudicate.py lemmas --book deuteronomy [--model claude-opus-5-5] [--dry-run]
  python scripts/tt_adjudicate.py links  [--model claude-opus-5-5] [--dry-run]
  python scripts/tt_adjudicate.py gold --sample data/tt/gold/sample_refs.json   # model as second reader

Every accepted annotation is written with source="model". Rejected items are left as they were.
Requires ANTHROPIC_API_KEY (loaded from .env by python-dotenv). --dry-run prints prompts and exits.
"""
import argparse
import csv
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv  # noqa: E402
from translation_technique.adjudicate import (  # noqa: E402
    AnthropicAnnotator, lemma_prompt, link_prompt, merge_lemma_annotations, merge_link_annotations,
    parse_lemma_response, parse_link_response,
)
from translation_technique.align import book_stem  # noqa: E402
from translation_technique.lemmas import read_jsonl, write_jsonl  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TT_DIR = os.path.join(ROOT, 'data', 'tt')
BATCH = 50


def _verse_texts(stem: str) -> dict:
    out = defaultdict(list)
    with open(os.path.join(ROOT, 'data', 'corpora', 'pesh_etcbc', f'{stem}.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            out[r['reference']].append(r['word_text'])
    return {k: ' '.join(v) for k, v in out.items()}


def run_lemmas(stem: str, client, dry: bool) -> None:
    path = os.path.join(TT_DIR, 'lemmas', f'{stem}.jsonl')
    rows = read_jsonl(path)
    texts = _verse_texts(stem)
    seen, batch_items = set(), []
    for r in rows:
        if r['source'] == 'unresolved' and r['norm'] not in seen:
            seen.add(r['norm'])
            batch_items.append({'norm': r['norm'], 'ref': r['ref'], 'verse_text': texts.get(r['ref'], '')})
    total = 0
    for i in range(0, len(batch_items), BATCH):
        batch = batch_items[i:i + BATCH]
        prompt = lemma_prompt(batch)
        if dry:
            print(prompt[:1500]); return
        accepted = parse_lemma_response(client.complete(prompt), batch)
        total += merge_lemma_annotations(rows, accepted)
        print(f'batch {i // BATCH + 1}: accepted {len(accepted)}/{len(batch)}')
    write_jsonl(path, rows)
    print(f'{stem}: {total} tokens annotated by model')


def run_links(client, dry: bool) -> None:
    pend = json.load(open(os.path.join(TT_DIR, 'align', 'pending.json'), encoding='utf-8'))
    if not pend:
        print('no pending links'); return
    by_book = defaultdict(list)
    for p in pend:
        by_book[book_stem(p['ref'])].append(p)
    for stem, items in by_book.items():
        lemmas = read_jsonl(os.path.join(TT_DIR, 'lemmas', f'{stem}.jsonl'))
        toks = defaultdict(list)
        lookup = {}
        for l in lemmas:
            toks[l['ref']].append({'position': l['position'], 'form': l['form']})
            lookup[(l['ref'], l['position'])] = (l['lemma'], l['source'])
        batch_items = [{'ref': p['ref'], 'heb_node': p['heb_node'], 'heb_word': p['heb_word'], 'heb_lex': p['heb_lex'],
                        'heb_gloss': p['heb_gloss'], 'syr_tokens': toks[p['ref']]} for p in items]
        apath = os.path.join(TT_DIR, 'align', f'{stem}.jsonl')
        rows = read_jsonl(apath)
        total = 0
        for i in range(0, len(batch_items), BATCH):
            batch = batch_items[i:i + BATCH]
            prompt = link_prompt(batch)
            if dry:
                print(prompt[:1500]); return
            accepted = parse_link_response(client.complete(prompt), batch)
            total += merge_link_annotations(rows, accepted, lookup)
        write_jsonl(apath, rows)
        print(f'{stem}: {total} links adjudicated by model')
    _update_manifest(client.model_id)


def _update_manifest(model_id: str) -> None:
    import hashlib
    mpath = os.path.join(TT_DIR, 'align', 'manifest.json')
    m = json.load(open(mpath, encoding='utf-8'))
    h, model_links = hashlib.sha256(), 0
    for stem in m['books']:
        path = os.path.join(TT_DIR, 'align', f'{stem}.jsonl')
        h.update(open(path, 'rb').read())
        model_links += sum(1 for r in read_jsonl(path) if r['source'] == 'model')
    m.update(model_id=model_id, model_links=model_links, hash=h.hexdigest())
    json.dump(m, open(mpath, 'w', encoding='utf-8'), indent=1)


def run_gold(sample_path: str, client, dry: bool) -> None:
    """Model as second reader: align the sample verses, write reader="model" rows."""
    refs = json.load(open(sample_path, encoding='utf-8'))
    stem = 'deuteronomy'
    lemmas = read_jsonl(os.path.join(TT_DIR, 'lemmas', f'{stem}.jsonl'))
    align = read_jsonl(os.path.join(TT_DIR, 'align', f'{stem}.jsonl'))
    toks, lookup = defaultdict(list), {}
    for l in lemmas:
        toks[l['ref']].append({'position': l['position'], 'form': l['form']})
        lookup[(l['ref'], l['position'])] = (l['lemma'], l['source'])
    heb = defaultdict(list)
    for r in align:
        if r['heb_node'] is not None and r['ref'] in refs:
            heb[r['ref']].append(r)
    items = [{'ref': ref, 'heb_node': r['heb_node'], 'heb_word': r['heb_word'], 'heb_lex': r['heb_lex'],
              'heb_gloss': r['heb_gloss'], 'syr_tokens': toks[ref]}
             for ref in refs for r in {x['heb_node']: x for x in heb[ref]}.values()]
    out = []
    for i in range(0, len(items), BATCH):
        batch = items[i:i + BATCH]
        prompt = link_prompt(batch)
        if dry:
            print(prompt[:1500]); return
        for a in parse_link_response(client.complete(prompt), batch):
            src = next(b for b in batch if b['heb_node'] == a['heb_node'])
            lemma = lookup.get((a['ref'], a['syr_position']), (None, None))[0] if a['syr_position'] else None
            out.append({'ref': a['ref'], 'heb_node': a['heb_node'], 'heb_lex': src['heb_lex'], 'heb_word': src['heb_word'],
                        'heb_gloss': src['heb_gloss'], 'heb_feats': None, 'syr_position': a['syr_position'],
                        'syr_lemma': lemma, 'syr_source': None, 'kind': 'one-one' if a['syr_position'] else 'null',
                        'reader': 'model', 'agreed': None})
    gpath = os.path.join(TT_DIR, 'gold', 'deuteronomy_sample.jsonl')
    existing = [r for r in (read_jsonl(gpath) if os.path.exists(gpath) else []) if r['reader'] != 'model']
    write_jsonl(gpath, existing + out)
    print(f'gold: wrote {len(out)} model-reader rows')


def main() -> None:
    load_dotenv(os.path.join(ROOT, '.env'))
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['lemmas', 'links', 'gold'])
    ap.add_argument('--book', default='deuteronomy')
    ap.add_argument('--model', default='claude-opus-5-5')
    ap.add_argument('--sample', default=os.path.join(TT_DIR, 'gold', 'sample_refs.json'))
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()
    client = None if args.dry_run else AnthropicAnnotator(args.model)
    if args.mode == 'lemmas':
        run_lemmas(args.book, client, args.dry_run)
    elif args.mode == 'links':
        run_links(client, args.dry_run)
    else:
        run_gold(args.sample, client, args.dry_run)


if __name__ == '__main__':
    main()
