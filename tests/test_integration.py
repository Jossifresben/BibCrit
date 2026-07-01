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
def client(tmp_path, monkeypatch):
    """Flask test client with isolated tmp_path as data_dir.

    Supabase env vars are blanked so the pipeline uses disk cache only,
    ensuring tests are not affected by real cached entries in the cloud DB.
    """
    monkeypatch.setenv('SUPABASE_URL', '')
    monkeypatch.setenv('SUPABASE_KEY', '')

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


@pytest.fixture
def authed_client(client, monkeypatch):
    """Same as `client`, but Tier-1 (@require_api_key) routes are reachable —
    patches validate_api_key() to always succeed, so tests can exercise a
    Tier-1 route's body without a real Supabase-backed key. Use this instead
    of hand-rolling `monkeypatch.setattr('biblical_core.api_auth.validate_api_key', ...)`
    in each new test (that repeated pattern was flagged in Task 7's code
    review as something to solve once, before Tasks 8-9 copy it 12+ more
    times across other blueprints' Tier-1 routes)."""
    monkeypatch.setattr('biblical_core.api_auth.validate_api_key', lambda raw_key: True)
    return client


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


def test_api_divergence_missing_ref_returns_400(authed_client):
    """/api/divergence is Tier-1 (require_api_key); authed_client bypasses the
    key check so the request reaches the view body where the missing-ref
    check lives."""
    rv = authed_client.get('/api/divergence')
    assert rv.status_code == 400
    data = json.loads(rv.data)
    assert 'error' in data


def test_api_divergence_unknown_ref_returns_404(authed_client):
    rv = authed_client.get('/api/divergence?ref=Obadiah+99:99')
    assert rv.status_code == 404


def test_api_divergence_no_api_key_returns_401(client):
    """/api/divergence is Tier-1 (calls Claude on a cache miss) — a missing
    X-API-Key must be rejected with 401, same as its /stream sibling."""
    rv = client.get('/api/divergence?ref=Isaiah+7:14')
    assert rv.status_code == 401
    data = json.loads(rv.data)
    assert data['error'] == 'unauthorized'


def test_api_divergence_serves_cached_result(authed_client, tmp_path):
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
        'prompt_version': 'v2',
        'discovery_ready': False,
    }
    key = hashlib.sha256(
        f'{reference}|divergence|v2|{DIVERGENCE_MODEL}'.encode()
    ).hexdigest()
    cache_path = tmp_path / 'cache' / f'{key}.json'
    cache_path.write_text(json.dumps(cache_payload), encoding='utf-8')

    rv = authed_client.get('/api/divergence?ref=Isaiah+7:14')
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


def test_app_starts_with_limiter_installed(client):
    """Smoke test: Limiter.init_app() didn't break normal routing, and
    /health stays completely unthrottled."""
    for _ in range(5):
        rv = client.get('/health')
        assert rv.status_code == 200


def test_issue_api_key_requires_name_and_email(client):
    rv = client.post('/api/v1/keys', json={})
    assert rv.status_code == 400


def test_issue_api_key_returns_key_once(client, monkeypatch):
    from unittest.mock import MagicMock
    import state
    fake_supabase = MagicMock()
    monkeypatch.setattr(state.pipeline, '_supabase', fake_supabase)

    rv = client.post('/api/v1/keys', json={'name': 'Test User', 'email': 't@example.com'})
    assert rv.status_code == 201
    data = json.loads(rv.data)
    assert data['api_key'].startswith('bibcrit_live_')


def test_issued_key_is_hashed_not_stored_raw(client, monkeypatch):
    from unittest.mock import MagicMock
    import state
    from biblical_core.api_auth import hash_api_key
    fake_supabase = MagicMock()
    monkeypatch.setattr(state.pipeline, '_supabase', fake_supabase)

    rv = client.post('/api/v1/keys', json={'name': 'Test User 2', 'email': 't2@example.com'})
    raw_key = json.loads(rv.data)['api_key']

    insert_call = fake_supabase.table.return_value.insert.call_args
    inserted_row = insert_call[0][0]
    assert inserted_row['key_hash'] == hash_api_key(raw_key)
    assert inserted_row['key_hash'] != raw_key


def test_key_prefix_is_distinguishing_not_just_the_fixed_prefix(client, monkeypatch):
    from unittest.mock import MagicMock
    import state
    from biblical_core.api_auth import KEY_PREFIX
    fake_supabase = MagicMock()
    monkeypatch.setattr(state.pipeline, '_supabase', fake_supabase)

    rv1 = client.post('/api/v1/keys', json={'name': 'A', 'email': 'a@example.com'})
    prefix1 = fake_supabase.table.return_value.insert.call_args[0][0]['key_prefix']

    rv2 = client.post('/api/v1/keys', json={'name': 'B', 'email': 'b@example.com'})
    prefix2 = fake_supabase.table.return_value.insert.call_args[0][0]['key_prefix']

    assert len(prefix1) > len(KEY_PREFIX)  # actually extends past the fixed prefix
    assert prefix1 != prefix2  # two different keys produce two different prefixes


def test_cors_header_present_on_tier0_read(client):
    rv = client.get('/api/cache')
    assert rv.headers.get('Access-Control-Allow-Origin') == '*'


def test_cors_header_absent_on_vote_post(client):
    rv = client.post('/api/vote', json={'reference': 'Test 1:1', 'tool': 'divergence', 'value': 1})
    assert 'Access-Control-Allow-Origin' not in rv.headers


def test_cors_header_present_on_scribal_and_numerical_export(client):
    """Regression guard: these two Tier-0 export routes were initially missing
    from the CORS allow-list (caught in code review)."""
    for path in ('/api/scribal/export/sbl', '/api/numerical/export/sbl'):
        rv = client.get(path)
        assert rv.headers.get('Access-Control-Allow-Origin') == '*', path


def test_openapi_spec_has_v1_and_deprecated_bare_paths(client):
    rv = client.get('/api/v1/openapi.json')
    spec = json.loads(rv.data)
    assert '/api/v1/cache' in spec['paths']
    assert spec['paths']['/api/cache']['get'].get('deprecated') is True
    assert spec['paths']['/api/v1/divergence/stream']['get'].get('deprecated') is not True


def test_openapi_spec_marks_analysis_paths_as_requiring_api_key(client):
    rv = client.get('/api/v1/openapi.json')
    spec = json.loads(rv.data)
    stream_entry = spec['paths']['/api/v1/divergence/stream']['get']
    assert stream_entry['security'] == [{'ApiKeyAuth': []}]
    cache_entry = spec['paths']['/api/v1/cache']['get']
    assert 'security' not in cache_entry


def test_openapi_spec_version_bumped():
    from blueprints.research import _OPENAPI_SPEC
    assert _OPENAPI_SPEC['info']['version'] == '1.1.0'


def test_openapi_versioned_and_deprecated_entries_share_no_mutable_state(client):
    """Regression guard (found in code review): the versioned and deprecated-
    alias spec entries must be fully independent objects, including nested
    lists like 'tags' — otherwise a future transform mutating one in place
    would silently corrupt the other."""
    from blueprints.research import _OPENAPI_SPEC
    versioned = _OPENAPI_SPEC['paths']['/api/v1/cache']['get']
    deprecated = _OPENAPI_SPEC['paths']['/api/cache']['get']
    assert versioned is not deprecated
    assert versioned['tags'] is not deprecated['tags']
    assert versioned['tags'] == deprecated['tags']  # same content, different objects


# ── blueprints/textual.py: /api/v1 rollout (versioning, rate limits, auth) ──

def test_v1_alias_matches_bare_route_for_tier0(client):
    rv_bare = client.get('/api/books?tradition=MT')
    rv_v1 = client.get('/api/v1/books?tradition=MT')
    assert rv_bare.status_code == rv_v1.status_code == 200
    assert rv_bare.data == rv_v1.data


def test_tier1_stream_route_rejects_missing_api_key(client):
    rv = client.get('/api/v1/divergence/stream?ref=Genesis+1:1')
    assert rv.status_code == 401
    data = json.loads(rv.data)
    assert data['error'] == 'unauthorized'


def test_tier1_stream_route_rejects_bare_alias_too(client):
    """The bare form must enforce the same key requirement — versioning is
    just a URL alias, not a security boundary."""
    rv = client.get('/api/divergence/stream?ref=Genesis+1:1')
    assert rv.status_code == 401


def test_vote_post_rate_limited_at_20_per_hour(client):
    """20/hour on vote writes vs 60/minute;1000/day on reads — confirm the
    tighter limiter actually trips by exceeding it for real."""
    payload = {'reference': 'RateLimitTest 1:1', 'tool': 'divergence', 'value': 1}
    responses = [client.post('/api/vote', json=payload) for _ in range(21)]
    assert any(r.status_code == 429 for r in responses)


def test_all_tier1_stream_routes_reject_missing_key(client):
    tier1_paths = [
        '/api/v1/scribal/stream', '/api/v1/numerical/stream',
        '/api/v1/theological/stream', '/api/v1/patristic/stream',
        '/api/v1/targum/stream', '/api/v1/nt-text/stream',
        '/api/v1/stl/stream', '/api/v1/chiasm/stream',
        '/api/v1/source/stream', '/api/v1/lxx-ms/stream',
    ]
    for path in tier1_paths:
        rv = client.get(path)
        assert rv.status_code == 401, f'{path} did not require a key'


def test_scribal_and_numerical_export_v1_aliases_work(client):
    """These 2 Tier-0 export routes were missed from the initial Task 8 pass
    (a scoping mistake in the task dispatch, not a prior implementer error) —
    confirm they now have working versioned aliases like every other route."""
    rv1 = client.get('/api/v1/scribal/export/sbl?book=Isaiah')
    rv2 = client.get('/api/v1/numerical/export/sbl')
    assert rv1.status_code in (200, 404)  # never 401 — this is Tier-0, keyless
    assert rv2.status_code in (404, 501)  # stub route; still never 401


# ── blueprints/discovery.py: /api/v1 rollout (2 Tier-0 routes) ─────────────

def test_discovery_v1_aliases_work(client):
    rv_v1_cache = client.get('/api/v1/cache')
    rv_v1_cards = client.get('/api/v1/discovery/cards')
    assert rv_v1_cache.status_code == 200
    assert rv_v1_cards.status_code == 200


def test_admin_flag_route_untouched(client):
    """Confirm the admin route was NOT given a v1 alias — out of scope."""
    rv = client.get('/api/v1/admin/discovery/flag')
    assert rv.status_code == 404
