"""Tests for biblical_core/json_stream.py."""

import pytest
from biblical_core.json_stream import extract_next_section


class TestExtractNextSection:
    def test_simple_string_value(self):
        buf = '"synthesis": "The LXX reads differently.", "next": 1'
        key, val, rem = extract_next_section(buf)
        assert key == 'synthesis'
        assert val == 'The LXX reads differently.'
        assert '"next"' in rem

    def test_object_value(self):
        buf = '"assessment": {"title": "A", "confidence": 0.8}, "other": true'
        key, val, rem = extract_next_section(buf)
        assert key == 'assessment'
        assert val == {'title': 'A', 'confidence': 0.8}

    def test_array_value(self):
        buf = '"revisions": [{"type": "theo"}, {"type": "scribe"}], "done": true'
        key, val, rem = extract_next_section(buf)
        assert key == 'revisions'
        assert len(val) == 2

    def test_incomplete_string_returns_none(self):
        buf = '"synthesis": "The LXX reads'
        assert extract_next_section(buf) is None

    def test_incomplete_array_returns_none(self):
        buf = '"revisions": [{"type": "theo"'
        assert extract_next_section(buf) is None

    def test_end_of_object_returns_none(self):
        assert extract_next_section('}') is None
        assert extract_next_section('  }  ') is None

    def test_empty_buffer_returns_none(self):
        assert extract_next_section('') is None

    def test_leading_comma_stripped(self):
        buf = ', "synthesis": "text", "other": 1'
        key, val, _ = extract_next_section(buf)
        assert key == 'synthesis'

    def test_escaped_quotes_in_string(self):
        buf = '"synthesis": "He said \\"hello\\" clearly.", "x": 1'
        key, val, _ = extract_next_section(buf)
        assert key == 'synthesis'
        assert 'hello' in val

    def test_nested_object_not_prematurely_closed(self):
        buf = '"families": {"alexandrian": {"support": "strong", "witnesses": ["\u05d0", "B"]}}, "x": 1'
        key, val, _ = extract_next_section(buf)
        assert key == 'families'
        assert val['alexandrian']['support'] == 'strong'

    def test_remaining_buffer_correct(self):
        buf = '"a": "x", "b": "y"'
        _, _, rem = extract_next_section(buf)
        key2, val2, _ = extract_next_section(rem)
        assert key2 == 'b'
        assert val2 == 'y'
