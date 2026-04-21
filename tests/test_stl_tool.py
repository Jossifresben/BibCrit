"""Tests for the Second Temple Literature Bridge tool."""
import pytest
from biblical_core.claude_pipeline import (
    STL_MODEL, _STL_SYSTEM, ClaudePipeline,
)


def make_pipeline(tmp_path) -> ClaudePipeline:
    return ClaudePipeline(data_dir=str(tmp_path), api_key='', cap_usd=5.0)


# ── Constants ────────────────────────────────────────────────────────────────

def test_stl_constants_importable():
    assert isinstance(STL_MODEL, str) and STL_MODEL
    assert isinstance(_STL_SYSTEM, str) and 'second temple' in _STL_SYSTEM.lower()


# ── analyze_stl ──────────────────────────────────────────────────────────────

def test_analyze_stl_no_client_returns_error(tmp_path):
    p = make_pipeline(tmp_path)
    result = p.analyze_stl('Genesis 6:1-4')
    assert 'error' in result
    assert result['allusions'] == []
    assert result['synthesis'] == ''


def test_analyze_stl_cache_roundtrip(tmp_path):
    p = make_pipeline(tmp_path)
    fake = {
        'reference': 'Genesis 6:1-4',
        'synthesis': 'The Watchers passage is the single most-cited canonical text in Second Temple literature.',
        'allusions': [
            {
                'stl_work': '1_enoch',
                'stl_passage': '1 En 6:1-2',
                'stl_content': 'The Watchers see the daughters of men and descend.',
                'allusion_type': 'allusion',
                'directionality': 'canonical_to_stl',
                'confidence': 0.97,
                'canonical_element': 'sons of God / daughters of men',
                'scholarly_note': 'Nickelsburg (2001, 165) argues 1 En 6-11 is a haggadic expansion of Gen 6:1-4.',
                'relevance_to_dss': 'The Book of Giants at Qumran elaborates the same tradition.',
                'relevance_to_nt': 'Jude 6 and 2 Pet 2:4 reflect the same tradition.',
            }
        ],
        'works_covered': {
            '1_enoch':  {'present': True,  'passage_count': 3},
            'jubilees': {'present': True,  'passage_count': 1},
            'sirach':   {'present': False, 'passage_count': 0},
            '4_ezra':   {'present': False, 'passage_count': 0},
            'tobit':    {'present': False, 'passage_count': 0},
        },
        'dss_significance': 'The Book of Giants (4Q530-532) is a direct Qumran elaboration.',
        'nt_significance': 'Jude 6 and 2 Peter 2:4 allude to the Watcher tradition.',
        'directionality_summary': 'STL texts consistently depend on and expand the canonical passage.',
        'assessment': {
            'title': 'Genesis 6:1-4 as the seed of Second Temple angelology',
            'reasoning': 'This passage generated more STL commentary than any other four verses in the canon.',
            'plain': 'Ancient Jewish writers were fascinated by this story and wrote about it extensively.',
            'confidence': 0.95,
            'next_steps': 'Compare with 4Q201-202 (Aramaic Enoch fragments) for textual variants.',
        },
        'citations': {
            'sbl': 'George W. E. Nickelsburg, 1 Enoch 1 (Minneapolis: Fortress, 2001), 165–99.',
            'bibtex': '@book{nickelsburg2001, author={Nickelsburg, George W. E.}, title={1 Enoch 1}, year={2001}}',
        },
        'discovery_ready': True,
    }
    p.save_cache('Genesis 6:1-4', 'stl', 'v1', STL_MODEL, fake)
    cached = p.get_cached('Genesis 6:1-4', 'stl', 'v1', STL_MODEL)
    assert cached is not None
    assert cached['allusions'][0]['stl_work'] == '1_enoch'
    assert cached['works_covered']['1_enoch']['present'] is True
    assert cached['allusions'][0]['confidence'] == 0.97


def test_analyze_stl_budget_cap_returns_error(tmp_path):
    p = ClaudePipeline(data_dir=str(tmp_path), api_key='fake-key', cap_usd=0.0)
    result = p.analyze_stl('Daniel 7:13')
    assert 'error' in result
    assert 'budget' in result['error'].lower() or 'cap' in result['error'].lower()
    assert result['allusions'] == []


# ── stream_stl ───────────────────────────────────────────────────────────────

def test_stream_stl_no_client_yields_error(tmp_path):
    p = make_pipeline(tmp_path)
    items = list(p.stream_stl('Genesis 6:1-4'))
    assert len(items) == 1
    # Last item must be the epilogue: (None, dict_with_error)
    assert items[-1][0] is None
    assert 'error' in items[-1][1]


def test_stream_stl_cache_hit_yields_sections_then_epilogue(tmp_path):
    p = make_pipeline(tmp_path)
    fake = {
        'reference': 'Psalm 82:1',
        'synthesis': 'The divine council scene.',
        'allusions': [],
        'works_covered': {'1_enoch': {'present': False, 'passage_count': 0}},
        'dss_significance': None,
        'nt_significance': None,
        'directionality_summary': 'No direct dependency found.',
        'assessment': {'title': 'Ps 82 in STL', 'reasoning': '', 'plain': '', 'confidence': 0.5, 'next_steps': ''},
        'citations': {'sbl': '', 'bibtex': ''},
        'discovery_ready': False,
    }
    p.save_cache('Psalm 82:1', 'stl', 'v1', STL_MODEL, fake)
    items = list(p.stream_stl('Psalm 82:1'))
    keys = [k for k, _ in items]
    # Must end with None epilogue
    assert keys[-1] is None
    # Synthesis section must appear
    assert 'synthesis' in keys
    assert items[-1][1] == fake  # epilogue payload must equal the cached dict
    assert len([k for k, _ in items if k is not None]) >= 1  # at least one section yielded


# ── Blueprint routes ──────────────────────────────────────────────────────────

@pytest.fixture
def client(tmp_path, monkeypatch):
    """Flask test client with isolated tmp_path as data_dir.

    Supabase env vars are blanked so the pipeline uses disk cache only,
    ensuring tests are not affected by real cached entries in the cloud DB.
    """
    monkeypatch.setenv('SUPABASE_URL', '')
    monkeypatch.setenv('SUPABASE_KEY', '')

    (tmp_path / 'cache').mkdir()
    (tmp_path / 'prompts').mkdir()

    import app as app_module
    app_module.DATA_DIR = str(tmp_path)
    app_module._initialized = False

    import state as state_module
    state_module.pipeline = None

    app_module.app.config['TESTING'] = True
    with app_module.app.test_client() as c:
        # Force init with new data dir
        with app_module.app.app_context():
            app_module._init()
        yield c


def test_stl_page_returns_200(client):
    resp = client.get('/stl')
    assert resp.status_code == 200
    assert b'stl' in resp.data.lower() or b'second temple' in resp.data.lower()


def test_stl_stream_missing_ref_returns_error_event(client):
    resp = client.get('/api/stl/stream')
    assert resp.status_code == 200
    assert b'error' in resp.data
