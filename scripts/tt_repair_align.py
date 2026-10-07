# scripts/tt_repair_align.py
"""Offline repair of an adjudicated alignment file (no model, no network).

  python scripts/tt_repair_align.py deuteronomy [--model claude-opus-5-5]

Restores a null row for every Syriac token no row references (left behind when the model re-pointed its
Hebrew node), recomputes one-one / one-many / many-one, sets prob to null on model links, and refreshes
the manifest hash and counts. Idempotent.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from translation_technique.adjudicate import recompute_kinds, restore_orphans  # noqa: E402
from translation_technique.lemmas import read_jsonl, write_jsonl  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TT_DIR = os.path.join(ROOT, 'data', 'tt')


def repair(stem: str, tt_dir: str = TT_DIR) -> dict:
    lemmas = read_jsonl(os.path.join(tt_dir, 'lemmas', f'{stem}.jsonl'))
    apath = os.path.join(tt_dir, 'align', f'{stem}.jsonl')
    rows = read_jsonl(apath)
    lookup = {(l['ref'], l['position']): (l['lemma'], l['source']) for l in lemmas}
    positions = defaultdict(set)
    for ref, pos in lookup:
        positions[ref].add(pos)
    before = {'rows': len(rows), 'kinds': dict(Counter(r['kind'] for r in rows)),
              'model_prob_not_null': sum(1 for r in rows if r['source'] == 'model' and r['syr_position'] is not None and r['prob'] is not None)}
    added = restore_orphans(rows, lookup, positions)
    recompute_kinds(rows)
    for r in rows:
        if r['source'] == 'model' and r['syr_position'] is not None:
            r['prob'] = None
    write_jsonl(apath, rows)
    after = {'rows': len(rows), 'kinds': dict(Counter(r['kind'] for r in rows)), 'orphans_restored': added}
    return {'before': before, 'after': after}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('book')
    ap.add_argument('--model', default='claude-opus-5-5')
    args = ap.parse_args()
    out = repair(args.book)
    import tt_adjudicate
    tt_adjudicate._update_manifest(args.model)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
