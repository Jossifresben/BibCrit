import importlib.util
import json
import os
import shutil

import pytest
import requests

from translation_technique import lemmas
from translation_technique.lemmas import SedraCache, SedraUnavailable, build_lemma_rows, sedra_fetch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location('tt_build_lemmas', os.path.join(ROOT, 'scripts', 'tt_build_lemmas.py'))
script = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(script)

FIXTURE_CORPUS = os.path.join(os.path.dirname(__file__), 'fixtures', 'corpora', 'pesh_etcbc')


class _Resp:
    def __init__(self, status, payload=None):
        self.status_code = status
        self._payload = payload

    def json(self):
        return self._payload


def _patch_get(monkeypatch, resp=None, exc=None):
    def fake_get(url, timeout=None):
        if exc:
            raise exc
        return resp
    monkeypatch.setattr(requests, 'get', fake_get)


def test_fetch_404_is_none(monkeypatch):
    _patch_get(monkeypatch, _Resp(404))
    assert sedra_fetch('x') is None


def test_fetch_empty_list_is_none(monkeypatch):
    _patch_get(monkeypatch, _Resp(200, []))
    assert sedra_fetch('x') is None


def test_fetch_429_raises_unavailable(monkeypatch):
    _patch_get(monkeypatch, _Resp(429))
    with pytest.raises(SedraUnavailable):
        sedra_fetch('x')


def test_fetch_request_exception_raises_unavailable(monkeypatch):
    _patch_get(monkeypatch, exc=requests.ConnectionError('boom'))
    with pytest.raises(SedraUnavailable):
        sedra_fetch('x')


def test_offline_unknown_form_is_unresolved_and_cache_untouched(tmp_path):
    p = tmp_path / 'c.json'
    cache = SedraCache(str(p), fetcher=None)
    rows = build_lemma_rows([{'reference': 'Deuteronomy 1:1', 'position': '1', 'word_text': 'ܘܬܡܚܐ'}], cache)
    assert rows[0]['source'] == 'unresolved'
    assert not p.exists()
    assert cache.stats() == {'hits': 0, 'misses': 0}


def _tokens(*forms):
    return [{'reference': 'Deuteronomy 1:1', 'position': str(i + 1), 'word_text': w} for i, w in enumerate(forms)]


def test_prefetch_reports_unfetched_after_three_attempts(tmp_path, monkeypatch):
    sleeps = []
    monkeypatch.setattr(script.time, 'sleep', lambda s: sleeps.append(s))
    attempts = {}

    def fetch(norm):
        attempts[norm] = attempts.get(norm, 0) + 1
        if norm == 'ܡܢ':
            raise SedraUnavailable('down')
        return [{'lemma': norm, 'pos': 'noun', 'kaylo': None}]
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=fetch, delay=0)
    n = script.prefetch(_tokens('ܡܢ', 'ܡܪܝܐ', 'ܫܡܫܐ'), cache, workers=2)
    assert n == 1
    assert attempts['ܡܢ'] == 3
    assert not cache.has('ܡܢ')
    assert cache.has('ܡܪܝܐ') and cache.has('ܫܡܫܐ')
    assert sleeps == [5.0, 5.0]


def test_build_book_not_written_when_unfetched(tmp_path, monkeypatch):
    monkeypatch.setattr(script.time, 'sleep', lambda s: None)
    corpus = tmp_path / 'corpus'
    shutil.copytree(FIXTURE_CORPUS, corpus)
    first_form = None
    import csv
    with open(corpus / 'deuteronomy.csv', encoding='utf-8') as fh:
        first_form = lemmas.normalize_form(next(csv.DictReader(fh))['word_text'])

    def fetch(norm):
        if norm == first_form:
            raise SedraUnavailable('down')
        return None
    cache = SedraCache(str(tmp_path / 'c.json'), fetcher=fetch, delay=0)
    tt = tmp_path / 'tt'
    cov = script.build_book('deuteronomy', cache, workers=2, corpus_dir=str(corpus), tt_dir=str(tt))
    assert cov is None
    assert not (tt / 'lemmas' / 'deuteronomy.jsonl').exists()
