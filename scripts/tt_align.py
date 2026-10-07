# scripts/tt_align.py
"""Stage B: align Hebrew (BHSA) to the Syriac lemma layer, all books with lemma files.

Usage:
  python scripts/tt_align.py                 # all books present in data/tt/lemmas/
  python scripts/tt_align.py --books deuteronomy genesis
  python scripts/tt_align.py --threshold 0.3 --iterations 5

Writes data/tt/align/<book>.jsonl, data/tt/align/pending.json,
       data/tt/align/manifest.json, data/tt/lexemes.json,
and updates lemma/pos/confidence of disambiguated tokens in data/tt/lemmas/<book>.jsonl.
"""
import argparse
import hashlib
import json
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from translation_technique.align import align_corpus, build_parallel, hebrew_tokens, pending_links  # noqa: E402
from translation_technique.lemmas import read_jsonl, write_jsonl  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TT_DIR = os.path.join(ROOT, 'data', 'tt')


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--books', nargs='*')
    ap.add_argument('--threshold', type=float, default=0.3)
    ap.add_argument('--iterations', type=int, default=5)
    args = ap.parse_args()

    lem_dir = os.path.join(TT_DIR, 'lemmas')
    books = args.books or sorted(f[:-6] for f in os.listdir(lem_dir)
                                 if f.endswith('.jsonl') and not f.startswith('unresolved'))
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
        changed = 0
        for r in lrows:
            key = (r['ref'], r['position'])
            if key in dis:
                r['lemma'], r['pos'], r['confidence'] = dis[key]
                changed += 1
        write_jsonl(os.path.join(lem_dir, f'{stem}.jsonl'), lrows)
        print(f'{stem}: disambiguated {changed}')

    out_dir = os.path.join(TT_DIR, 'align')
    os.makedirs(out_dir, exist_ok=True)
    by_book = defaultdict(list)
    for r in rows:
        by_book[r['ref'].rsplit(' ', 1)[0].lower().replace(' ', '_')].append(r)
    h = hashlib.sha256()
    for stem in sorted(by_book):
        path = os.path.join(out_dir, f'{stem}.jsonl')
        write_jsonl(path, by_book[stem])
        h.update(open(path, 'rb').read())

    pend = pending_links(rows, args.threshold)
    with open(os.path.join(out_dir, 'pending.json'), 'w', encoding='utf-8') as fh:
        json.dump(pend, fh, ensure_ascii=False)

    lex: dict = {}
    for r in rows:
        if r['heb_lex'] is None:
            continue
        e = lex.setdefault(r['heb_lex'], {'gloss': r['heb_gloss'], 'word': r['heb_word'], 'books': {}})
        stem = r['ref'].rsplit(' ', 1)[0].lower().replace(' ', '_')
        e['books'][stem] = e['books'].get(stem, 0) + 1
    with open(os.path.join(TT_DIR, 'lexemes.json'), 'w', encoding='utf-8') as fh:
        json.dump(lex, fh, ensure_ascii=False)

    version = open(os.path.join(TT_DIR, 'VERSION')).read().strip() if os.path.exists(os.path.join(TT_DIR, 'VERSION')) else '0.1.0'
    manifest = {
        'version': version,
        'built_at': datetime.now(timezone.utc).isoformat(timespec='seconds'),
        'corpus_versions': {'bhsa': '2021', 'pesh_etcbc': 'ETCBC/peshitta tf 0.2', 'lemmas': version},
        'iterations': args.iterations, 'threshold': args.threshold, 'books': sorted(by_book),
        'model_id': None, 'model_links': 0, 'total_links': sum(1 for r in rows if r['kind'] != 'null'),
        'pending_links': len(pend), 'hash': h.hexdigest(),
    }
    with open(os.path.join(out_dir, 'manifest.json'), 'w', encoding='utf-8') as fh:
        json.dump(manifest, fh, indent=1)
    print(json.dumps({k: manifest[k] for k in ('total_links', 'pending_links', 'hash')}))


if __name__ == '__main__':
    main()
