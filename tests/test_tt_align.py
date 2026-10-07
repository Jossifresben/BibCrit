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
