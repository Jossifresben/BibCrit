import os
import pytest
from translation_technique.store import TTStore

FIX = os.path.join(os.path.dirname(__file__), 'fixtures', 'tt')


@pytest.fixture
def store():
    return TTStore(FIX)


def test_unavailable_when_no_manifest(tmp_path):
    s = TTStore(str(tmp_path))
    assert s.available is False and s.books == [] and s.rows(None) == []


def test_manifest_version_books(store):
    assert store.available and store.version == '0.0.0-test'
    assert store.manifest['hash'] == 'deadbeef' and store.books == ['deuteronomy']


def test_rows_filtered_and_cached(store):
    rows = store.rows(['deuteronomy'])
    assert len(rows) == 6
    assert store.rows(['deuteronomy']) is rows
    assert store.rows(['genesis']) == []
    assert store.rows([]) == []


def test_lexemes_search(store):
    out = store.lexemes('jrd', None)
    assert out[0] == {'lex': 'JRD[', 'gloss': 'descend', 'word': 'יָרַד', 'count': 4}
    assert [o['lex'] for o in store.lexemes('come', None)] == ['BW>[']
    assert [o['lex'] for o in store.lexemes('ירד', ['deuteronomy'])] == ['JRD[']
    assert store.lexemes('zzz', None) == []
    assert store.lexemes('jrd', []) == []


def test_verse_rows(store):
    assert len(store.verse_rows('Deuteronomy 24:13')) == 4
    assert store.verse_rows('Deuteronomy 1:1') == []


def test_witnesses(store):
    assert store.witness_sigla() == ['9a1']
    assert store.witness_substitutions('9a1')[('Deuteronomy 22:4', 1)]['lemma'] == 'ܐܚܐ'
    assert store.witness_notes('9a1')[0]['keyed_from'] == 'test fixture'


def test_coverage_and_eval(store):
    assert store.coverage['deuteronomy']['tokens'] == 10
    assert store.eval is None


def test_manifest_dynamic_loading(tmp_path):
    """Manifest not cached when missing; detects file added after process start."""
    s = TTStore(str(tmp_path))
    assert s.manifest == {}
    # Write manifest after reading empty
    import json
    align_dir = tmp_path / 'align'
    align_dir.mkdir()
    manifest_file = align_dir / 'manifest.json'
    manifest_file.write_text(json.dumps({'version': '1.0.0', 'books': ['genesis']}))
    # Read again; should get populated manifest
    assert s.manifest == {'version': '1.0.0', 'books': ['genesis']}
