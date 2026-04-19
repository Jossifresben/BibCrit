# True Section Streaming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the blocking `messages.create()` pattern with `messages.stream()` so each JSON section (synthesis, divergences, assessment…) is emitted to the browser as a `section` SSE event the moment it completes — instead of everything arriving at once after 60–90 seconds.

**Architecture:** Three layers change together.
1. `biblical_core/json_stream.py` (new) — a pure utility that extracts complete top-level JSON key-value pairs from a partial streaming buffer.
2. `biblical_core/claude_pipeline.py` — each `analyze_*` method gains a companion `stream_*` generator that calls `messages.stream()`, yields `(key, value)` pairs as sections complete, and caches the final result.
3. Each blueprint SSE endpoint — switches from the thread+result_box pattern to a thread+Queue pattern that emits `section` events as they arrive, preserving keepalive heartbeats.
4. Each tool JS file — adds a `section` event handler that renders and animates each section as it lands.

Caching is unchanged: the cache key is still `SHA-256("{ref}|{tool}|{prompt}|{model}")`. Existing cache entries remain valid. Cache hits stream sections instantly from the stored JSON (no API call).

**Tech Stack:** Python 3.11, Anthropic SDK (`messages.stream()`), `queue.Queue` for thread-safe section relay, Flask SSE (`stream_with_context`), vanilla JS.

---

## File Map

| File | Change |
|---|---|
| `biblical_core/json_stream.py` | **Create** — `extract_next_section(buffer)` utility |
| `tests/test_json_stream.py` | **Create** — unit tests for the parser |
| `biblical_core/claude_pipeline.py` | Add `_call_streaming()` helper + `stream_theological()` reference implementation; later `stream_*` for all 12 other tools |
| `blueprints/critical.py` | `api_theological_stream` switches to Queue streaming pattern |
| `static/theological.js` | Add `section` event handler in SSE listener |
| `blueprints/textual.py` | Same streaming pattern for divergence, backtranslation, dss, genealogy, nt_ot |
| `blueprints/critical.py` | Same for scribal, numerical, patristic |
| `blueprints/literary.py` | Same for chiasm, source |
| `blueprints/research.py` | Same for (none — discovery is query-based, no streaming) |
| `blueprints/targum.py` | Same for targum |
| `blueprints/nt_text.py` | Same for nt_text |
| `static/*.js` (12 files) | Same `section` handler for all remaining tools |

---

## Task 1 — JSON section boundary parser

**Files:**
- Create: `biblical_core/json_stream.py`
- Create: `tests/test_json_stream.py`

The Claude API streams tokens one-by-one. All BibCrit prompts produce a JSON object whose top-level keys are the sections we want to emit (`synthesis`, `key_divergences`, `assessment`, etc.). This utility extracts each complete key-value pair as it becomes available in the buffer.

All existing prompts use the assistant prefill trick (`'{'`), so the buffer we receive from `messages.stream()` starts AFTER `{`. We prepend `{` to the buffer and reconstruct it as we consume sections.

- [ ] **Step 1: Create `biblical_core/json_stream.py`**

```python
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
```

- [ ] **Step 2: Create `tests/test_json_stream.py`**

```python
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
        buf = '"families": {"alexandrian": {"support": "strong", "witnesses": ["א", "B"]}}, "x": 1'
        key, val, _ = extract_next_section(buf)
        assert key == 'families'
        assert val['alexandrian']['support'] == 'strong'

    def test_remaining_buffer_correct(self):
        buf = '"a": "x", "b": "y"'
        _, _, rem = extract_next_section(buf)
        key2, val2, _ = extract_next_section(rem)
        assert key2 == 'b'
        assert val2 == 'y'
```

- [ ] **Step 3: Run tests to verify they fail (no implementation yet → ImportError)**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
python -m pytest tests/test_json_stream.py -v
```

Expected: ImportError or 10 failures.

- [ ] **Step 4: Run tests against the implementation**

```bash
python -m pytest tests/test_json_stream.py -v
```

Expected: 10/10 PASS.

- [ ] **Step 5: Commit**

```bash
git add biblical_core/json_stream.py tests/test_json_stream.py
git commit -m "feat: add incremental JSON section extractor for streaming

New biblical_core/json_stream.py with extract_next_section() parses
completed top-level key-value pairs from a partial Claude stream buffer.
10 unit tests covering strings, objects, arrays, escapes, and edge cases.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2 — Streaming helper in ClaudePipeline

**Files:**
- Modify: `biblical_core/claude_pipeline.py`

Add a private `_call_streaming()` generator that wraps `messages.stream()` and yields `(key, value)` pairs using the parser from Task 1. Also add `stream_theological()` as the reference implementation used in Task 3.

- [ ] **Step 1: Add imports at the top of `claude_pipeline.py`**

After `import threading`, add:
```python
from queue import Queue, Empty
from biblical_core.json_stream import extract_next_section
```

- [ ] **Step 2: Add `_call_streaming()` method to `ClaudePipeline`**

Place this directly after the `__init__` method (before the first `analyze_*` method):

```python
def _call_streaming(self, system: str, user_content: str,
                    model: str, max_tokens: int,
                    prefill: str = '{'):
    """Generator: yields (key, value) pairs as top-level JSON sections complete.

    Uses the Anthropic streaming API so sections arrive as Claude writes them,
    not all at once. The prefill ('{') is prepended to match the existing
    assistant-prefill pattern used by all blocking analyze_* methods.

    After the generator exhausts, the caller should call
    self.record_spend(input_tokens * cost + output_tokens * cost).
    Usage tracking is done via self._last_stream_usage set after completion.

    Yields:
        (key: str, value: any) tuples in the order Claude writes them.

    Sets:
        self._last_stream_text: the full raw response text (for caching).
        self._last_stream_usage: (input_tokens, output_tokens) tuple.
    """
    if not self._client:
        return

    self._last_stream_text = prefill
    self._last_stream_usage = (0, 0)
    buffer = ''  # content AFTER the prefill opening brace

    with self._client.messages.stream(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[
            {'role': 'user',      'content': user_content},
            {'role': 'assistant', 'content': prefill},
        ],
    ) as stream:
        for text_chunk in stream.text_stream:
            buffer += text_chunk
            self._last_stream_text += text_chunk
            while True:
                result = extract_next_section(buffer)
                if result is None:
                    break
                key, value, buffer = result
                yield key, value

        final_msg = stream.get_final_message()
        self._last_stream_usage = (
            final_msg.usage.input_tokens,
            final_msg.usage.output_tokens,
        )
```

- [ ] **Step 3: Add `stream_theological()` generator**

> **Note:** This step was superseded during implementation. The final version of `stream_theological()` uses the epilogue pattern (no `self._last_theological_result` or `self._last_stream_text`). See the actual committed code for the canonical implementation. For Task 5 (rolling out to remaining tools), use the pattern in the **implemented** `stream_theological()` as your template, not this draft.

The canonical signature that Task 5 implementers should follow:
- yields `(key, value)` pairs for each JSON section
- yields `(None, result_dict)` as the **final** item on every code path (cache hit, no client, budget exceeded, success, parse failure, exception)
- wraps `_call_streaming()` in `try/except/finally`; `finally` calls `record_spend`
- no instance-attribute side effects (`_last_stream_text`, `_last_stream_usage`, `_last_theological_result` do not exist)

```python
def stream_theological(self, reference: str, vul_text: str = ''):
    """Streaming version of analyze_theological().

    Yields (key, value) pairs as each JSON section completes,
    followed by a final epilogue: (None, final_result_dict).
    The epilogue is always the last item; callers must handle key is None.
    Caches the complete result internally.
    """
    model          = THEOLOGICAL_MODEL
    prompt_version = 'v2'
    tool           = 'theological'

    cached = self.get_cached(reference, tool, prompt_version, model)
    if cached:
        for key, value in cached.items():
            yield key, value
            time.sleep(0.04)
        yield None, cached
        return

    if not self._client:
        yield None, {'error': 'No API key configured.'}
        return

    budget = self.get_budget()
    if budget['spend_usd'] >= self._cap_usd:
        yield None, {'error': 'Monthly budget reached.'}
        return

    template = self.load_prompt('theological', prompt_version)
    user_content = (
        template
        .replace('{{REFERENCE}}', reference)
        .replace('{{VUL_TEXT}}', vul_text)
    ) if template else (
        f'Reference: {reference}\nVulgate: {vul_text or "(not loaded)"}\n'
        'Identify theologically motivated textual changes. Return JSON.'
    )

    sections: dict = {}
    in_tok = out_tok = 0
    full_text = '{'
    try:
        for key, value in self._call_streaming(
            system=_THEOLOGICAL_SYSTEM,
            user_content=user_content,
            model=model,
            max_tokens=8192,
        ):
            if key is None:
                in_tok, out_tok, full_text = value
            else:
                sections[key] = value
                yield key, value
    except Exception as exc:
        yield None, {'error': str(exc)}
        return
    finally:
        self.record_spend(in_tok * _SONNET_COST_IN + out_tok * _SONNET_COST_OUT)

    data = _parse_json_response(full_text)
    if 'parse_error' not in data:
        self.save_cache(reference, tool, prompt_version, model, data)
        yield None, data
    else:
        yield None, (sections if sections else data)
```

- [ ] **Step 4: Verify the new method is syntactically correct**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
python -c "from biblical_core.claude_pipeline import ClaudePipeline; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add biblical_core/claude_pipeline.py
git commit -m "feat(pipeline): add _call_streaming() and stream_theological()

_call_streaming() wraps messages.stream() and yields (key, value) pairs
as top-level JSON sections complete using the json_stream parser.
stream_theological() is the reference implementation: cache hit yields
instantly, cache miss streams from API and caches on completion.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3 — Update theological blueprint to use Queue streaming

**Files:**
- Modify: `blueprints/critical.py` — `api_theological_stream()` only

The existing pattern uses a thread+result_box to keep the SSE connection alive during the blocking API call. The new pattern uses a thread+Queue: the thread drives the streaming generator and puts items into the queue; the Flask generator polls the queue every 8 seconds, yielding keepalives when empty.

- [ ] **Step 1: Add `Queue` and `Empty` imports to `blueprints/critical.py`**

At the top (already has `import threading`), add:
```python
from queue import Queue, Empty
```

- [ ] **Step 2: Locate `api_theological_stream()` and its inner `generate()` function**

Find the section that currently contains:
```python
yield event('step', msg=_step(lang, 'theo_generating'))
_result_box = [None]

def _run_theo():
    try:
        _result_box[0] = pipeline.analyze_theological(reference, vul_text)
    except Exception as exc:
        _result_box[0] = {'error': str(exc)}

_t = threading.Thread(target=_run_theo, daemon=True)
_t.start()
while _t.is_alive():
    _t.join(timeout=8)
    if _t.is_alive():
        yield ': keepalive\n\n'
result = _result_box[0] or {'error': 'Analysis returned no result'}
```

- [ ] **Step 3: Replace that block with the Queue streaming pattern**

```python
yield event('step', msg=_step(lang, 'theo_generating'))
q = Queue()

def _run_theo():
    try:
        for key, value in pipeline.stream_theological(reference, vul_text):
            if key is None:
                # Epilogue: value is the final result dict
                q.put(('done', None, value))
                return
            q.put(('section', key, value))
        # Generator exhausted without epilogue (should not happen)
        q.put(('done', None, {}))
    except Exception as exc:
        q.put(('error', None, str(exc)))

_t = threading.Thread(target=_run_theo, daemon=True)
_t.start()

result = {}
while True:
    try:
        item = q.get(timeout=8)
    except Empty:
        yield ': keepalive\n\n'
        continue

    evt_type, key, data = item
    if evt_type == 'section':
        result[key] = data
        yield event('section', key=key, data=data)
    elif evt_type == 'done':
        result = data if data else result
        break
    elif evt_type == 'error':
        yield event('error', msg=data)
        return

if result.get('error'):
    yield event('error', msg=result['error'])
    return
if result.get('parse_error'):
    yield event('error', msg='Analysis could not be parsed — please try again')
    return
```

The `yield event('done', data=result)` line at the end of the `generate()` function remains unchanged — it fires after the while loop.

- [ ] **Step 4: Verify the server starts without errors**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
python app.py &
sleep 3
curl -s http://localhost:5001/api/theological/stream?ref=Isaiah+7:14 \
  --max-time 10 --no-buffer | head -5
kill %1
```

Expected: SSE output beginning with `data: {"type": "step"...}` lines.

- [ ] **Step 5: Commit**

```bash
git add blueprints/critical.py
git commit -m "feat(theological): stream sections via Queue pattern

theological SSE endpoint now emits 'section' events as each JSON
section completes during the Claude stream. Keepalive heartbeats
preserved. Falls back to 'done' with complete data as before.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4 — Update theological.js section-by-section rendering

**Files:**
- Modify: `static/theological.js`

Add a `section` event handler so each section renders and animates the moment it arrives — instead of waiting for `done`.

- [ ] **Step 1: Locate the SSE `onmessage` handler in `theological.js`**

Find the switch/if block that handles `msg.type`:
```javascript
if (msg.type === 'step') {
    setLoadingStep(msg.msg);
} else if (msg.type === 'done') {
    ...
    renderResult(msg.data);
    ...
}
```

- [ ] **Step 2: Add `section` handler before the `done` handler**

```javascript
} else if (msg.type === 'section') {
    _renderSection(msg.key, msg.data);
} else if (msg.type === 'done') {
    // done fires after all sections — wire exports and finalize
    _finalize(msg.data);
}
```

- [ ] **Step 3: Add `_renderSection` and `_finalize` functions**

Extract the per-section rendering logic from the existing `renderResult()` into `_renderSection()`, and move the post-render wiring (exports, ResultActions) into `_finalize()`. The existing `renderResult()` remains as a fallback that calls both in sequence.

Add above `renderResult`:

```javascript
function _renderSection(key, data) {
    // Ensure results container is visible
    if (results) results.style.display = '';
    if (emptyState) emptyState.style.display = 'none';
    if (loadState) loadState.style.display = 'none';

    var el;
    if (key === 'revisions') {
        // Same rendering logic currently inside renderResult for revisions
        var overallSec = document.getElementById('overall-section');
        if (overallSec) {
            // ... (copy the revisions rendering block from renderResult here)
        }
    } else if (key === 'bibcrit_assessment' || key === 'assessment') {
        var bibSec  = document.getElementById('bibcrit-assessment');
        var bibBody = document.getElementById('bibcrit-body');
        // ... (copy the assessment rendering block)
    }
    // Animate this specific section
    if (el) {
        staggerReveal(el, 0);  // fade this section in
    }
}

function _finalize(data) {
    _lastData = data || _lastData;
    if (exportRow) exportRow.style.display = '';
    staggerReveal(results, 0);  // gentle fade on overall container
    if (window.ResultActions) {
        ResultActions.init({
            toolName: 'theological',
            getReference: function() { return _currentRef; },
            getResultData: function() { return _lastData || {}; },
        });
    }
    _wireExports();
}
```

> **Note:** The exact field names and DOM IDs come from the existing `renderResult()` function — copy them directly. Do not guess.

- [ ] **Step 4: Verify in browser**

1. Open `http://localhost:5001/theological?ref=Isaiah+7:14`
2. Clear the disk cache entry for this passage first:
   ```bash
   ls data/cache/ | grep theological
   # find the file and delete it
   ```
3. Click Analyze
4. Watch: "Analyzing…" step shows, then sections appear one by one as Claude writes them — revisions first, then overall assessment, then BibCrit assessment. Total wait for first content: ~15–20 s instead of 60–90 s.

Expected: First section visible well before the spinner disappears.

- [ ] **Step 5: Commit**

```bash
git add static/theological.js
git commit -m "feat(theological.js): render sections as they stream in

Adds _renderSection() and _finalize() so each 'section' SSE event
populates and animates its DOM target immediately. renderResult()
retained as fallback for cached results that emit all sections at once.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5 — Roll out to remaining 12 tools

**Files:**
- `biblical_core/claude_pipeline.py` — add `stream_*()` for patristic, genealogy, dss, divergence, backtranslation, scribal, numerical, nt_ot, chiasm, source, targum, nt_text
- `blueprints/textual.py`, `critical.py`, `literary.py`, `targum.py`, `nt_text.py` — Queue pattern in each SSE endpoint
- `static/patristic.js`, `genealogy.js`, `dss.js`, `apparatus.js`, `backtranslation.js`, `scribal.js`, `numerical.js`, `nt_ot.js`, `chiasm.js`, `source.js`, `targum.js`, `nt_text.js` — `section` event handlers

**Pattern is identical for each tool** — copy the theological template from Tasks 2–4 and substitute:
- System constant (e.g., `_PATRISTIC_SYSTEM`)
- Prompt version constant (e.g., `'v3'`)
- Tool string (e.g., `'patristic'`)
- Max tokens (use the same value as the existing blocking call)
- `_last_*_result` attribute name
- DOM section IDs and field names (from the existing `renderResult()`)

### Tools and their section keys

| Tool | Key JSON sections (in typical output order) |
|---|---|
| patristic | `citations`, `text_form_distribution`, `transmission_synthesis`, `assessment` |
| genealogy | `archetype_analysis`, `transmission_branches`, `critical_editions`, `assessment` |
| dss | `witness_comparison`, `key_divergences`, `transmission_history`, `assessment` |
| divergence | `divergences`, `synthesis`, `transmission_history`, `assessment` |
| backtranslation | `vorlage_analysis`, `confidence_summary`, `assessment` |
| scribal | `dimensions`, `diagnostic_passages`, `synthesis`, `assessment` |
| numerical | `figures`, `lifespan_timeline`, `systematic_analysis`, `theories`, `assessment` |
| nt_ot | `citations`, `intertextual_analysis`, `synthesis`, `assessment` |
| chiasm | `structure`, `parallel_analysis`, `literary_function`, `assessment` |
| source | `units`, `source_summary`, `redaction_notes`, `assessment` |
| targum | `key_divergences`, `rendering_fidelity`, `theological_modifications`, `expansions`, `messianic`, `lxx_alignment`, `assessment` |
| nt_text | `metzger_rating`, `manuscript_families`, `variant_register`, `disputed_passage`, `synthesis`, `assessment` |

- [ ] **Step 1: Add all 12 `stream_*()` methods to `claude_pipeline.py`**

Each method follows the exact same structure as `stream_theological()` in Task 2, Step 3. Substitute the system constant, prompt version, tool string, user_content template, and `_last_*_result` attribute.

- [ ] **Step 2: Update all blueprint SSE endpoints**

Each endpoint follows the Queue pattern from Task 3, Step 3. Substitute the pipeline method and `_last_*_result` attribute name.

- [ ] **Step 3: Update all JS files**

Each JS file follows the pattern from Task 4, Steps 2–3. Substitute the section key names and corresponding DOM IDs from the existing `renderResult()` logic.

- [ ] **Step 4: Smoke-test each tool with a cached passage**

For each tool, load a known-cached passage in the browser and confirm:
- Sections appear sequentially (the `section` events fire one by one from the cache hit path)
- The `done` event fires after all sections
- No console errors

```bash
# Quick curl test per tool (adjust tool name and ref):
curl -s "http://localhost:5001/api/patristic/stream?ref=Isaiah+7:14" \
  --max-time 5 --no-buffer | grep '"type"' | head -10
```

Expected output includes both `"type":"section"` lines AND a final `"type":"done"` line.

- [ ] **Step 5: Commit per tool or per blueprint file**

```bash
git add biblical_core/claude_pipeline.py blueprints/*.py static/*.js
git commit -m "feat: stream sections for all 13 tools

All analyze_* methods now have stream_* companions. All blueprint SSE
endpoints use the Queue pattern. All tool JS files handle 'section'
events. First content visible 15-25s into analysis instead of 60-90s.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6 — Cache-hit section streaming (instant stagger)

**Files:**
- `biblical_core/claude_pipeline.py` — adjust `stream_*` cache hit path
- Verify all JS `section` handlers work for cache hit paths

Currently, the cache hit path in each `stream_*` method does `yield from cached.items()`, which emits all sections in dictionary order with no delay. This means the CSS animations all fire at the same tick — effectively no stagger.

Add a tiny `time.sleep(0.04)` (40 ms) between cache-hit section yields so the browser processes each `section` event separately and the CSS animations stagger visually:

- [ ] **Step 1: Update cache hit path in all `stream_*` methods**

Change:
```python
if cached:
    self._last_*_result = cached
    yield from cached.items()
    return
```

To:
```python
import time  # (ensure this import is at the top of claude_pipeline.py)

if cached:
    self._last_*_result = cached
    for key, value in cached.items():
        yield key, value
        time.sleep(0.04)  # 40ms gap so browser can process each section event
    return
```

- [ ] **Step 2: Test cached passage in browser**

Open a cached passage (e.g., `/theological?ref=Isaiah+7:14`).
Expected: Sections appear one at a time with ~40ms gaps and CSS slide-in animation on each, not all at once.

- [ ] **Step 3: Commit**

```bash
git add biblical_core/claude_pipeline.py
git commit -m "fix(streaming): add 40ms gap between cache-hit section yields

Without the gap, all sections arrive in the same event loop tick and
the CSS animations fire simultaneously. 40ms apart gives a clean
sequential reveal even on cache hits.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Final verification checklist

After all tasks are done, run through this in the browser:

- [ ] **Uncached passage** (`/theological?ref=Hosea+1:1`, not yet in cache): first section visible within ~20s; remaining sections appear one by one as Claude writes them; `done` fires at the end
- [ ] **Cached passage** (`/theological?ref=Isaiah+7:14`): sections appear sequentially with CSS stagger, total reveal under 0.5s
- [ ] **Spanish locale** (`/theological?ref=Isaiah+7:14&lang=es`): same behaviour (translation path still calls `renderResult()` with full data, `staggerReveal` handles it)
- [ ] **All 13 tools**: each emits `section` events in curl test (`grep '"type":"section"'`)
- [ ] **Budget bar**: still updates after streaming completes
- [ ] **Export buttons**: SBL/BibTeX still copy correctly after stream
- [ ] **Share QR**: still works after stream
- [ ] No console errors on any tool page

---

## Out of scope

- **True per-token text streaming** within a section (e.g., synthesis text appearing word by word) — the current approach emits complete sections. Per-token streaming requires client-side JSON assembly and is deferred.
- **Spanish streaming** — the translation path (`_translate_step`) still uses a blocking call and emits `done` with the full translated result. Streaming translation would require a separate streaming translator, deferred.
- **Scribal radar chart** — the scribal profiler renders a D3 radar chart, not section cards. The `section` event handler for scribal emits dimension data one axis at a time. The radar chart re-draws on each `section` event rather than after `done`.
