# scripts/tt_build_lemmas.py
"""Stage A: build the Syriac lemma layer for the Peshitta OT.

Usage:
  python scripts/tt_build_lemmas.py --book deuteronomy
  python scripts/tt_build_lemmas.py --all
  python scripts/tt_build_lemmas.py --all --offline   # never call SEDRA; unknown forms stay unresolved

Reads  data/corpora/pesh_etcbc/<book>.csv
Writes data/tt/lemmas/<book>.jsonl, data/tt/lemmas/unresolved.<book>.json,
       data/tt/lemmas/coverage.json (merged per book), data/tt/sedra_cache.json
First run is bounded by SEDRA calls (0.3 s each); later runs are offline.
"""
import argparse
import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from translation_technique.lemmas import (  # noqa: E402
    SedraCache, build_lemma_rows, coverage, sedra_fetch, write_jsonl,
)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORPUS_DIR = os.path.join(ROOT, 'data', 'corpora', 'pesh_etcbc')
TT_DIR = os.path.join(ROOT, 'data', 'tt')
CACHE_PATH = os.path.join(TT_DIR, 'sedra_cache.json')


def build_book(stem: str, cache: SedraCache) -> dict:
    path = os.path.join(CORPUS_DIR, f'{stem}.csv')
    with open(path, encoding='utf-8') as fh:
        tokens = list(csv.DictReader(fh))
    rows = build_lemma_rows(tokens, cache)
    out_dir = os.path.join(TT_DIR, 'lemmas')
    write_jsonl(os.path.join(out_dir, f'{stem}.jsonl'), rows)
    unresolved = sorted({r['norm'] for r in rows if r['source'] == 'unresolved'})
    with open(os.path.join(out_dir, f'unresolved.{stem}.json'), 'w', encoding='utf-8') as fh:
        json.dump(unresolved, fh, ensure_ascii=False, indent=0)
    cov = coverage(rows)
    cov_path = os.path.join(out_dir, 'coverage.json')
    merged = json.load(open(cov_path, encoding='utf-8')) if os.path.exists(cov_path) else {}
    merged[stem] = cov
    with open(cov_path, 'w', encoding='utf-8') as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=1, sort_keys=True)
    cache.save()
    return cov


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--book', help='book stem, e.g. deuteronomy')
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--offline', action='store_true')
    args = ap.parse_args()
    if not (args.book or args.all):
        ap.error('give --book <stem> or --all')
    fetcher = None if args.offline else sedra_fetch
    cache = SedraCache(CACHE_PATH, fetcher=fetcher)
    if args.offline:
        # unknown forms must not raise; wrap get() to return None
        cache.fetcher = lambda norm: None
        cache.delay = 0
    stems = [args.book] if args.book else sorted(
        f[:-4] for f in os.listdir(CORPUS_DIR) if f.endswith('.csv'))
    for stem in stems:
        cov = build_book(stem, cache)
        print(f"{stem}: tokens={cov['tokens']} types={cov['types']} "
              f"by_source_tokens={ {k: round(v, 3) for k, v in cov['by_source_tokens'].items()} }")
    print('sedra cache:', cache.stats())


if __name__ == '__main__':
    main()
