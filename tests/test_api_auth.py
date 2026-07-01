"""Tests for API key generation, hashing, and validation."""
from biblical_core.api_auth import generate_api_key, hash_api_key, validate_api_key


def test_generate_api_key_has_expected_prefix_and_length():
    key = generate_api_key()
    assert key.startswith('bibcrit_live_')
    assert len(key) > len('bibcrit_live_') + 30


def test_generate_api_key_is_unique():
    assert generate_api_key() != generate_api_key()


def test_hash_api_key_is_deterministic_and_not_the_raw_key():
    key = 'bibcrit_live_test123'
    h1 = hash_api_key(key)
    h2 = hash_api_key(key)
    assert h1 == h2
    assert h1 != key
    assert len(h1) == 64  # sha256 hex digest


def test_validate_api_key_false_when_no_supabase(monkeypatch):
    import state
    monkeypatch.setattr(state, 'pipeline', None)
    assert validate_api_key('bibcrit_live_anything') is False


def test_validate_api_key_false_for_empty_string():
    assert validate_api_key('') is False
