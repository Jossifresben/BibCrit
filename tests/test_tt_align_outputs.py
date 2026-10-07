# tests/test_tt_align_outputs.py
import importlib.util
import json
import os

import pytest


def _mod():
    spec = importlib.util.spec_from_file_location(
        'tt_align', os.path.join(os.path.dirname(os.path.dirname(__file__)), 'scripts', 'tt_align.py'))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _row(book_ref, lex, source='ibm1', kind='one-one'):
    return {'ref': book_ref, 'heb_node': 1, 'heb_lex': lex, 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {},
            'syr_position': 1, 'syr_lemma': 'l', 'syr_source': 'sedra', 'prob': 0.9, 'kind': kind, 'source': source}


def test_subset_run_merges_manifest_lexemes_pending(tmp_path):
    m = _mod()
    t = str(tmp_path)
    m.write_outputs(t, {'deuteronomy': [_row('Deuteronomy 1:1', 'A')], 'amos': [_row('Amos 1:1', 'A')]},
                    [{'ref': 'Deuteronomy 1:1', 'heb_node': 1}, {'ref': 'Amos 1:1', 'heb_node': 1}], 0.3, 5)
    man = m.write_outputs(t, {'amos': [_row('Amos 1:1', 'B'), _row('Amos 1:2', 'B')]}, [{'ref': 'Amos 1:2', 'heb_node': 1}], 0.3, 5)
    assert man['books'] == ['amos', 'deuteronomy'] and man['total_links'] == 3
    lex = json.load(open(tmp_path / 'lexemes.json'))
    assert lex['A']['books'] == {'deuteronomy': 1} and lex['B']['books'] == {'amos': 2}
    pend = json.load(open(tmp_path / 'align' / 'pending.json'))
    assert sorted(p['ref'] for p in pend) == ['Amos 1:2', 'Deuteronomy 1:1']
    assert man['pending_links'] == 2


def test_model_rows_are_not_overwritten_without_force(tmp_path):
    m = _mod()
    t = str(tmp_path)
    m.write_outputs(t, {'deuteronomy': [_row('Deuteronomy 1:1', 'A', source='model')]}, [], 0.3, 5)
    with pytest.raises(m.RefusedOverwrite, match='1 model rows'):
        m.write_outputs(t, {'deuteronomy': [_row('Deuteronomy 1:1', 'A')]}, [], 0.3, 5)
    kept = [json.loads(l) for l in open(tmp_path / 'align' / 'deuteronomy.jsonl')]
    assert kept[0]['source'] == 'model'
    m.write_outputs(t, {'deuteronomy': [_row('Deuteronomy 1:1', 'A')]}, [], 0.3, 5, force=True)
    assert json.loads(open(tmp_path / 'align' / 'deuteronomy.jsonl').readline())['source'] == 'ibm1'
