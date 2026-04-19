"""Tests for _call_streaming() and stream_theological() generator contracts."""
import time
import json
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from biblical_core.claude_pipeline import ClaudePipeline


def _make_pipeline(with_client=True):
    """Create a ClaudePipeline with mocked internals."""
    pl = ClaudePipeline.__new__(ClaudePipeline)
    pl._client = MagicMock() if with_client else None
    pl._supabase = None
    pl._cache_dir = '/tmp/bibcrit_test_cache'
    pl._cap_usd = 100.0
    pl._model_version = 'claude-sonnet-4-6'
    pl._budget_cache = None
    pl._budget_cache_time = 0
    return pl


# ── _call_streaming ──────────────────────────────────────────────────────────

class TestCallStreamingEpilogue:
    def test_no_client_yields_epilogue(self):
        """When _client is None, must yield a single (None, (0, 0, prefill)) epilogue."""
        pl = _make_pipeline(with_client=False)
        items = list(pl._call_streaming(system='s', user_content='u', model='m', max_tokens=10))
        assert len(items) == 1
        key, value = items[0]
        assert key is None
        in_tok, out_tok, full_text = value
        assert in_tok == 0
        assert out_tok == 0
        assert full_text == '{'   # default prefill

    def test_epilogue_is_last_item(self):
        """With a real stream mock, (None, ...) must be the last item yielded."""
        pl = _make_pipeline(with_client=True)

        # Simulate Claude streaming: `"key": "value"}`
        stream_ctx = MagicMock()
        stream_ctx.__enter__ = lambda s: s
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.text_stream = iter(['"key": "val"}'])
        final_msg = MagicMock()
        final_msg.usage.input_tokens = 5
        final_msg.usage.output_tokens = 10
        stream_ctx.get_final_message = MagicMock(return_value=final_msg)
        pl._client.messages.stream = MagicMock(return_value=stream_ctx)

        items = list(pl._call_streaming(system='s', user_content='u', model='m', max_tokens=100))
        # Last item must be the epilogue
        key, value = items[-1]
        assert key is None
        in_tok, out_tok, full_text = value
        assert in_tok == 5
        assert out_tok == 10
        assert '"key": "val"' in full_text


# ── stream_theological ───────────────────────────────────────────────────────

class TestStreamTheologicalEpilogue:
    def test_no_client_yields_error_epilogue(self):
        """When _client is None, must yield exactly (None, {'error': ...})."""
        pl = _make_pipeline(with_client=False)
        items = list(pl.stream_theological('Genesis 1'))
        assert len(items) == 1
        key, value = items[0]
        assert key is None
        assert 'error' in value

    def test_budget_exceeded_yields_error_epilogue(self):
        """When budget is at cap, must yield exactly (None, {'error': ...})."""
        pl = _make_pipeline(with_client=True)
        pl._cap_usd = 0.0  # cap is 0 → always exceeded
        # Mock get_budget to return spend > cap
        pl.get_budget = MagicMock(return_value={'spend_usd': 1.0})
        # Mock get_cached to return None (no cache)
        pl.get_cached = MagicMock(return_value=None)

        items = list(pl.stream_theological('Genesis 1'))
        assert len(items) == 1
        key, value = items[0]
        assert key is None
        assert 'error' in value

    def test_cache_hit_epilogue_is_cached_dict(self):
        """On a cache hit, last item must be (None, cached_dict) and sections yielded first."""
        pl = _make_pipeline(with_client=False)
        cached = {'revisions': [{'text': 'a'}], 'summary': 'b'}
        pl.get_cached = MagicMock(return_value=cached)

        items = list(pl.stream_theological('Genesis 1'))
        # Last item is the epilogue
        key, value = items[-1]
        assert key is None
        assert value == cached
        # All non-epilogue items should be (section_key, section_value) pairs
        section_items = items[:-1]
        assert len(section_items) == len(cached)
        for k, v in section_items:
            assert k is not None
            assert cached[k] == v

    def test_successful_stream_epilogue_is_parsed_dict(self):
        """After a successful API stream, last item is (None, parsed_result_dict)."""
        pl = _make_pipeline(with_client=True)
        pl.get_cached = MagicMock(return_value=None)
        pl.get_budget = MagicMock(return_value={'spend_usd': 0.0})
        pl.load_prompt = MagicMock(return_value=None)
        pl.record_spend = MagicMock()
        pl.save_cache = MagicMock()

        result_json = '{"revisions": [], "summary": "test"}'

        stream_ctx = MagicMock()
        stream_ctx.__enter__ = lambda s: s
        stream_ctx.__exit__ = MagicMock(return_value=False)
        stream_ctx.text_stream = iter(['"revisions": [], "summary": "test"}'])
        final_msg = MagicMock()
        final_msg.usage.input_tokens = 10
        final_msg.usage.output_tokens = 20
        stream_ctx.get_final_message = MagicMock(return_value=final_msg)
        pl._client.messages.stream = MagicMock(return_value=stream_ctx)

        items = list(pl.stream_theological('Genesis 1'))
        key, value = items[-1]
        assert key is None
        assert isinstance(value, dict)
        assert 'error' not in value
        # record_spend must have been called
        pl.record_spend.assert_called_once()
