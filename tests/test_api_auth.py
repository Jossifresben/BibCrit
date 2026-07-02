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


def test_validate_api_key_false_when_revoked(monkeypatch):
    """A revoked key must be rejected even though the row is found —
    revoked is checked, not just row existence."""
    from unittest.mock import MagicMock
    import state

    fake_pipeline = MagicMock()
    fake_pipeline._supabase.table.return_value.select.return_value.eq.return_value \
        .limit.return_value.execute.return_value.data = [
            {'id': 'row-1', 'revoked': True, 'requests_total': 3}
        ]
    monkeypatch.setattr(state, 'pipeline', fake_pipeline)

    assert validate_api_key('bibcrit_live_revoked_key') is False
    # A revoked key must not be treated as "used" — no update call should follow.
    fake_pipeline._supabase.table.return_value.update.assert_not_called()


def test_validate_api_key_true_when_live(monkeypatch):
    """A non-revoked key is accepted and bumps last_used_at/requests_total."""
    from unittest.mock import MagicMock
    import state

    fake_pipeline = MagicMock()
    fake_pipeline._supabase.table.return_value.select.return_value.eq.return_value \
        .limit.return_value.execute.return_value.data = [
            {'id': 'row-2', 'revoked': False, 'requests_total': 7}
        ]
    monkeypatch.setattr(state, 'pipeline', fake_pipeline)

    assert validate_api_key('bibcrit_live_live_key') is True
    update_call = fake_pipeline._supabase.table.return_value.update.call_args
    assert update_call[0][0]['requests_total'] == 8  # incremented from 7
