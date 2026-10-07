# tests/test_tt_align.py
import pytest
from translation_technique.align import normalize_ref, build_parallel, syr_units, book_stem, apply_disambiguations


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
            if k == 2:
                cands = [{'lemma': 'c', 'pos': 'noun', 'kaylo': None}, {'lemma': 'c', 'pos': 'verb', 'kaylo': None}]
                # verses 9,10: lemma already written back (pipeline state after a first run)
                row = {'position': j + 1, 'form': 'c', 'norm': 'c', 'lemma': 'c' if i >= 8 else None,
                       'source': 'sedra', 'candidates': cands}
            else:
                row = {'position': j + 1, 'form': syr[k], 'norm': syr[k], 'lemma': syr[k], 'source': 'sedra',
                       'candidates': [{'lemma': syr[k], 'pos': 'noun', 'kaylo': None}]}
            row['units'] = syr_units(row)
            sw.append(row)
        par.append({'ref': f'Toy 1:{i + 1}', 'heb': hw, 'syr': sw})
    return par


def test_train_ibm1_learns_identity_mapping():
    par = _toy_parallel()
    pairs = [([[h['lex']] for h in p['heb']], [s['units'] for s in p['syr']]) for p in par]
    t = train_ibm1(pairs, iterations=5)
    assert t['a']['A'] > t['a']['B'] and t['b']['B'] > t['b']['A']


def test_symmetrize_intersection_then_grow():
    # 3x3 toy; pairs are (heb, syr, p)
    fpost = [(0, 0, 0.9), (1, 1, 0.8), (2, 2, 0.4), (2, 1, 0.02)]
    bpost = [(0, 0, 0.9), (1, 1, 0.7), (2, 2, 0.45), (2, 1, 0.5)]
    fam = {(0, 0), (1, 1), (2, 2)}
    bam = {(0, 0), (1, 1), (2, 1)}
    links = symmetrize([(fpost, fam)], [(bpost, bam)])[0]
    got = {(h, s): p for h, s, p in links}
    assert (0, 0) in got and (1, 1) in got
    assert abs(got[(0, 0)] - 0.9) < 1e-9
    # (2,2): argmax only fwd, sqrt(0.4*0.45) >= 0.2 -> grown
    assert (2, 2) in got and abs(got[(2, 2)] - (0.4 * 0.45) ** 0.5) < 1e-9
    # (2,1): argmax only bwd, fwd posterior 0.02 -> sqrt(0.02*0.5)=0.1 < 0.2 -> rejected
    assert (2, 1) not in got


def test_syr_units_uses_candidates_even_when_lemma_set():
    from translation_technique.align import syr_units
    row = {'lemma': 'c', 'norm': 'c', 'candidates': [{'lemma': 'c', 'pos': 'noun', 'kaylo': None},
                                                     {'lemma': 'c', 'pos': 'verb', 'kaylo': None}]}
    assert syr_units(row) == ['c|noun', 'c|verb']


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


def test_disambiguation_chosen_once_per_token():
    from collections import defaultdict
    from translation_technique.align import _rows_for_verse
    cands = [{'lemma': 'c', 'pos': 'noun', 'kaylo': None}, {'lemma': 'c', 'pos': 'verb', 'kaylo': None}]
    feats = {}
    heb = [{'node': 1, 'lex': 'X', 'word': 'x', 'gloss': 'x', 'feats': feats},
           {'node': 2, 'lex': 'Y', 'word': 'y', 'gloss': 'y', 'feats': feats}]
    syr = [{'position': 1, 'form': 'c', 'lemma': None, 'source': 'sedra', 'candidates': cands,
            'units': ['c|noun', 'c|verb']}]
    t = defaultdict(lambda: defaultdict(float))
    t['c|noun']['X'] = 0.5; t['c|verb']['X'] = 0.1     # X alone prefers noun
    t['c|noun']['Y'] = 0.05; t['c|verb']['Y'] = 0.4    # Y alone prefers verb; sum favours noun (0.55 vs 0.5); last-link winner would be verb
    rows, dis = _rows_for_verse({'ref': 'T 1:1', 'heb': heb, 'syr': syr}, [(0, 0, 0.9), (1, 0, 0.8)], t)
    assert {r['syr_lemma'] for r in rows} == {'c'}
    lemma, pos, post = dis[('T 1:1', 1)]
    assert (lemma, pos) == ('c', 'noun') and abs(post - 0.55 / 1.05) < 1e-3


def test_align_corpus_idempotent_after_writeback():
    par = _toy_parallel()
    rows1, dis1 = align_corpus(par, iterations=5)
    lemma_rows = [{'ref': p['ref'], 'position': s['position'], 'lemma': s['lemma'], 'pos': None, 'confidence': None}
                  for p in par for s in p['syr']]
    apply_disambiguations(lemma_rows, dis1)
    lk = {(r['ref'], r['position']): r for r in lemma_rows}
    par2 = _toy_parallel()
    for p in par2:
        for s in p['syr']:
            s['lemma'] = lk[(p['ref'], s['position'])]['lemma']
            s['units'] = syr_units(s)
    rows2, dis2 = align_corpus(par2, iterations=5)
    assert rows1 == rows2 and dis1 == dis2


def test_apply_disambiguations_touches_only_three_fields():
    rows = [{'ref': 'T 1:1', 'position': 1, 'form': 'f', 'lemma': None, 'pos': None, 'confidence': None, 'x': 1},
            {'ref': 'T 1:1', 'position': 2, 'form': 'g', 'lemma': 'q', 'pos': 'noun', 'confidence': 1.0, 'x': 2}]
    before = [dict(r) for r in rows]
    assert apply_disambiguations(rows, {('T 1:1', 1): ('c', 'verb', 0.7)}) == 1
    assert rows[1] == before[1]
    assert {k for k in rows[0] if rows[0][k] != before[0][k]} == {'lemma', 'pos', 'confidence'}


def test_book_stem():
    assert book_stem('1 Samuel 1:1') == '1_samuel'
    assert book_stem('Song of Songs 1:1') == 'song_of_songs'
