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
from translation_technique.align import book_stem, manifest_hash  # noqa: E402
from translation_technique.lemmas import read_jsonl, write_jsonl  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TT_DIR = os.path.join(ROOT, 'data', 'tt')
BATCH = 50
LEMMA_BATCH = 25


def _complete(client, prompt: str, label: str) -> str:
    text, stop = client.complete(prompt)
    if stop == 'max_tokens':
        print(f'WARNING: {label} hit max_tokens; response may be truncated')
    return text


def _verse_texts(stem: str) -> dict:
    out = defaultdict(list)
    with open(os.path.join(ROOT, 'data', 'corpora', 'pesh_etcbc', f'{stem}.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            out[r['reference']].append(r['word_text'])
    return {k: ' '.join(v) for k, v in out.items()}


def run_lemmas(stem: str, client, dry: bool, max_batches=None) -> dict:
    path = os.path.join(TT_DIR, 'lemmas', f'{stem}.jsonl')
    rows = read_jsonl(path)
    texts = _verse_texts(stem)
    seen, batch_items = set(), []
    for r in rows:
        if r['source'] == 'unresolved' and r['norm'] not in seen:
            seen.add(r['norm'])
            batch_items.append({'norm': r['norm'], 'ref': r['ref'], 'verse_text': texts.get(r['ref'], '')})
    total, stats = 0, {'batches': 0, 'accepted': 0}
    for i in range(0, len(batch_items), LEMMA_BATCH):
        if max_batches is not None and stats['batches'] >= max_batches:
            break
        batch = batch_items[i:i + LEMMA_BATCH]
        prompt = lemma_prompt(batch)
        if dry:
            print(prompt[:1500]); return stats
        label = f'lemma batch {i // LEMMA_BATCH + 1}'
        accepted = parse_lemma_response(_complete(client, prompt, label), batch)
        total += merge_lemma_annotations(rows, accepted)
        write_jsonl(path, rows)  # checkpoint
        stats['batches'] += 1
        stats['accepted'] += len(accepted)
        print(f'{label}: accepted {len(accepted)}/{len(batch)}')
    print(f'{stem}: {total} tokens annotated by model')
    return stats


def run_links(client, dry: bool, max_batches=None) -> dict:
    with open(os.path.join(TT_DIR, 'align', 'pending.json'), encoding='utf-8') as fh:
        pend = json.load(fh)
    stats = {'batches': 0, 'accepted': 0}
    if not pend:
        print('no pending links'); return stats
    by_book = defaultdict(list)
    for p in pend:
        by_book[book_stem(p['ref'])].append(p)
    for stem, items in by_book.items():
        if max_batches is not None and stats['batches'] >= max_batches:
            break
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
            if max_batches is not None and stats['batches'] >= max_batches:
                break
            batch = batch_items[i:i + BATCH]
            prompt = link_prompt(batch)
            if dry:
                print(prompt[:1500]); return stats
            label = f'{stem} link batch {i // BATCH + 1}'
            accepted = parse_link_response(_complete(client, prompt, label), batch)
            total += merge_link_annotations(rows, accepted, lookup)
            write_jsonl(apath, rows)  # checkpoint
            _write_pending(pend, stem, rows)
            stats['batches'] += 1
            stats['accepted'] += len(accepted)
            print(f'{label}: accepted {len(accepted)}/{len(batch)}')
        print(f'{stem}: {total} links adjudicated by model')
    if not dry:
        _update_manifest(client.model_id)
    return stats


def _write_pending(pend: list, stem: str, rows: list) -> None:
    """Rewrite pending.json in place: drop items of this book whose row is no longer ibm1."""
    still = {(r['ref'], r['heb_node']) for r in rows if r['source'] == 'ibm1'}
    pend[:] = [p for p in pend if book_stem(p['ref']) != stem or (p['ref'], p['heb_node']) in still]
    with open(os.path.join(TT_DIR, 'align', 'pending.json'), 'w', encoding='utf-8') as fh:
        json.dump(pend, fh, ensure_ascii=False)


def _update_manifest(model_id: str) -> None:
    mpath = os.path.join(TT_DIR, 'align', 'manifest.json')
    with open(mpath, encoding='utf-8') as fh:
        m = json.load(fh)
    rows = [r for stem in m['books'] for r in read_jsonl(os.path.join(TT_DIR, 'align', f'{stem}.jsonl'))]
    model_links = sum(1 for r in rows if r['source'] == 'model')
    with open(os.path.join(TT_DIR, 'align', 'pending.json'), encoding='utf-8') as fh:
        pending = len(json.load(fh))
    m.update(model_id=model_id, model_links=model_links, pending_links=pending,
             total_links=sum(1 for r in rows if r['kind'] != 'null'), hash=manifest_hash(os.path.join(TT_DIR, 'align'), m['books']))
    with open(mpath, 'w', encoding='utf-8') as fh:
        json.dump(m, fh, indent=1)
        fh.write('\n')


def run_gold(sample_path: str, stem: str, client, dry: bool, max_batches=None) -> dict:
    """Model as second reader: align the sample verses, write reader="model" rows."""
    with open(sample_path, encoding='utf-8') as fh:
        refs = json.load(fh)
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
    out, stats = [], {'batches': 0, 'accepted': 0}
    for i in range(0, len(items), BATCH):
        if max_batches is not None and stats['batches'] >= max_batches:
            break
        batch = items[i:i + BATCH]
        prompt = link_prompt(batch)
        if dry:
            print(prompt[:1500]); return stats
        stats['batches'] += 1
        for a in parse_link_response(_complete(client, prompt, f'gold batch {i // BATCH + 1}'), batch):
            src = next(b for b in batch if b['heb_node'] == a['heb_node'])
            lemma = lookup.get((a['ref'], a['syr_position']), (None, None))[0] if a['syr_position'] is not None else None
            out.append({'ref': a['ref'], 'heb_node': a['heb_node'], 'heb_lex': src['heb_lex'], 'heb_word': src['heb_word'],
                        'heb_gloss': src['heb_gloss'], 'heb_feats': None, 'syr_position': a['syr_position'],
                        'syr_lemma': lemma, 'syr_source': None, 'kind': 'one-one' if a['syr_position'] is not None else 'null',
                        'reader': 'model', 'agreed': None})
            stats['accepted'] += 1
    gpath = os.path.join(TT_DIR, 'gold', f'{stem}_sample.jsonl')
    existing = [r for r in (read_jsonl(gpath) if os.path.exists(gpath) else []) if r['reader'] != 'model']
    write_jsonl(gpath, existing + out)
    print(f'gold: wrote {len(out)} model-reader rows')
    return stats


def main() -> None:
    load_dotenv(os.path.join(ROOT, '.env'))
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['lemmas', 'links', 'gold'])
    ap.add_argument('--book', default='deuteronomy')
    ap.add_argument('--model', default='claude-opus-5-5')
    ap.add_argument('--sample', default=os.path.join(TT_DIR, 'gold', 'sample_refs.json'))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--max-batches', type=int, default=None, help='stop after N batches (any mode)')
    args = ap.parse_args()
    client = None if args.dry_run else AnthropicAnnotator(args.model)
    if args.mode == 'lemmas':
        stats = run_lemmas(args.book, client, args.dry_run, args.max_batches)
    elif args.mode == 'links':
        stats = run_links(client, args.dry_run, args.max_batches)
    else:
        stats = run_gold(args.sample, args.book, client, args.dry_run, args.max_batches)
    if not args.dry_run:
        print(f"model={args.model} batches={stats['batches']} accepted={stats['accepted']}")


if __name__ == '__main__':
    main()
