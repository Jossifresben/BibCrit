# tests/test_integration.py
"""Integration tests — Flask routes return expected shapes.

These tests use the Flask test client and do NOT call the real Claude API.
They verify route wiring, error handling, and cache behavior.
"""
import json
import os
import shutil
import pytest


@pytest.fixture
def client(tmp_path):
    """Flask test client with isolated tmp_path as data_dir."""
    # Copy corpus fixtures into tmp_path
    fixtures = os.path.join(os.path.dirname(__file__), 'fixtures')
    corpora_src = os.path.join(fixtures, 'corpora')
    corpora_dst = tmp_path / 'corpora'
    shutil.copytree(corpora_src, corpora_dst)
    (tmp_path / 'cache').mkdir()
    (tmp_path / 'prompts').mkdir()

    import app as app_module
    app_module.DATA_DIR = str(tmp_path)
    app_module._initialized = False

    import state as state_module
    state_module.corpus = None
    state_module.pipeline = None
    state_module.i18n = {}

    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        # Force init with new data dir
        with app_module.app.app_context():
            app_module._init()
        yield c


def test_health_route(client):
    rv = client.get('/health')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data['status'] == 'ok'


def test_divergence_page_loads(client):
    rv = client.get('/divergence')
    assert rv.status_code == 200
    assert b'Divergence' in rv.data


def test_api_books_returns_list(client):
    rv = client.get('/api/books?tradition=MT')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'books' in data
    assert isinstance(data['books'], list)
    assert 'Isaiah' in data['books']


def test_api_chapters_for_isaiah(client):
    rv = client.get('/api/chapters?book=Isaiah&tradition=MT')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 7 in data['chapters']


def test_api_verses_for_isaiah_7(client):
    rv = client.get('/api/verses?book=Isaiah&chapter=7&tradition=MT')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 14 in data['verses']


def test_api_divergence_missing_ref_returns_400(client):
    rv = client.get('/api/divergence')
    assert rv.status_code == 400
    data = json.loads(rv.data)
    assert 'error' in data


def test_api_divergence_unknown_ref_returns_404(client):
    rv = client.get('/api/divergence?ref=Obadiah+99:99')
    assert rv.status_code == 404


def test_api_divergence_no_api_key_returns_error_in_body(client):
    rv = client.get('/api/divergence?ref=Isaiah+7:14')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    # Without API key returns error dict (200 status, error field)
    assert 'error' in data or 'divergences' in data


def test_api_divergence_serves_cached_result(client, tmp_path):
    """If a valid cache entry exists, /api/divergence returns it without calling Claude."""
    import hashlib
    from biblical_core.claude_pipeline import DIVERGENCE_MODEL

    reference = 'Isaiah 7:14'
    cache_payload = {
        'divergences': [{'mt_word': 'הָעַלְמָה', 'lxx_word': 'παρθένος',
                         'divergence_type': 'theological_tendency', 'confidence': 0.82,
                         'hypotheses': [], 'dss_witness': None, 'citations': [],
                         'analysis_technical': 'Test.', 'analysis_plain': 'Test plain.'}],
        'summary_technical': '',
        'summary_plain': '',
        'cached_at': '2026-01-01T00:00:00',
        'model_version': DIVERGENCE_MODEL,
        'prompt_version': 'v1',
        'discovery_ready': False,
    }
    key = hashlib.sha256(
        f'{reference}|divergence|v1|{DIVERGENCE_MODEL}'.encode()
    ).hexdigest()
    cache_path = tmp_path / 'cache' / f'{key}.json'
    cache_path.write_text(json.dumps(cache_payload), encoding='utf-8')

    rv = client.get('/api/divergence?ref=Isaiah+7:14')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data.get('divergences', [{}])[0].get('mt_word') == 'הָעַלְמָה'


def test_api_budget_returns_shape(client):
    rv = client.get('/api/budget')
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert 'spend_usd' in data
    assert 'cap_usd' in data
    assert 'pct' in data


def test_discovery_page_loads(client):
    rv = client.get('/discovery')
    assert rv.status_code == 200
    assert b'Discovery' in rv.data


def test_export_sbl_no_cache_returns_404(client):
    rv = client.get('/api/divergence/export/sbl?ref=Isaiah+7:14')
    assert rv.status_code == 404


def test_export_bibtex_no_cache_returns_404(client):
    rv = client.get('/api/divergence/export/bibtex?ref=Isaiah+7:14')
    assert rv.status_code == 404
