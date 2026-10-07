# tests/test_tt_adjudicate.py
import json
from translation_technique.adjudicate import (
    lemma_prompt, parse_lemma_response, link_prompt, parse_link_response,
    merge_lemma_annotations, merge_link_annotations,
)


def test_lemma_prompt_mentions_every_form_and_demands_json():
    p = lemma_prompt([{'norm': 'ܘܬܡܚܐ', 'ref': 'Deuteronomy 1:1', 'verse_text': 'ܐ ܘܬܡܚܐ ܒ'}])
    assert 'ܘܬܡܚܐ' in p and 'JSON' in p and 'confidence' in p


def test_parse_lemma_response_accepts_valid_and_rejects_invalid():
    batch = [{'norm': 'ܘܬܡܚܐ', 'ref': 'Deuteronomy 1:1', 'verse_text': ''},
             {'norm': 'ܐܫܟܚܗ', 'ref': 'Deuteronomy 1:2', 'verse_text': ''}]
    text = json.dumps([
        {'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'verb', 'confidence': 0.7},
        {'norm': 'ܐܫܟܚܗ', 'lemma': 'eshkah', 'pos': 'verb', 'confidence': 0.9},      # not Syriac script
        {'norm': 'ܙܙܙ', 'lemma': 'ܙܙܙ', 'pos': 'verb', 'confidence': 0.9},             # not in batch
        {'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'thing', 'confidence': 0.7},          # bad pos
    ])
    acc = parse_lemma_response(text, batch)
    assert acc == [{'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'verb', 'confidence': 0.7}]


def test_parse_lemma_response_tolerates_code_fence_and_garbage():
    batch = [{'norm': 'ܘܬܡܚܐ', 'ref': 'r', 'verse_text': ''}]
    assert parse_lemma_response('```json\n[{"norm":"ܘܬܡܚܐ","lemma":"ܡܚܐ","pos":"verb","confidence":0.5}]\n```', batch)
    assert parse_lemma_response('not json', batch) == []


def test_link_prompt_and_parse_quarantines_bad_positions():
    batch = [{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'heb_word': 'וַיֵּרֶד', 'heb_lex': 'JRD[', 'heb_gloss': 'descend',
              'syr_tokens': [{'position': 1, 'form': 'ܘܢܚܬ'}, {'position': 2, 'form': 'ܡܢ'}]}]
    p = link_prompt(batch)
    assert 'JRD[' in p and 'ܘܢܚܬ' in p
    text = json.dumps([{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': 9},
                       {'ref': 'Deuteronomy 1:1', 'heb_node': 99, 'syr_position': 1}])
    assert parse_link_response(text, batch) == []
    text = json.dumps([{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': 1}])
    assert parse_link_response(text, batch) == [{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': 1}]
    text = json.dumps([{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': None}])
    assert parse_link_response(text, batch) == [{'ref': 'Deuteronomy 1:1', 'heb_node': 7, 'syr_position': None}]


def test_merge_lemma_annotations_only_touches_unresolved():
    rows = [{'ref': 'r', 'position': 1, 'form': 'ܘܬܡܚܐ', 'norm': 'ܘܬܡܚܐ', 'lemma': None, 'pos': None,
             'source': 'unresolved', 'rule': None, 'candidates': [], 'confidence': 0.0},
            {'ref': 'r', 'position': 2, 'form': 'ܡܢ', 'norm': 'ܡܢ', 'lemma': 'ܡܢ', 'pos': 'particle',
             'source': 'sedra', 'rule': None, 'candidates': [], 'confidence': 1.0}]
    n = merge_lemma_annotations(rows, [{'norm': 'ܘܬܡܚܐ', 'lemma': 'ܡܚܐ', 'pos': 'verb', 'confidence': 0.7},
                                       {'norm': 'ܡܢ', 'lemma': 'X', 'pos': 'verb', 'confidence': 0.9}])
    assert n == 1
    assert rows[0]['source'] == 'model' and rows[0]['lemma'] == 'ܡܚܐ' and rows[0]['confidence'] == 0.7
    assert rows[1]['lemma'] == 'ܡܢ'


def test_merge_link_annotations_replaces_ibm1_row():
    rows = [{'ref': 'r', 'heb_node': 7, 'heb_lex': 'JRD[', 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {},
             'syr_position': 2, 'syr_lemma': 'ܡܢ', 'syr_source': 'sedra', 'prob': 0.1, 'kind': 'one-one', 'source': 'ibm1'}]
    lookup = {('r', 1): ('ܢܚܬ', 'sedra'), ('r', 2): ('ܡܢ', 'sedra')}
    n = merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 7, 'syr_position': 1}], lookup)
    assert n == 1
    assert rows[0]['syr_position'] == 1 and rows[0]['syr_lemma'] == 'ܢܚܬ' and rows[0]['source'] == 'model' and rows[0]['prob'] == 1.0
    rows[0]['source'] = 'ibm1'  # model rows are never re-touched; reset to exercise the null branch
    n = merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 7, 'syr_position': None}], lookup)
    assert rows[0]['kind'] == 'null' and rows[0]['syr_lemma'] is None and rows[0]['source'] == 'model'


def test_merge_link_annotations_collapses_duplicates_and_spares_model_rows():
    base = {'ref': 'r', 'heb_node': 7, 'heb_lex': 'L', 'heb_word': 'w', 'heb_gloss': 'g', 'heb_feats': {},
            'syr_lemma': 'ܡܢ', 'syr_source': 'sedra', 'prob': 0.1, 'kind': 'one-many', 'source': 'ibm1'}
    rows = [dict(base, syr_position=2), dict(base, syr_position=3)]
    lookup = {('r', 1): ('ܢܚܬ', 'sedra')}
    n = merge_link_annotations(rows, [{'ref': 'r', 'heb_node': 7, 'syr_position': 1}], lookup)
    assert n == 1 and len(rows) == 1 and rows[0]['syr_position'] == 1 and rows[0]['source'] == 'model'
    keep = [dict(base, syr_position=2, source='model')]
    assert merge_link_annotations(keep, [{'ref': 'r', 'heb_node': 7, 'syr_position': 1}], lookup) == 0
    assert keep[0]['syr_position'] == 2


def test_parsers_reject_wrong_types_without_raising():
    batch = [{'ref': 'r', 'heb_node': 7, 'heb_word': 'w', 'heb_lex': 'L', 'heb_gloss': 'g',
              'syr_tokens': [{'position': 1, 'form': 'ܐ'}]}]
    for bad in (True, 1.0, [1], '1'):
        assert parse_link_response(json.dumps([{'ref': 'r', 'heb_node': 7, 'syr_position': bad}]), batch) == []
    for bad in ([7], '7', True, 7.0):
        assert parse_link_response(json.dumps([{'ref': 'r', 'heb_node': bad, 'syr_position': 1}]), batch) == []
    lb = [{'norm': 'ܐܐ', 'ref': 'r', 'verse_text': ''}]
    for it in ({'norm': 'ܐܐ', 'lemma': 'ܐܐ\n', 'pos': 'verb', 'confidence': 0.5},
               {'norm': 'ܐܐ', 'lemma': 'ܐܐ', 'pos': 'verb', 'confidence': True},
               {'norm': ['ܐܐ'], 'lemma': 'ܐܐ', 'pos': 'verb', 'confidence': 0.5},
               {'norm': 'ܐܐ', 'lemma': 'ܐܐ', 'pos': ['verb'], 'confidence': 0.5}):
        assert parse_lemma_response(json.dumps([it]), lb) == []


def test_manifest_hash_order_independent_and_sensitive(tmp_path):
    from translation_technique.align import manifest_hash
    (tmp_path / 'a.jsonl').write_text('1\n')
    (tmp_path / 'b.jsonl').write_text('2\n')
    h = manifest_hash(str(tmp_path), ['a', 'b'])
    assert h == manifest_hash(str(tmp_path), ['b', 'a'])
    (tmp_path / 'b.jsonl').write_text('3\n')
    assert manifest_hash(str(tmp_path), ['a', 'b']) != h
