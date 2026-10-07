"""Compares our Deuteronomy counts with the figures published in the dissertation slides.
A disagreement is a finding to report, not a test failure: this test only prints."""
import os
import pytest
from translation_technique.lemmas import read_jsonl
from translation_technique.tables import distribution

ROOT = os.path.dirname(os.path.dirname(__file__))
ALIGN = os.path.join(ROOT, 'data', 'tt', 'align', 'deuteronomy.jsonl')

PUBLISHED = {
    'JRD[': {'ܢܚܬ': 9, 'ܟܒܫ': 2, 'ܐܬܐ': 1},        # slide: NXT 9, KBC 2, >TJ 1
    'BW>[': {'_top1': 60, '_top2': 28},             # bar chart, read by eye
    'NTN[': {'_top1': 133, '_top2': 19},            # bar chart, read by eye
}


@pytest.mark.skipif(not os.path.exists(ALIGN), reason='Deuteronomy alignment not built')
def test_print_dissertation_diff(capsys):
    rows = read_jsonl(ALIGN)
    for lex, pub in PUBLISHED.items():
        d = distribution(rows, lex, ['deuteronomy'])
        ours = {i['syr_lemma']: i['count'] for i in d['items']}
        top = [i['count'] for i in d['items'][:2]] + [0, 0]
        print(f'\n{lex}: total={d["total"]} null={d["null_count"]} model_share={d["model_share_total"]}')
        for k, v in pub.items():
            if k == '_top1':
                print(f'  top-1 count: ours={top[0]} published≈{v}')
            elif k == '_top2':
                print(f'  top-2 count: ours={top[1]} published≈{v}')
            else:
                print(f'  {k}: ours={ours.get(k, 0)} published={v}')
    assert True
