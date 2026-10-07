from translation_technique.lemmas import normalize_form, strip_affixes, AFFIX_RULES


def test_normalize_strips_seyame_and_dots():
    assert normalize_form('ܬܪ̈ܥܝܗܝܢ') == 'ܬܪܥܝܗܝܢ'
    assert normalize_form('ܕܩ̇ܛܠ') == 'ܕܩܛܠ'
    assert normalize_form('ܥܝܢܗ̇') == 'ܥܝܢܗ'


def test_normalize_leaves_plain_forms_alone():
    assert normalize_form('ܡܪܝܐ') == 'ܡܪܝܐ'


def test_normalize_strips_surrounding_whitespace():
    assert normalize_form(' ܡܢ ') == 'ܡܢ'


def test_strip_affixes_proclitic_waw_then_dalath():
    cands = strip_affixes('ܘܕܫܡܫܐ')
    ids = [c[0] for c in cands]
    forms = [c[1] for c in cands]
    assert 'ܕܫܡܫܐ' in forms          # after stripping ܘ
    assert 'ܫܡܫܐ' in forms           # after stripping ܘ then ܕ
    assert ids[0] == 'pre_waw'


def test_strip_affixes_suffix():
    cands = strip_affixes('ܥܝܢܗ')
    assert ('suf_h', 'ܥܝܢ') in cands


def test_strip_affixes_never_returns_empty_or_single_letter():
    for _, form in strip_affixes('ܘܠ'):
        assert len(form) >= 2


def test_affix_rules_order_is_waw_dalath_lamadh_beth_first():
    kinds = [(r[0], r[1]) for r in AFFIX_RULES[:4]]
    assert kinds == [('pre_waw', 'pre'), ('pre_dalath', 'pre'), ('pre_lamadh', 'pre'), ('pre_beth', 'pre')]


import json
import os
import pytest
from translation_technique.lemmas import SedraCache, build_lemma_rows, coverage, write_jsonl, read_jsonl

FIX = os.path.join(os.path.dirname(__file__), 'fixtures', 'sedra_sample.json')


def _fake_fetcher():
    data = json.load(open(FIX, encoding='utf-8'))
    calls = []

    def fetch(norm):
        calls.append(norm)
        raw = data.get(norm)
        if not raw:
            return None
        return [{'lemma': e['stem'], 'pos': e.get('category'), 'kaylo': e.get('kaylo')} for e in raw]
    fetch.calls = calls
    return fetch


def test_cache_fetches_once_then_serves_from_memory(tmp_path):
    fetch = _fake_fetcher()
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=fetch, delay=0)
    assert cache.get('ܡܪܝܐ')[0]['lemma'] == 'ܡܪܝܐ'
    assert cache.get('ܡܪܝܐ')[0]['lemma'] == 'ܡܪܝܐ'
    assert fetch.calls == ['ܡܪܝܐ']


def test_cache_persists_misses_and_reloads(tmp_path):
    p = str(tmp_path / 'c.json')
    fetch = _fake_fetcher()
    cache = SedraCache(p, fetcher=fetch, delay=0)
    assert cache.get('ܥܝܢܗ') is None
    cache.save()
    cache2 = SedraCache(p, fetcher=fetch, delay=0)
    assert cache2.get('ܥܝܢܗ') is None
    assert fetch.calls == ['ܥܝܢܗ']          # not fetched again
    assert cache2.stats() == {'hits': 0, 'misses': 1}


def test_cache_without_fetcher_raises_on_unknown(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=None)
    with pytest.raises(KeyError):
        cache.get('ܡܪܝܐ')


def _tokens(*pairs):
    return [{'reference': 'Deuteronomy 1:1', 'position': str(i + 1), 'word_text': w}
            for i, w in enumerate(pairs)]


def test_build_rows_single_candidate_is_sedra_confidence_1(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=_fake_fetcher(), delay=0)
    rows = build_lemma_rows(_tokens('ܡܪܝܐ'), cache)
    r = rows[0]
    assert r['source'] == 'sedra' and r['lemma'] == 'ܡܪܝܐ' and r['pos'] == 'noun'
    assert r['confidence'] == 1.0 and r['rule'] is None
    assert r['position'] == 1 and r['norm'] == 'ܡܪܝܐ'


def test_build_rows_ambiguous_keeps_candidates_and_null_lemma(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=_fake_fetcher(), delay=0)
    r = build_lemma_rows(_tokens('ܥܠ'), cache)[0]
    assert r['source'] == 'sedra' and r['lemma'] is None and r['pos'] is None
    assert len(r['candidates']) == 2 and r['confidence'] == 0.0


def test_build_rows_rule_hit_records_rule(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=_fake_fetcher(), delay=0)
    r = build_lemma_rows(_tokens('ܕܫܡܫܐ'), cache)[0]
    assert r['source'] == 'rule' and r['rule'] == 'pre_dalath' and r['lemma'] == 'ܫܡܫܐ'


def test_build_rows_normalizes_before_lookup(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=_fake_fetcher(), delay=0)
    r = build_lemma_rows(_tokens('ܥܝܢܗ̇'), cache)[0]
    assert r['norm'] == 'ܥܝܢܗ' and r['source'] == 'rule' and r['rule'] == 'suf_h'


def test_build_rows_unresolved(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=_fake_fetcher(), delay=0)
    r = build_lemma_rows(_tokens('ܘܬܡܚܐ'), cache)[0]
    assert r['source'] == 'unresolved' and r['lemma'] is None and r['candidates'] == []


def test_row_key_order_matches_spec(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=_fake_fetcher(), delay=0)
    r = build_lemma_rows(_tokens('ܡܪܝܐ'), cache)[0]
    assert list(r.keys()) == ['ref', 'position', 'form', 'norm', 'lemma', 'pos', 'source', 'rule', 'candidates', 'confidence']


def test_coverage_shares(tmp_path):
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=_fake_fetcher(), delay=0)
    rows = build_lemma_rows(_tokens('ܡܪܝܐ', 'ܡܪܝܐ', 'ܕܫܡܫܐ', 'ܘܬܡܚܐ'), cache)
    c = coverage(rows)
    assert c['tokens'] == 4 and c['types'] == 3
    assert c['by_source_tokens'] == {'sedra': 0.5, 'rule': 0.25, 'unresolved': 0.25}
    assert c['by_source_types']['sedra'] == pytest.approx(1 / 3)


def test_jsonl_roundtrip(tmp_path):
    p = str(tmp_path / 'x.jsonl')
    write_jsonl(p, [{'a': 1}, {'b': 'ܥ'}])
    assert read_jsonl(p) == [{'a': 1}, {'b': 'ܥ'}]
