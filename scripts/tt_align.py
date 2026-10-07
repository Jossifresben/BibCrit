# scripts/tt_align.py
"""Stage B: align Hebrew (BHSA) to the Syriac lemma layer, all books with lemma files.

Usage:
  python scripts/tt_align.py                 # all books present in data/tt/lemmas/
  python scripts/tt_align.py --books deuteronomy genesis
  python scripts/tt_align.py --threshold 0.3 --iterations 5
  python scripts/tt_align.py --books deuteronomy --force   # discards model links in that book's file

Writes data/tt/align/<book>.jsonl and merges (never replaces) pending.json,
       data/tt/align/manifest.json, data/tt/lexemes.json,
and updates lemma/pos/confidence of disambiguated tokens in data/tt/lemmas/<book>.jsonl.
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from translation_technique.align import (  # noqa: E402
    manifest_hash,
    align_corpus, apply_disambiguations, book_stem, build_parallel, hebrew_tokens, pending_links)
from translation_technique.lemmas import read_jsonl, write_jsonl  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TT_DIR = os.path.join(ROOT, 'data', 'tt')


class RefusedOverwrite(Exception):
    pass


def check_model_rows(tt_dir: str, books: list, force: bool) -> None:
    """Raise RefusedOverwrite if any of these books' alignment files holds model rows and force is not set."""
    lost = {}
    for stem in books:
        path = os.path.join(tt_dir, 'align', f'{stem}.jsonl')
        if os.path.exists(path):
            n = sum(1 for r in read_jsonl(path) if r['source'] == 'model')
            if n:
                lost[stem] = n
    if lost and not force:
        raise RefusedOverwrite(', '.join(f'{s}.jsonl has {n} model rows that would be lost' for s, n in lost.items()))


def _load(path, default):
    if os.path.exists(path):
        with open(path, encoding='utf-8') as fh:
            return json.load(fh)
    return default


def write_outputs(tt_dir: str, rows_by_book: dict, pend: list, threshold: float, iterations: int,
                  force: bool = False) -> dict:
    """Write align/<book>.jsonl for the books given and MERGE manifest, lexemes and pending with whatever is
    already on disk (only the books being aligned are replaced). Refuses, before writing anything, to replace
    an alignment file that holds model-adjudicated links unless force is set."""
    out_dir = os.path.join(tt_dir, 'align')
    os.makedirs(out_dir, exist_ok=True)
    check_model_rows(tt_dir, list(rows_by_book), force)
    for stem in sorted(rows_by_book):
        write_jsonl(os.path.join(out_dir, f'{stem}.jsonl'), rows_by_book[stem])
    old = _load(os.path.join(out_dir, 'manifest.json'), {})
    books = sorted(set(old.get('books', [])) | set(rows_by_book))
    digest = manifest_hash(out_dir, books)

    pend_all = [p for p in _load(os.path.join(out_dir, 'pending.json'), []) if book_stem(p['ref']) not in rows_by_book] + pend
    with open(os.path.join(out_dir, 'pending.json'), 'w', encoding='utf-8') as fh:
        json.dump(pend_all, fh, ensure_ascii=False)

    lex = _load(os.path.join(tt_dir, 'lexemes.json'), {})
    for e in lex.values():
        for stem in rows_by_book:
            e.get('books', {}).pop(stem, None)
    for stem, brows in rows_by_book.items():
        for r in brows:
            if r['heb_lex'] is None:
                continue
            e = lex.setdefault(r['heb_lex'], {'gloss': r['heb_gloss'], 'word': r['heb_word'], 'books': {}})
            e['books'][stem] = e['books'].get(stem, 0) + 1
    lex = {k: v for k, v in lex.items() if v['books']}
    with open(os.path.join(tt_dir, 'lexemes.json'), 'w', encoding='utf-8') as fh:
        json.dump(lex, fh, ensure_ascii=False)

    all_rows = [r for stem in books for r in (rows_by_book[stem] if stem in rows_by_book
                else read_jsonl(os.path.join(out_dir, f'{stem}.jsonl')))]
    vpath = os.path.join(tt_dir, 'VERSION')
    version = open(vpath).read().strip() if os.path.exists(vpath) else '0.1.0'
    manifest = {
        'version': version,
        'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'corpus_versions': {'bhsa': '2021', 'pesh_etcbc': 'ETCBC/peshitta tf 0.2', 'lemmas': version},
        'iterations': iterations, 'threshold': threshold, 'books': books,
        'model_id': old.get('model_id') if any(r['source'] == 'model' for r in all_rows) else None,
        'model_links': sum(1 for r in all_rows if r['source'] == 'model'),
        'total_links': sum(1 for r in all_rows if r['kind'] != 'null'),
        'pending_links': len(pend_all), 'hash': digest,
    }
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=1)
        fh.write('\n')
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--books', nargs='*')
    ap.add_argument('--threshold', type=float, default=0.3)
    ap.add_argument('--iterations', type=int, default=5)
    ap.add_argument('--force', action='store_true', help='overwrite alignment files that hold model-adjudicated links')
    args = ap.parse_args()

    lem_dir = os.path.join(TT_DIR, 'lemmas')
    books = args.books or sorted(f[:-6] for f in os.listdir(lem_dir)
                                 if f.endswith('.jsonl') and not f.startswith('unresolved'))
    try:
        check_model_rows(TT_DIR, books, args.force)  # before any file is touched
    except RefusedOverwrite as e:
        sys.exit(f'refusing to overwrite: {e}. Pass --force to discard those model links.')
    from tf.app import use
    A = use('ETCBC/bhsa', silence='deep')

    parallel, lemma_rows_by_book = [], {}
    for stem in books:
        rows = read_jsonl(os.path.join(lem_dir, f'{stem}.jsonl'))
        lemma_rows_by_book[stem] = rows
        parallel.extend(build_parallel(hebrew_tokens(A.api, stem), rows))
    print(f'parallel verses: {len(parallel)}')

    rows, dis = align_corpus(parallel, iterations=args.iterations)

    # write back disambiguations
    for stem, lrows in lemma_rows_by_book.items():
        changed = apply_disambiguations(lrows, dis)
        write_jsonl(os.path.join(lem_dir, f'{stem}.jsonl'), lrows)
        print(f'{stem}: disambiguated {changed}')

    by_book = defaultdict(list)
    for r in rows:
        by_book[book_stem(r['ref'])].append(r)
    pend = pending_links(rows, args.threshold)
    try:
        manifest = write_outputs(TT_DIR, by_book, pend, args.threshold, args.iterations, args.force)
    except RefusedOverwrite as e:
        sys.exit(f'refusing to overwrite: {e}. Pass --force to discard those model links.')
    print(json.dumps({k: manifest[k] for k in ('total_links', 'pending_links', 'hash')}))


if __name__ == '__main__':
    main()
