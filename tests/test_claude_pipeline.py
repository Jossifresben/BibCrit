# tests/test_claude_pipeline.py
import json
import os
from datetime import datetime
import pytest
from biblical_core.claude_pipeline import ClaudePipeline, DIVERGENCE_MODEL


def make_pipeline(tmp_path) -> ClaudePipeline:
    return ClaudePipeline(data_dir=str(tmp_path), api_key='', cap_usd=5.0)


def test_cache_key_is_deterministic(tmp_path):
    p = make_pipeline(tmp_path)
    k1 = p._cache_key('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL)
    k2 = p._cache_key('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL)
    assert k1 == k2


def test_different_model_gives_different_key(tmp_path):
    p = make_pipeline(tmp_path)
    k1 = p._cache_key('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL)
    k2 = p._cache_key('Isaiah 7:14', 'divergence', 'v1', 'claude-opus-4-5')
    assert k1 != k2


def test_different_passage_gives_different_key(tmp_path):
    p = make_pipeline(tmp_path)
    k1 = p._cache_key('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL)
    k2 = p._cache_key('Genesis 1:1', 'divergence', 'v1', DIVERGENCE_MODEL)
    assert k1 != k2


def test_cache_miss_returns_none(tmp_path):
    p = make_pipeline(tmp_path)
    result = p.get_cached('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL)
    assert result is None


def test_cache_roundtrip(tmp_path):
    p = make_pipeline(tmp_path)
    data = {'divergences': [{'mt_word': 'הָעַלְמָה', 'lxx_word': 'παρθένος'}]}
    p.save_cache('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL, data)
    cached = p.get_cached('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL)
    assert cached is not None
    assert cached['divergences'][0]['mt_word'] == 'הָעַלְמָה'


def test_save_cache_adds_metadata(tmp_path):
    p = make_pipeline(tmp_path)
    data = {'divergences': []}
    p.save_cache('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL, data)
    cached = p.get_cached('Isaiah 7:14', 'divergence', 'v1', DIVERGENCE_MODEL)
    assert 'cached_at' in cached
    assert cached['model_version'] == DIVERGENCE_MODEL
    assert cached['discovery_ready'] is False


def test_budget_starts_at_zero(tmp_path):
    p = make_pipeline(tmp_path)
    budget = p.get_budget()
    assert budget['spend_usd'] == 0.0
    assert budget['cap_usd'] == 5.0


def test_record_spend_accumulates(tmp_path):
    p = make_pipeline(tmp_path)
    p.record_spend(1.50)
    p.record_spend(0.75)
    budget = p.get_budget()
    assert abs(budget['spend_usd'] - 2.25) < 0.001


def test_budget_resets_on_new_month(tmp_path):
    p = make_pipeline(tmp_path)
    p.record_spend(3.00)
    budget = p.get_budget()
    budget['month'] = '2020-01'
    with open(p._budget_path, 'w') as f:
        json.dump(budget, f)
    p.record_spend(1.00)
    budget = p.get_budget()
    assert budget['spend_usd'] == 1.00


def test_load_prompt_returns_empty_if_missing(tmp_path):
    p = make_pipeline(tmp_path)
    result = p.load_prompt('divergence', 'v1')
    assert result == ''


def test_load_prompt_reads_file(tmp_path):
    prompts_dir = tmp_path / 'prompts'
    prompts_dir.mkdir()
    (prompts_dir / 'divergence_v1.txt').write_text('Hello {{REFERENCE}}')
    p = make_pipeline(tmp_path)
    result = p.load_prompt('divergence', 'v1')
    assert result == 'Hello {{REFERENCE}}'


def test_no_api_key_returns_error_dict(tmp_path):
    p = make_pipeline(tmp_path)
    result = p.analyze_divergence('Isaiah 7:14', 'MT text', 'LXX text')
    assert 'error' in result
    assert result['divergences'] == []


def test_budget_cap_enforced_when_exceeded(tmp_path):
    """analyze_divergence should return error dict (not call API) when cap is reached."""
    p = ClaudePipeline(data_dir=str(tmp_path), api_key='fake-key-wont-be-called', cap_usd=1.0)
    p.record_spend(1.0)  # exactly at cap
    result = p.analyze_divergence('Isaiah 7:14', 'MT text', 'LXX text')
    assert 'error' in result
    assert 'budget' in result['error'].lower()
    assert result['divergences'] == []


def test_budget_cap_not_triggered_when_under(tmp_path):
    """analyze_divergence should not block on cap when spend is below it."""
    p = ClaudePipeline(data_dir=str(tmp_path), api_key='', cap_usd=5.0)
    p.record_spend(4.99)  # just under cap
    # api_key is empty so we get the no-api-key error, not the budget error
    result = p.analyze_divergence('Isaiah 7:14', 'MT text', 'LXX text')
    assert 'error' in result
    assert 'budget' not in result['error'].lower()


def test_cache_dir_property(tmp_path):
    """cache_dir property exposes the internal cache directory path."""
    p = make_pipeline(tmp_path)
    assert p.cache_dir == str(tmp_path / 'cache')
