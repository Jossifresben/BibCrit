"""Incremental JSON section extractor for Claude streaming output.

All BibCrit prompts produce a single JSON object. This module extracts
top-level key-value pairs as they complete in a streaming buffer, allowing
the server to emit 'section' SSE events before the full response arrives.

Usage:
    buffer = '{'  # prefill already applied
    for text_chunk in stream.text_stream:
        buffer += text_chunk
        while True:
            result = extract_next_section(buffer)
            if result is None:
                break
            key, value, buffer = result
            emit_section(key, value)
"""

import json
import re


def extract_next_section(buffer: str):
    """Extract the next complete top-level key-value pair from a partial JSON buffer.

    The buffer should contain the content AFTER the opening '{', e.g.
    '"synthesis": "The LXX reading...", "key_divergences": [{'

    Args:
        buffer: Partial JSON string after the opening brace.

    Returns:
        (key: str, value: any, remaining: str)  — key is the JSON key string,
        value is the parsed Python object, remaining is the buffer after this
        section (still starts after a consumed comma, ready for the next key).
        Returns None if the next section is not yet complete in the buffer.
    """
    # Strip leading separators and whitespace
    s = buffer.lstrip(' \t\n\r,')

    # Check for end-of-object (nothing more to extract)
    if s.startswith('}') or not s:
        return None

    # Match opening quote of a key
    m = re.match(r'"((?:[^"\\]|\\.)*)"\s*:\s*', s)
    if not m:
        return None

    key = m.group(1)
    after_colon = s[m.end():]

    value_json, end_pos = _extract_value(after_colon)
    if value_json is None:
        return None  # Value not yet complete in buffer

    try:
        value = json.loads(value_json)
    except json.JSONDecodeError:
        return None

    remaining = after_colon[end_pos:]
    return key, value, remaining


def _extract_value(s: str):
    """Extract one complete JSON value from the start of string s.

    Returns (json_string, end_position) or (None, 0) if the value is incomplete.
    """
    stripped = s.lstrip(' \t\n\r')
    skip = len(s) - len(stripped)
    s = stripped

    if not s:
        return None, 0

    c = s[0]

    if c == '"':
        pos = 1
        while pos < len(s):
            if s[pos] == '\\':
                pos += 2
                continue
            if s[pos] == '"':
                return s[:pos + 1], skip + pos + 1
            pos += 1
        return None, 0  # String not yet closed

    if c in ('{', '['):
        close = '}' if c == '{' else ']'
        depth, in_str, pos = 0, False, 0
        while pos < len(s):
            ch = s[pos]
            if in_str:
                if ch == '\\':
                    pos += 2
                    continue
                if ch == '"':
                    in_str = False
            else:
                if ch == '"':
                    in_str = True
                elif ch == c:
                    depth += 1
                elif ch == close:
                    depth -= 1
                    if depth == 0:
                        return s[:pos + 1], skip + pos + 1
            pos += 1
        return None, 0  # Object/array not yet closed

    # Number, bool, null — terminated by comma, whitespace, or }
    m = re.match(r'(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null)', s)
    if m:
        return m.group(0), skip + m.end()
    return None, 0
