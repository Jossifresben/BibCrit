# tests/test_tt_tables.py
import pytest
from translation_technique.tables import (
    FACETS, summary, distribution, crosstab, model_share, apply_witness, occurrences, facet_value,
)
from translation_technique.witnesses import load_witnesses, sigla, substitutions_for


def _row(ref, lex, lemma, vs='qal', syr_source='sedra', source='ibm1', kind='one-one', pos=1):
    return {'ref': ref, 'heb_node': hash((ref, pos)) % 10000, 'heb_lex': lex, 'heb_word': 'w', 'heb_gloss': 'g',
            'heb_feats': {'sp': 'verb', 'vs': vs, 'vt': 'perf', 'clause_typ': 'WayX', 'obj_function': 'none', 'next_prep': 'none'},
            'syr_position': pos, 'syr_lemma': lemma, 'syr_source': syr_source, 'prob': 0.8, 'kind': kind, 'source': source}


def _rows():
    return [
        _row('Deuteronomy 1:1', 'JRD[', 'ܢܚܬ'),
        _row('Deuteronomy 1:2', 'JRD[', 'ܢܚܬ'),
        _row('Deuteronomy 1:3', 'JRD[', 'ܟܒܫ', vs='hif'),
        _row('Deuteronomy 1:4', 'JRD[', 'ܟܒܫ', vs='hif', syr_source='model'),
        _row('Deuteronomy 1:5', 'JRD[', None, kind='null'),
        _row('Genesis 1:1', 'JRD[', 'ܐܬܐ', source='model'),
        _row('Genesis 1:2', 'BW>[', 'ܐܬܐ'),
    ]


def test_distribution_counts_and_model_share():
    d = distribution(_rows(), 'JRD[', ['deuteronomy'])
    assert d['total'] == 5 and d['null_count'] == 1
    assert d['items'][0] == {'syr_lemma': 'ܢܚܬ', 'count': 2, 'model_share': pytest.approx(0.0)}
    assert d['items'][1] == {'syr_lemma': 'ܟܒܫ', 'count': 2, 'model_share': pytest.approx(0.5)}
    assert d['model_share_total'] == pytest.approx(0.25)


def test_distribution_all_books():
    d = distribution(_rows(), 'JRD[', None)
    assert d['total'] == 6
    assert {i['syr_lemma'] for i in d['items']} == {'ܢܚܬ', 'ܟܒܫ', 'ܐܬܐ'}


def test_facets_declare_unavailable_animacy():
    assert FACETS['animacy']['available'] is False and FACETS['animacy']['reason']
    assert FACETS['vs']['available'] is True


def test_facet_value_book_and_feature():
    r = _row('Deuteronomy 1:1', 'JRD[', 'ܢܚܬ', vs='hif')
    assert facet_value(r, 'book') == 'deuteronomy' and facet_value(r, 'vs') == 'hif'


def test_crosstab_matrix_and_stats():
    c = crosstab(_rows(), 'JRD[', 'vs', ['deuteronomy'])
    assert c['lemmas'] == ['ܢܚܬ', 'ܟܒܫ'] and c['values'] == ['hif', 'qal']
    assert c['matrix'] == [[0, 2], [2, 0]]
    assert c['dof'] == 1 and c['unreliable'] is True
    assert c['cramers_v'] == 1.0


def test_crosstab_unavailable_facet_raises():
    with pytest.raises(ValueError):
        crosstab(_rows(), 'JRD[', 'animacy', None)


def test_model_share_counts_either_side():
    assert model_share(_rows()) == pytest.approx(2 / 7)


def test_apply_witness_substitutes_and_marks():
    rows = apply_witness(_rows(), {('Deuteronomy 1:1', 1): {'lemma': 'ܐܙܠ', 'form': 'x', 'note': '', 'keyed_from': 't'}})
    r = next(x for x in rows if x['ref'] == 'Deuteronomy 1:1')
    assert r['syr_lemma'] == 'ܐܙܠ' and r['syr_source'] == 'witness'
    assert _rows()[0]['syr_lemma'] == 'ܢܚܬ'   # input untouched


def test_occurrences_sorted_canonically():
    occ = occurrences(_rows(), 'JRD[', None)
    assert occ[0]['ref'] == 'Genesis 1:1' and occ[-1]['ref'] == 'Deuteronomy 1:4'
    assert all(o['kind'] != 'null' for o in occ)


def test_witness_file(tmp_path):
    p = tmp_path / 'w.jsonl'
    p.write_text('{"ref":"Deuteronomy 22:4","position":5,"sigla":"9a1","form":"ܕܐܚܘܟ","lemma":"ܐܚܐ","note":"","keyed_from":"slide"}\n'
                 '{"ref":"Deuteronomy 22:4","position":5,"sigla":"7a1","form":"x","lemma":"y","note":"","keyed_from":"slide"}\n', encoding='utf-8')
    w = load_witnesses(str(p))
    assert sigla(w) == ['7a1', '9a1']
    subs = substitutions_for(w, '9a1')
    assert subs[('Deuteronomy 22:4', 5)]['lemma'] == 'ܐܚܐ'


def test_witness_file_rejects_missing_keyed_from(tmp_path):
    p = tmp_path / 'w.jsonl'
    p.write_text('{"ref":"Deuteronomy 22:4","position":5,"sigla":"9a1","form":"x","lemma":"y","note":""}\n', encoding='utf-8')
    with pytest.raises(ValueError):
        load_witnesses(str(p))


def test_apply_witness_none_lemma_becomes_null_row():
    rows = apply_witness(_rows(), {('Deuteronomy 1:1', 1): {'lemma': None, 'form': 'x', 'note': '', 'keyed_from': 't'}})
    r = next(x for x in rows if x['ref'] == 'Deuteronomy 1:1')
    assert r['syr_lemma'] is None and r['kind'] == 'null' and r['syr_source'] == 'witness'


def test_empty_books_selects_nothing():
    assert distribution(_rows(), 'JRD[', [])['total'] == 0


def test_summary_too_few():
    sm = summary(_rows(), 'BW>[', None)
    assert sm['too_few'] and sm['n'] == 1


def test_summary_facts_hand_computed():
    rows = [_row(f'Deuteronomy 1:{i}', 'X[', 'ܐ') for i in range(1, 7)]
    rows += [_row(f'Deuteronomy 2:{i}', 'X[', 'ܒ', vs='hif') for i in range(1, 3)]
    rows += [_row('Deuteronomy 3:1', 'X[', 'ܓ'), _row('Deuteronomy 3:2', 'X[', None, kind='null')]
    sm = summary(rows, 'X[', ['deuteronomy'])
    assert sm['n'] == 9 and sm['total'] == 10 and sm['null_count'] == 1
    assert sm['dominant']['lemma'] == 'ܐ' and sm['dominant']['count'] == 6
    assert sm['dominant']['share'] == pytest.approx(6 / 9)
    assert sm['distinct'] == 3 and sm['singletons'] == 1
    assert sm['model_share'] == pytest.approx(0.0)
    assert sm['facet'] is None or sm['facet']['v'] <= 1.0   # counts this small are flagged unreliable


def test_summary_picks_reliable_facet_with_largest_v():
    rows = []
    for i in range(30):
        rows.append(_row(f'Deuteronomy 1:{i + 1}', 'Y[', 'ܐ', vs='qal'))
    for i in range(30):
        rows.append(_row(f'Deuteronomy 2:{i + 1}', 'Y[', 'ܒ', vs='hif'))
    sm = summary(rows, 'Y[', None)
    assert sm['facet']['facet'] == 'vs' and sm['facet']['v'] == pytest.approx(1.0)


def _sub(lex=None, lemma='ܐܚܐ'):
    return {('Deuteronomy 1:1', 4): {'lemma': lemma, 'form': 'x', 'note': '', 'keyed_from': 't', 'heb_lex': lex}}


def _witness_rows():
    null = _row('Deuteronomy 1:1', '>X/', None, kind='null', pos=None)
    null['heb_node'] = 50
    syr_only = _row('Deuteronomy 1:1', None, 'ܒܒܒ', kind='null', pos=4)
    syr_only['heb_node'] = None
    syr_only['heb_lex'] = None
    return [_row('Deuteronomy 1:1', 'JRD[', 'ܢܚܬ'), null, syr_only]


def test_apply_witness_heb_lex_links_null_and_drops_syriac_only():
    out = apply_witness(_witness_rows(), _sub('>X/'))
    assert len(out) == 2
    r = next(x for x in out if x['heb_lex'] == '>X/')
    assert (r['kind'], r['source'], r['syr_source'], r['prob'], r['syr_position'], r['syr_lemma']) == \
        ('one-one', 'witness', 'witness', 1.0, 4, 'ܐܚܐ')
    assert not any(x['heb_node'] is None for x in out)


def test_apply_witness_without_heb_lex_keeps_old_behaviour():
    out = apply_witness(_witness_rows(), _sub(None))
    assert len(out) == 3 and next(x for x in out if x['heb_lex'] == '>X/')['kind'] == 'null'


def test_load_witnesses_accepts_heb_lex(tmp_path):
    p = tmp_path / 'w.jsonl'
    p.write_text('{"ref": "Deuteronomy 1:1", "position": 4, "sigla": "s", "heb_lex": ">X/", "form": "f", "lemma": "l", "keyed_from": "k"}\n')
    assert load_witnesses(str(p))[0]['heb_lex'] == '>X/'
    assert substitutions_for(load_witnesses(str(p)), 's')[('Deuteronomy 1:1', 4)]['heb_lex'] == '>X/'
