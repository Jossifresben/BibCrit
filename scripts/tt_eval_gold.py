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


def main(argv=None, tt_dir=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    tt = tt_dir or os.environ.get('TT_DIR') or os.path.join(ROOT, 'data', 'tt')
    gold_dir = os.path.join(tt, 'gold')
    mode = argv[0] if argv else 'eval'
    os.makedirs(gold_dir, exist_ok=True)
    if mode == 'sample':
        refs = sorted({r['ref'] for r in read_jsonl(os.path.join(tt, 'align', 'deuteronomy.jsonl'))})
        sample = select_sample(refs, 200, 7)
        with open(os.path.join(gold_dir, 'sample_refs.json'), 'w', encoding='utf-8') as f:
            json.dump(sample, f, ensure_ascii=False, indent=0)
        print(f'wrote {len(sample)} refs')
        return 0
    gpath = os.path.join(gold_dir, 'deuteronomy_sample.jsonl')
    if not os.path.exists(gpath):
        print(f'error: gold file missing: {gpath} (annotate refs in the gold editor first)', file=sys.stderr)
        return 1
    gold = mark_agreed(read_jsonl(gpath))
    if not any(r['reader'] == 'model' for r in gold):
        print('warning: no reader "model" rows in the gold file; agreement and precision/recall are 0.0 '
              '(run tt_adjudicate.py gold first)', file=sys.stderr)
    write_jsonl(gpath, gold)
    align = read_jsonl(os.path.join(tt, 'align', 'deuteronomy.jsonl'))
    a = agreement(gold)
    pr = precision_recall(align, gold)
    with open(os.path.join(tt, 'align', 'manifest.json'), encoding='utf-8') as f:
        manifest_hash = json.load(f)['hash']
    out = {**a, **pr, 'manifest_hash': manifest_hash}
    with open(os.path.join(gold_dir, 'eval.json'), 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
