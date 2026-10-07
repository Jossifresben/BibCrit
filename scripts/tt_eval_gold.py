# scripts/tt_eval_gold.py
"""Gold evaluation.

  python scripts/tt_eval_gold.py sample     # writes data/tt/gold/sample_refs.json (200 Deuteronomy refs)
  python scripts/tt_eval_gold.py eval       # writes data/tt/gold/eval.json from deuteronomy_sample.jsonl
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from translation_technique.gold import agreement, mark_agreed, precision_recall, select_sample  # noqa: E402
from translation_technique.lemmas import read_jsonl, write_jsonl  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TT = os.path.join(ROOT, 'data', 'tt')
GOLD = os.path.join(TT, 'gold')


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else 'eval'
    os.makedirs(GOLD, exist_ok=True)
    if mode == 'sample':
        refs = sorted({r['ref'] for r in read_jsonl(os.path.join(TT, 'align', 'deuteronomy.jsonl'))})
        sample = select_sample(refs, 200, 7)
        json.dump(sample, open(os.path.join(GOLD, 'sample_refs.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
        print(f'wrote {len(sample)} refs')
        return
    gpath = os.path.join(GOLD, 'deuteronomy_sample.jsonl')
    gold = mark_agreed(read_jsonl(gpath))
    write_jsonl(gpath, gold)
    align = read_jsonl(os.path.join(TT, 'align', 'deuteronomy.jsonl'))
    a = agreement(gold)
    pr = precision_recall(align, gold)
    out = {**a, **pr, 'manifest_hash': json.load(open(os.path.join(TT, 'align', 'manifest.json')))['hash']}
    json.dump(out, open(os.path.join(GOLD, 'eval.json'), 'w', encoding='utf-8'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
