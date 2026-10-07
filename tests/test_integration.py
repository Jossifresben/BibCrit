# tests/test_integration.py
"""Integration tests — Flask routes return expected shapes.

These tests use the Flask test client and do NOT call the real Claude API.
They verify route wiring, error handling, and cache behavior.
"""
import re
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


def test_api_divergence_no_api_key_returns_401(client, monkeypatch):
    monkeypatch.setenv('BIBCRIT_API_KEYS_ENFORCE', '1')
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


def test_tier1_stream_route_rejects_missing_api_key(client, monkeypatch):
    monkeypatch.setenv('BIBCRIT_API_KEYS_ENFORCE', '1')
    rv = client.get('/api/v1/divergence/stream?ref=Genesis+1:1')
    assert rv.status_code == 401
    data = json.loads(rv.data)
    assert data['error'] == 'unauthorized'


def test_tier1_stream_route_rejects_bare_alias_too(client, monkeypatch):
    monkeypatch.setenv('BIBCRIT_API_KEYS_ENFORCE', '1')
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


def test_all_tier1_stream_routes_reject_missing_key(client, monkeypatch):
    monkeypatch.setenv('BIBCRIT_API_KEYS_ENFORCE', '1')
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


# ── Design doc "Testing" section: gaps flagged by the final whole-branch
# review (rate-limit enforcement/isolation, OpenAPI validity gate) ─────────

def test_openapi_spec_validates_as_openapi_3_0(client):
    pytest.importorskip('openapi_spec_validator')
    from openapi_spec_validator import validate
    spec = client.get('/api/v1/openapi.json').get_json()
    validate(spec)  # raises on any schema violation


def test_tier0_read_rate_limited_at_60_per_minute(client):
    """60/minute;1000/day on Tier-0 reads — confirm the limiter actually
    trips by exceeding it for real."""
    responses = [client.get('/api/books?tradition=MT') for _ in range(61)]
    assert any(r.status_code == 429 for r in responses)


def test_tier1_per_key_rate_limit_isolated_between_keys(authed_client):
    """20/hour per key on Tier-1 routes — confirm one key's overuse doesn't
    burn another key's quota (the design doc's core Tier-1 fairness claim).
    Uses the bare (non-stream) /api/v1/divergence — same Tier-1 rate limit as
    its /stream sibling, but a plain JSON response, avoiding SSE-generator
    cleanup issues when driving 20+ rapid requests through a test client."""
    key_a_responses = [
        authed_client.get('/api/v1/divergence?ref=Genesis+1:1',
                          headers={'X-API-Key': 'bibcrit_live_test_key_a'})
        for _ in range(21)
    ]
    assert any(r.status_code == 429 for r in key_a_responses), \
        "key A should have tripped its own 20/hour limit"

    # A different key must be unaffected by key A's usage.
    key_b_response = authed_client.get(
        '/api/v1/divergence?ref=Genesis+1:1',
        headers={'X-API-Key': 'bibcrit_live_test_key_b'})
    assert key_b_response.status_code != 429, \
        "key B's quota must be isolated from key A's"


# ── Translation technique ────────────────────────────────────────────────────

@pytest.fixture
def tt_client(client, tmp_path, monkeypatch):
    import shutil
    import state as state_module
    from translation_technique.store import TTStore
    src = os.path.join(os.path.dirname(__file__), 'fixtures', 'tt')
    dst = tmp_path / 'tt'
    shutil.copytree(src, dst)
    monkeypatch.setattr(state_module, 'tt', TTStore(str(dst)))
    return client


def test_tt_page_renders_app_unlisted_noindex(tt_client):
    r = tt_client.get('/translation-technique')
    assert r.status_code == 200
    html = r.data.decode()
    assert re.search(r'id="tt-app"(?![^>]*\bhidden\b)', html)
    assert 'tt-gate' not in html
    assert '<meta name="robots" content="noindex, nofollow">' in html


def test_tt_empty_state_and_featured_links(tt_client):
    html = tt_client.get('/translation-technique').data.decode()
    assert 'id="tt-empty"' in html
    for lex in ('JRD[', 'BW&gt;[', 'NTN[', 'XRM['):
        assert f'data-lex="{lex}"' in html
    assert 'data-sort="prob"' in html and 'aria-sort="ascending"' in html
    assert 'id="tt-how"' in html and 'id="tt-findings"' in html


def test_tt_findings_for_jrd(tt_client, monkeypatch):
    import json
    import state as state_module
    import translation_technique.tables as tables
    root = os.path.dirname(os.path.dirname(__file__))
    monkeypatch.setattr(state_module, 'i18n', json.load(open(os.path.join(root, 'data', 'i18n.json'), encoding='utf-8')))
    monkeypatch.setattr(tables, 'MIN_SUMMARY_N', 3)   # the fixture has only 3 aligned JRD[ occurrences
    d = tt_client.get('/api/tt/table?lex=JRD[&books=deuteronomy').get_json()
    assert not d['summary']['too_few']
    assert 'ܟܒܫ' in d['findings'][0] and 'accounts for' in d['findings'][0]
    assert len(d['findings']) == 5
    html = tt_client.get('/translation-technique').data.decode()
    assert 'id="tt-findings"' in html and 'Computed from the table above; not an interpretation.' in html


def test_tt_lexeme_search_hebrew_and_bare_lex(tt_client):
    assert tt_client.get('/api/tt/lexemes?q=JRD').get_json()[0]['lex'] == 'JRD['
    assert tt_client.get('/api/tt/lexemes?q=%D7%99%D7%A8%D7%93').get_json()[0]['lex'] == 'JRD['


def test_tt_verse_badges_render(tt_client):
    r = tt_client.get('/translation-technique/verse/Deuteronomy 24:13')
    html = r.data.decode()
    assert r.status_code == 200          # MT text may be absent in the fixture corpus
    assert 'tradition-badge' in html and ('tt_verse_pesh' in html or 'Peshitta' in html)


def test_tt_query_params_become_data_attributes(tt_client):
    html = tt_client.get('/translation-technique?lex=JRD[&books=deuteronomy&facet=vs&witness=9a1').data.decode()
    assert 'data-lex="JRD["' in html and 'data-facet="vs"' in html and 'data-witness="9a1"' in html
    assert 'data-sel-books="deuteronomy"' in html


def test_tt_invalid_query_params_dropped(tt_client):
    html = tt_client.get('/translation-technique?lex=JRD[&books=nope&facet=animacy&witness=zzz').data.decode()
    assert 'data-facet=""' in html and 'data-witness=""' in html
    assert 'data-sel-books="deuteronomy"' in html
    html = tt_client.get('/translation-technique?facet=bogus').data.decode()
    assert 'data-facet=""' in html


def test_tt_witness_links_null_row_by_lex(tt_client):
    base = tt_client.get('/api/tt/table?lex=>X/&books=deuteronomy').get_json()
    assert base['occurrences'] == [] and base['distribution']['null_count'] == 1
    d = tt_client.get('/api/tt/table?lex=>X/&books=deuteronomy&witness=9a1').get_json()
    o = d['occurrences'][0]
    assert o['source'] == 'witness' and o['syr_source'] == 'witness' and o['prob'] == 1.0 and o['syr_position'] == 4
    assert o['syr_lemma'] == 'ܐܚܐ'


def test_tt_facet_options_use_ids_as_values(tt_client):
    html = tt_client.get('/translation-technique').data.decode()
    import re
    vals = re.findall(r'<select id="tt-facet".*?</select>', html, re.S)[0]
    values = re.findall(r'<option value="([^"]*)"', vals)
    assert values[0] == '' and 'vs' in values and 'obj_function' in values and 'animacy' in values
    assert re.search(r'<option value="animacy"[^>]*disabled', vals)


def test_tt_value_labels_and_no_bare_facet_ids(tt_client):
    d = tt_client.get('/api/tt/table?lex=JRD[&facet=vs').get_json()
    assert d['crosstab']['value_labels']['qal'] == 'Qal'
    html = tt_client.get('/translation-technique').data.decode()
    assert 'tt_facet_vs' in html and '>vs<' not in html and '>obj_function<' not in html
    assert '>vs\n' not in html and '>obj_function\n' not in html


def test_tt_page_spanish(tt_client):
    assert tt_client.get('/translation-technique?lang=es').status_code == 200


def test_tt_meta(tt_client):
    d = tt_client.get('/api/tt/meta').get_json()
    assert d['available'] is True and d['manifest']['hash'] == 'deadbeef'
    assert d['books'] == ['deuteronomy'] and d['sigla'] == ['9a1']
    assert d['facets']['animacy']['available'] is False
    assert d['coverage']['deuteronomy']['tokens'] == 10 and d['eval'] is None


def test_tt_lexemes(tt_client):
    d = tt_client.get('/api/tt/lexemes?q=jrd').get_json()
    assert d[0]['lex'] == 'JRD[' and d[0]['count'] == 4


def test_tt_table_distribution_and_crosstab(tt_client):
    d = tt_client.get('/api/tt/table?lex=JRD[&books=deuteronomy').get_json()
    assert d['distribution']['total'] == 4 and d['distribution']['null_count'] == 1
    assert d['distribution']['items'][0]['syr_lemma'] == 'ܟܒܫ'
    assert d['crosstab'] is None and d['manifest_hash'] == 'deadbeef'
    d = tt_client.get('/api/tt/table?lex=JRD[&facet=vs').get_json()
    assert d['crosstab']['matrix'] == [[2, 0], [0, 1]] and d['crosstab']['unreliable'] is True


def test_tt_table_witness(tt_client):
    d = tt_client.get('/api/tt/table?lex=JRD[&witness=9a1').get_json()
    assert any(i['syr_lemma'] == 'ܐܚܐ' for i in d['distribution']['items'])
    assert d['witness_notes'][0]['keyed_from'] == 'test fixture'


def test_tt_table_bad_facet_and_missing_lex(tt_client):
    assert tt_client.get('/api/tt/table?lex=JRD[&facet=animacy').status_code == 400
    assert tt_client.get('/api/tt/table').status_code == 400


def test_tt_csv_export(tt_client):
    r = tt_client.get('/api/tt/occurrences.csv?lex=JRD[')
    assert r.status_code == 200 and r.mimetype == 'text/csv'
    body = r.data.decode()
    assert body.startswith('# BibCrit translation technique export; version=0.0.0-test; manifest=deadbeef')
    assert 'Deuteronomy 22:4' in body and body.count('\n') >= 4


def test_tt_verse_view(tt_client):
    r = tt_client.get('/translation-technique/verse/Deuteronomy 24:13')
    assert r.status_code == 200 and 'ܟܒܫ' in r.data.decode()
    assert 'ܡܢ' in r.data.decode()
    assert tt_client.get('/translation-technique/verse/Deuteronomy 1:1').status_code == 404


def test_tt_unavailable_without_data(client, tmp_path, monkeypatch):
    import state as state_module
    from translation_technique.store import TTStore
    monkeypatch.setattr(state_module, 'tt', TTStore(str(tmp_path / 'nope')))
    assert client.get('/api/tt/meta').get_json()['available'] is False
    assert client.get('/translation-technique').status_code == 200


def test_tt_page_is_unlisted(client):
    assert '/translation-technique' not in client.get('/sitemap.xml').data.decode()
    assert '/translation-technique' not in client.get('/').data.decode()
    assert '/translation-technique' not in client.get('/guide').data.decode()
    assert '/translation-technique' not in client.get('/guide?lang=es').data.decode()


def test_tt_lang_is_whitelisted(tt_client):
    r = tt_client.get('/translation-technique?lang=x%22%20onmouseover%3D%22alert(1)')
    assert r.status_code == 200 and 'onmouseover' not in r.data.decode()


def test_tt_csv_hebrew_lex_ascii_filename(tt_client):
    r = tt_client.get('/api/tt/occurrences.csv?lex=%D7%90%D7%91')
    assert r.status_code == 200
    r.headers['Content-Disposition'].encode('ascii')


TT_KEYS = ['tt_gold_title', 'tt_gold_save', 'tt_gold_back', 'tt_gold_none', 'tt_page_title', 'tt_h1', 'tt_lede', 'tt_lexeme_label',
           'tt_lexeme_placeholder', 'tt_books_label', 'tt_facet_label', 'tt_facet_none', 'tt_witness_label',
           'tt_witness_main', 'tt_distribution_h2', 'tt_crosstab_h2', 'tt_occurrences_h2', 'tt_export_csv',
           'tt_model_share', 'tt_null_count', 'tt_unreliable', 'tt_methodology_h2', 'tt_coverage', 'tt_manifest',
           'tt_eval', 'tt_unevaluated', 'tt_facet_unavailable', 'tt_col_ref', 'tt_col_hebrew', 'tt_col_syriac',
           'tt_col_prob', 'tt_col_source', 'tt_verse_h1', 'tt_back',
           'tt_unaligned_syriac', 'tt_model_word', 'tt_col_lex', 'tt_manifest_label', 'tt_no_match', 'tt_banner', 'tt_empty',
           'tt_show_all', 'tt_all_books', 'tt_find_h', 'tt_find_caption', 'tt_find_dominant', 'tt_find_spread',
           'tt_find_null', 'tt_find_model', 'tt_find_facet', 'tt_find_facet_unreliable', 'tt_find_none',
           'tt_method_h', 'tt_method_p1', 'tt_method_p2', 'tt_method_p3', 'tt_method_p4', 'tt_method_p5',
           'tt_verse_mt', 'tt_verse_pesh', 'tt_sort_hint', 'tt_copy_link', 'tt_copied', 'tt_method_t1', 'tt_method_t2', 'tt_method_t3', 'tt_method_t4', 'tt_method_t5', 'tt_assoc_negligible', 'tt_assoc_weak', 'tt_assoc_moderate', 'tt_assoc_strong', 'tt_facet_vs', 'tt_facet_vs_help', 'tt_facet_vt', 'tt_facet_vt_help', 'tt_facet_clause_typ', 'tt_facet_clause_typ_help', 'tt_facet_obj_function', 'tt_facet_obj_function_help', 'tt_facet_next_prep', 'tt_facet_next_prep_help', 'tt_facet_book', 'tt_facet_book_help', 'tt_facet_animacy', 'tt_facet_animacy_help']


def test_tt_i18n_keys_present_in_both_languages():
    root = os.path.dirname(os.path.dirname(__file__))
    data = json.load(open(os.path.join(root, 'data', 'i18n.json'), encoding='utf-8'))
    for lang in ('en', 'es'):
        missing = [k for k in TT_KEYS if not data[lang].get(k)]
        assert not missing, f'{lang} missing {missing}'
    # the templated strings must keep their placeholders in both languages
    for lang in ('en', 'es'):
        assert '{share}' in data[lang]['tt_model_share']
        assert '{n}' in data[lang]['tt_null_count'] and '{total}' in data[lang]['tt_null_count']
        assert '{coverage}' in data[lang]['tt_coverage']
        assert '{hash}' in data[lang]['tt_manifest'] and '{version}' in data[lang]['tt_manifest']
        assert all(p in data[lang]['tt_eval'] for p in ('{precision}', '{recall}', '{agreement}', '{n}'))


def test_tt_gold_routes_hidden_without_env(tt_client, monkeypatch):
    monkeypatch.delenv('TT_GOLD_EDIT', raising=False)
    assert tt_client.get('/translation-technique/gold').status_code == 404


def test_tt_gold_form_and_post(tt_client, tmp_path, monkeypatch):
    monkeypatch.setenv('TT_GOLD_EDIT', '1')
    (tmp_path / 'tt' / 'gold').mkdir(exist_ok=True)
    (tmp_path / 'tt' / 'gold' / 'sample_refs.json').write_text('["Deuteronomy 24:13"]', encoding='utf-8')
    r = tt_client.get('/translation-technique/gold')
    assert r.status_code == 200 and 'Deuteronomy 24:13' in r.data.decode()
    r = tt_client.get('/translation-technique/gold/Deuteronomy 24:13')
    assert r.status_code == 200 and 'name="node_3"' in r.data.decode()
    r = tt_client.post('/translation-technique/gold/Deuteronomy 24:13', data={'node_3': '1', 'node_4': '', 'node_5': '2'})
    assert r.status_code == 302
    lines = (tmp_path / 'tt' / 'gold' / 'deuteronomy_sample.jsonl').read_text(encoding='utf-8').strip().split('\n')
    rows = [json.loads(l) for l in lines]
    assert {(x['heb_node'], x['syr_position']) for x in rows} == {(3, 1), (4, None), (5, 2)}
    assert all(x['reader'] == 'jossi' for x in rows)


def _gold_setup(tt_client, tmp_path, monkeypatch):
    monkeypatch.setenv('TT_GOLD_EDIT', '1')
    (tmp_path / 'tt' / 'gold').mkdir(exist_ok=True)
    (tmp_path / 'tt' / 'gold' / 'sample_refs.json').write_text('["Deuteronomy 24:13"]', encoding='utf-8')
    return tmp_path / 'tt' / 'gold' / 'deuteronomy_sample.jsonl'


def test_tt_gold_no_anchoring_and_dedupe(tt_client, tmp_path, monkeypatch):
    import re
    gpath = _gold_setup(tt_client, tmp_path, monkeypatch)
    html = tt_client.get('/translation-technique/gold/Deuteronomy 24:13').data.decode()
    assert len(re.findall(r'<select name="node_', html)) == 3
    assert 'selected' not in html
    assert 'aligner: #1' in html
    tt_client.post('/translation-technique/gold/Deuteronomy 24:13', data={'node_3': '2', 'node_4': '', 'node_5': '1'})
    html = tt_client.get('/translation-technique/gold/Deuteronomy 24:13').data.decode()
    assert html.count('selected') == 2


def test_tt_gold_post_validation_writes_nothing(tt_client, tmp_path, monkeypatch):
    gpath = _gold_setup(tt_client, tmp_path, monkeypatch)
    url = '/translation-technique/gold/Deuteronomy 24:13'
    assert tt_client.post(url, data={'node_3': 'abc'}).status_code == 400
    assert tt_client.post(url, data={'node_3': '99'}).status_code == 400
    assert tt_client.post(url, data={'node_3': '-1'}).status_code == 400
    assert not gpath.exists()


def test_tt_gold_post_replaces_jossi_keeps_model(tt_client, tmp_path, monkeypatch):
    gpath = _gold_setup(tt_client, tmp_path, monkeypatch)
    model = {'ref': 'Deuteronomy 24:13', 'heb_node': 3, 'syr_position': 1, 'reader': 'model', 'agreed': None}
    gpath.write_text(json.dumps(model) + '\n', encoding='utf-8')
    url = '/translation-technique/gold/Deuteronomy 24:13'
    tt_client.post(url, data={'node_3': '1'})
    tt_client.post(url, data={'node_3': '2', 'node_5': '1'})
    rows = [json.loads(l) for l in gpath.read_text(encoding='utf-8').strip().split('\n')]
    assert sum(r['reader'] == 'model' for r in rows) == 1
    j = [r for r in rows if r['reader'] == 'jossi']
    assert len(j) == 3 and {(r['heb_node'], r['syr_position']) for r in j} == {(3, 2), (4, None), (5, 1)}


def test_tt_gold_post_hidden_without_env(tt_client, monkeypatch):
    monkeypatch.delenv('TT_GOLD_EDIT', raising=False)
    assert tt_client.post('/translation-technique/gold/Deuteronomy 24:13', data={'node_3': '1'}).status_code == 404


def test_tt_findings_p_clause_has_no_equals_before_less_than(tt_client, monkeypatch):
    import state as state_module
    from blueprints.translation_technique import _findings
    with open(os.path.join(os.path.dirname(__file__), '..', 'data', 'i18n.json'), encoding='utf-8') as fh:
        monkeypatch.setattr(state_module, 'i18n', json.load(fh))
    sm = {'too_few': False, 'dominant': {'lemma': 'x', 'share': 0.5}, 'n': 10, 'singletons': 2, 'distinct': 3,
          'null_count': 1, 'model_share': 0.0}
    for p, want in ((0.0001, 'p < 0.001'), (0.0421, 'p = 0.042')):
        sm['facet'] = {'facet': 'vt', 'v': 0.4, 'p': p}
        out = ' '.join(_findings(sm, 'en'))
        assert want in out and 'p = <' not in out
