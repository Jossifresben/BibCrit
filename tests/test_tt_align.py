# tests/test_tt_align.py
import pytest
from translation_technique.align import normalize_ref, build_parallel


def test_normalize_ref_fixes_song_of_songs():
    assert normalize_ref('Song of songs 1:1') == 'Song of Songs 1:1'
    assert normalize_ref('Deuteronomy  22:4') == 'Deuteronomy 22:4'


def _heb():
    return {'Deuteronomy 1:1': [
        {'node': 1, 'lex': 'DBR/', 'word': 'דְּבָרִים', 'gloss': 'word',
         'feats': {'sp': 'subs', 'vs': 'NA', 'vt': 'NA', 'clause_typ': 'NmCl', 'obj_function': 'none', 'next_prep': 'none'}},
    ]}


def _lemmas():
    return [
        {'ref': 'Deuteronomy 1:1', 'position': 1, 'form': 'ܡܠܐ', 'norm': 'ܡܠܐ', 'lemma': 'ܡܠܬܐ', 'pos': 'noun',
         'source': 'sedra', 'rule': None, 'candidates': [{'lemma': 'ܡܠܬܐ', 'pos': 'noun', 'kaylo': None}], 'confidence': 1.0},
        {'ref': 'Deuteronomy 1:1', 'position': 2, 'form': 'ܥܠ', 'norm': 'ܥܠ', 'lemma': None, 'pos': None,
         'source': 'sedra', 'rule': None, 'candidates': [{'lemma': 'ܥܠ', 'pos': 'verb', 'kaylo': 'peal'}, {'lemma': 'ܥܠ', 'pos': 'preposition', 'kaylo': None}], 'confidence': 0.0},
        {'ref': 'Deuteronomy 1:1', 'position': 3, 'form': 'ܘܬܡܚܐ', 'norm': 'ܘܬܡܚܐ', 'lemma': None, 'pos': None,
         'source': 'unresolved', 'rule': None, 'candidates': [], 'confidence': 0.0},
        {'ref': 'Deuteronomy 9:9', 'position': 1, 'form': 'ܐ', 'norm': 'ܐ', 'lemma': 'ܐ', 'pos': None,
         'source': 'sedra', 'rule': None, 'candidates': [{'lemma': 'ܐ', 'pos': None, 'kaylo': None}], 'confidence': 1.0},
    ]


def test_build_parallel_keeps_only_shared_refs():
    par = build_parallel(_heb(), _lemmas())
    assert [p['ref'] for p in par] == ['Deuteronomy 1:1']


def test_build_parallel_alignment_units():
    par = build_parallel(_heb(), _lemmas())
    syr = par[0]['syr']
    assert syr[0]['units'] == ['ܡܠܬܐ']
    assert syr[1]['units'] == ['ܥܠ|verb', 'ܥܠ|preposition']   # candidate key = lemma|pos
    assert syr[2]['units'] == ['ܘܬܡܚܐ']                          # unresolved: surface form
    assert [s['position'] for s in syr] == [1, 2, 3]


from translation_technique.align import train_ibm1, symmetrize, align_corpus, pending_links


def _toy_parallel():
    """Ten verses; Hebrew lex A,B,C map to Syriac a,b,c; one ambiguous token."""
    heb_lex = ['A', 'B', 'C']
    syr = ['a', 'b', 'c']
    par = []
    for i in range(10):
        order = [0, 1, 2] if i % 2 == 0 else [1, 0, 2]
        hw = [{'node': 100 * i + k, 'lex': heb_lex[k], 'word': heb_lex[k], 'gloss': heb_lex[k].lower(),
               'feats': {'sp': 'subs', 'vs': 'NA', 'vt': 'NA', 'clause_typ': 'x', 'obj_function': 'none', 'next_prep': 'none'}}
              for k in order]
        sw = []
        for j, k in enumerate(order):
            if k == 2 and i < 8:
                sw.append({'position': j + 1, 'form': 'c', 'lemma': None, 'source': 'sedra',
                           'candidates': [{'lemma': 'c', 'pos': 'noun', 'kaylo': None}, {'lemma': 'c', 'pos': 'verb', 'kaylo': None}],
                           'units': ['c|noun', 'c|verb']})
            else:
                sw.append({'position': j + 1, 'form': syr[k], 'lemma': syr[k], 'source': 'sedra',
                           'candidates': [{'lemma': syr[k], 'pos': 'noun', 'kaylo': None}], 'units': [syr[k]]})
        par.append({'ref': f'Toy 1:{i + 1}', 'heb': hw, 'syr': sw})
    # verses 9,10 resolve c as noun, so EM should prefer c|noun for the ambiguous ones
    for p in par[8:]:
        for s in p['syr']:
            if s['form'] == 'c':
                s['lemma'] = 'c|noun'; s['units'] = ['c|noun']
    return par


def test_train_ibm1_learns_identity_mapping():
    par = _toy_parallel()
    pairs = [([[h['lex']] for h in p['heb']], [s['units'] for s in p['syr']]) for p in par]
    t = train_ibm1(pairs, iterations=5)
    assert t['a']['A'] > t['a']['B'] and t['b']['B'] > t['b']['A']


def test_symmetrize_intersection_then_grow():
    fwd = [[(0, 0, 0.9), (1, 1, 0.8), (2, 2, 0.4)]]
    bwd = [[(0, 0, 0.9), (1, 1, 0.7), (2, 1, 0.3)]]
    links = symmetrize(fwd, bwd)[0]
    assert (0, 0) in {(h, s) for h, s, _ in links}
    assert (1, 1) in {(h, s) for h, s, _ in links}
    # (2,2) is adjacent to (1,1) on the diagonal and present in one direction → grown in
    assert (2, 2) in {(h, s) for h, s, _ in links}


def test_align_corpus_rows_and_disambiguation():
    rows, dis = align_corpus(_toy_parallel(), iterations=5)
    r = next(x for x in rows if x['ref'] == 'Toy 1:1' and x['heb_lex'] == 'A')
    assert r['syr_lemma'] == 'a' and r['kind'] == 'one-one' and r['source'] == 'ibm1'
    assert list(r.keys()) == ['ref', 'heb_node', 'heb_lex', 'heb_word', 'heb_gloss', 'heb_feats',
                              'syr_position', 'syr_lemma', 'syr_source', 'prob', 'kind', 'source']
    assert dis[('Toy 1:1', 3)][0] == 'c' and dis[('Toy 1:1', 3)][1] == 'noun'
    assert 0 < dis[('Toy 1:1', 3)][2] <= 1


def test_rows_for_verse_null_and_kinds():
    from translation_technique.align import _rows_for_verse
    from collections import defaultdict
    par = _toy_parallel()
    p = par[0]
    p['syr'].append({'position': 4, 'form': 'z', 'lemma': 'z', 'source': 'rule',
                     'candidates': [{'lemma': 'z', 'pos': None, 'kaylo': None}], 'units': ['z']})
    t = defaultdict(lambda: defaultdict(lambda: 1e-6))
    rows, _ = _rows_for_verse(p, [(0, 0, 0.9), (1, 1, 0.9), (2, 2, 0.9)], t)
    nulls = [r for r in rows if r['kind'] == 'null']
    assert len(nulls) == 1 and nulls[0]['syr_lemma'] == 'z' and nulls[0]['heb_node'] is None
    assert not any(r['kind'] == 'null' and r['heb_lex'] in ('A', 'B', 'C') for r in rows)
    rows2, _ = _rows_for_verse(p, [(0, 0, 0.9), (0, 1, 0.6)], t)
    linked = [r for r in rows2 if r['kind'] != 'null']
    assert [r['kind'] for r in linked] == ['one-many', 'one-many']
    rows3, _ = _rows_for_verse(p, [(0, 0, 0.9), (1, 0, 0.6)], t)
    assert [r['kind'] for r in rows3 if r['kind'] != 'null'] == ['many-one', 'many-one']


def test_pending_links_threshold():
    rows = [{'kind': 'one-one', 'prob': 0.2}, {'kind': 'one-one', 'prob': 0.9}, {'kind': 'null', 'prob': 0.0}]
    assert pending_links(rows, 0.3) == [{'kind': 'one-one', 'prob': 0.2}]
