# BibCrit — Technical Reference

**Version:** as of 2026-03-31
**Runtime:** Python 3.11 / Flask 3 / Gunicorn on Render
**Primary model:** `claude-sonnet-4-5-20250929`

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Data Models](#2-data-models)
3. [Claude Pipeline](#3-claude-pipeline)
4. [Prompt Engineering](#4-prompt-engineering)
5. [i18n System](#5-i18n-system)
6. [Frontend Architecture](#6-frontend-architecture)
7. [Adding a New Analysis Tool](#7-adding-a-new-analysis-tool)
8. [Deployment](#8-deployment)

---

## 1. Architecture Overview

### Module diagram

```
browser
  │  HTTP GET  (page routes)
  │  EventSource  (SSE streams)
  ▼
app.py  ──  create_app()
  │         registers blueprints
  │         before_request → _init()  (lazy, double-checked lock)
  │         context_processor → inject_globals()
  ▼
blueprints/
  ├── textual.py    /divergence  /backtranslation  /api/divergence/stream  /api/backtranslation/stream
  ├── critical.py   /scribal     /numerical         /api/scribal/stream      /api/numerical/stream
  ├── discovery.py  /discovery   /api/discovery/cards  /api/admin/discovery/flag
  └── research.py   /health
  │
  ├── import state  (shared singletons)
  └── call state.corpus  /  state.pipeline
        │
        ▼
state.py
  ├── corpus: BiblicalCorpus | None
  ├── pipeline: ClaudePipeline | None
  ├── i18n: dict
  └── t: TranslationProxy
        │
        ├── biblical_core/corpus.py   (word-level CSV loader)
        ├── biblical_core/divergence.py  (dataclasses + formatters)
        └── biblical_core/claude_pipeline.py  (Claude API + cache + budget)
```

### Request lifecycle — SSE analysis stream

```
1.  Browser creates: new EventSource('/api/divergence/stream?ref=Isaiah+7:14')

2.  Flask routes to textual_bp.api_divergence_stream()
    └── Response(stream_with_context(generate()), mimetype='text/event-stream')

3.  Generator yields SSE frames:
      data: {"type":"step","msg":"Loading verse text…"}\n\n
      data: {"type":"step","msg":"Checking analysis cache…"}\n\n
      data: {"type":"step","msg":"Analyzing — new passages typically take 60–90s…"}\n\n
      data: {"type":"done","data":{...full JSON result...}}\n\n

4.  corpus.get_verse_words(ref, 'MT') / ('LXX')
    └── BiblicalCorpus._words dict lookup — O(1), pre-sorted by position

5.  pipeline.get_cached(ref, 'divergence', 'v2', DIVERGENCE_MODEL)
    ├── Supabase: SELECT FROM analysis_cache WHERE cache_key = sha256(...)
    └── Disk fallback: data/cache/{sha256}.json

6.  Cache miss → pipeline.analyze_divergence(ref, mt_text, lxx_text)
    ├── Budget check: spend_usd >= cap_usd → yield error frame
    ├── Load prompt: data/prompts/divergence_v2.txt
    ├── anthropic.Anthropic.messages.create(model, system, messages, max_tokens=8192)
    │     assistant pre-fill: '{'  (forces raw JSON, no markdown fence)
    ├── record_spend(input_toks * $3/MTok + output_toks * $15/MTok)
    └── _parse_json_response(raw) → save_cache(...)

7.  Generator yields:
      data: {"type":"done","data":{...}}\n\n

8.  EventSource fires 'message' event in browser
    → JavaScript parses msg.data, renders UI
    → EventSource.close()

Headers set on SSE response:
    Cache-Control: no-cache
    X-Accel-Buffering: no      ← disables nginx/Render proxy buffering
```

### State management — `state.py` singleton pattern

`state.py` is a module-level singleton. It imports **nothing** from `blueprints/` or `app.py`, preventing circular imports. All mutable globals are initialised to `None`/`{}` at import time.

`app._init()` runs the first time any request arrives (guarded by a `threading.Lock` for double-checked locking):

```python
_initialized = False
_init_lock   = threading.Lock()

def _init() -> None:
    global _initialized
    if _initialized:          # fast path — no lock acquired
        return
    with _init_lock:
        if _initialized:      # re-check inside lock
            return
        import state
        # ... populate state.i18n, state.corpus, state.pipeline
        _initialized = True
```

This means the first concurrent request blocks on the lock while the corpus loads; all subsequent requests return immediately from the pre-lock check.

---

## 2. Data Models

### `VerseWord` dataclass (`biblical_core/corpus.py`)

Represents a single morphologically-tagged word in one biblical tradition.

| Field | Type | Example |
|---|---|---|
| `reference` | `str` | `"Isaiah 7:14"` |
| `tradition` | `str` | `"MT"` \| `"LXX"` \| `"GNT"` \| `"DSS"` |
| `position` | `int` | `3` (1-based word position in verse) |
| `word_text` | `str` | `הָעַלְמָ֗ה` |
| `lemma` | `str` | `עַלְמָה` |
| `morph` | `str` | morphological tag string (tradition-dependent) |
| `strong` | `str` | `H5959` |
| `manuscript` | `str` | `"Leningrad"` \| `"Vaticanus"` \| `"1QIsa-a"` |

### `BiblicalCorpus` (`biblical_core/corpus.py`)

Internal store: `_words: dict[(reference, tradition) → list[VerseWord]]`

After `load_all()` each list is sorted ascending by `position`.

**CSV schema** (one row per word, located at `data/corpora/<tradition_dir>/*.csv`):

```
book_order, book, chapter, verse, reference, position,
word_text, lemma, morph, strong, manuscript, tradition
```

**Tradition → directory mapping:**

| Tradition | Directory |
|---|---|
| `MT` | `data/corpora/mt_etcbc/` |
| `LXX` | `data/corpora/lxx_stepbible/` |
| `GNT` | `data/corpora/gnt_opengnt/` |
| `DSS` | `data/corpora/dss/` |

Words with empty `word_text` are skipped on load. All CSVs in a tradition directory are loaded in sorted filename order.

**Public query API:**

```python
corpus.get_verse_words(reference, tradition) → list[VerseWord]
corpus.get_verse_text(reference, tradition)  → str   # words joined by space
corpus.available_traditions(reference)       → list[str]
corpus.get_books(tradition)                  → list[str]
corpus.get_chapters(book, tradition)         → list[int]
corpus.get_verses(book, chapter, tradition)  → list[int]
```

### `DivergenceRecord` and `Hypothesis` dataclasses (`biblical_core/divergence.py`)

```python
@dataclass
class Hypothesis:
    type: str           # one of the seven divergence_type strings
    confidence: float   # 0.0 – 1.0
    explanation: str    # 1–3 sentence scholarly note

@dataclass
class DivergenceRecord:
    reference:          str
    mt_word:            str
    lxx_word:           str
    divergence_type:    str
    confidence:         float
    hypotheses:         list[Hypothesis]
    dss_witness:        str | None
    citations:          list[str]
    analysis_technical: str
    analysis_plain:     str
    discovery_ready:    bool = False
```

`parse_claude_response(data, reference)` converts the raw JSON dict returned by Claude into a list of `DivergenceRecord` objects, **sorted by confidence descending**.

`confidence_tier(score)` maps a float to `'HIGH'` (≥ 0.75), `'MEDIUM'` (≥ 0.45), or `'LOW'`.

Export helpers:
- `format_sbl_footnote(record) → str` — SBL style-guide footnote string
- `format_bibtex(record) → str` — BibTeX `@misc` entry

### Cache format

Every cached result is a JSON object stored in both **Supabase** (`analysis_cache` table) and on **disk** (`data/cache/{sha256}.json`).

The cache key is:

```python
sha256(f"{reference}|{tool}|{prompt_version}|{model}".encode('utf-8')).hexdigest()
```

The stored JSON object merges Claude's response with metadata fields:

```json
{
  "reference": "Isaiah 7:14",
  "divergences": [...],          // tool-specific payload
  "summary_technical": "...",
  "summary_plain": "...",
  "cached_at": "2025-10-01T12:34:56",
  "model_version": "claude-sonnet-4-5-20250929",
  "prompt_version": "v2",
  "discovery_ready": false
}
```

The `discovery_ready` flag is surfaced on the Supabase row as a top-level column for efficient querying:

```sql
SELECT reference, data
FROM   analysis_cache
WHERE  discovery_ready = TRUE;
```

---

## 3. Claude Pipeline

### Class: `ClaudePipeline` (`biblical_core/claude_pipeline.py`)

Instantiated once by `app._init()` and stored at `state.pipeline`.

**Constructor parameters:**

| Parameter | Source | Default |
|---|---|---|
| `data_dir` | `app.BASE_DIR/data` | — |
| `api_key` | `ANTHROPIC_API_KEY` env var | `''` |
| `cap_usd` | `BIBCRIT_API_CAP_USD` env var | `10.0` |
| `supabase_url` | `SUPABASE_URL` env var | `''` |
| `supabase_key` | `SUPABASE_KEY` env var | `''` |

If `api_key` is empty, `self._client` remains `None`. All analysis methods detect this and return an `{'error': '...'}` dict without calling the API.

### Model constants

```python
DIVERGENCE_MODEL = 'claude-sonnet-4-5-20250929'
SCRIBAL_MODEL    = 'claude-sonnet-4-5-20250929'
NUMERICAL_MODEL  = 'claude-sonnet-4-5-20250929'
```

All three currently resolve to the same model. They are kept separate so each tool can be independently upgraded without touching the others.

### Pricing constants

```python
_SONNET_COST_IN  = 3.0  / 1_000_000   # $3.00 per million input tokens
_SONNET_COST_OUT = 15.0 / 1_000_000   # $15.00 per million output tokens
```

### Analysis methods

All four methods follow the same control flow:

1. Check cache (`get_cached`) — return immediately on hit.
2. Check budget (`get_budget`) — return `{'error': ...}` if `spend_usd >= cap_usd`.
3. Load prompt template (`load_prompt`), substitute placeholders.
4. Call `self._client.messages.create(...)` with `max_tokens=8192` and a JSON pre-fill (`'{'`).
5. Calculate cost, call `record_spend(cost)`.
6. Parse response with `_parse_json_response(raw)`.
7. Save to cache (`save_cache`).

**`analyze_divergence(reference, mt_text, lxx_text) → dict`**
- Tool: `divergence`, prompt version: `v2`, model: `DIVERGENCE_MODEL`
- System prompt: `_DIVERGENCE_SYSTEM` (Tov/Wevers/Pietersma specialist)
- Returns: `divergences`, `summary_technical`, `summary_plain`, `bibcrit_hypothesis`

**`analyze_backtranslation(reference, lxx_text, mt_text) → dict`**
- Tool: `backtranslation`, prompt version: `v1`, model: `DIVERGENCE_MODEL`
- System prompt: `_BACKTRANSLATION_SYSTEM` (LXX retroversion specialist)
- Returns: `reconstructed_words`, `summary_technical`, `summary_plain`, `overall_confidence`, `bibcrit_assessment`

**`analyze_scribal(book_name, sample_passages) → dict`**
- Tool: `scribal`, prompt version: `v1`, model: `SCRIBAL_MODEL`
- System prompt: `_SCRIBAL_SYSTEM` (Aejmelaeus/Tov/de Waard specialist)
- Cache key uses `book_name` as the reference field (not a verse reference)
- Returns: `book`, `translator_name`, `translator_profile`, `dimensions`, `overall_assessment`, `overall_plain`, `bibcrit_assessment`

**`analyze_numerical(reference) → dict`**
- Tool: `numerical`, prompt version: `v1`, model: `NUMERICAL_MODEL`
- System prompt: `_NUMERICAL_SYSTEM` (patriarchal chronology specialist)
- Returns: `reference`, `subject`, `figures`, `systematic_analysis`, `theories`, `overall_assessment`, `overall_plain`, `bibcrit_assessment`

### Prompt versioning

Prompt files live at `data/prompts/{tool}_{version}.txt`. The method `load_prompt(tool, version)` loads the file at runtime:

```python
def load_prompt(self, tool: str, version: str = 'v1') -> str:
    path = os.path.join(self._prompts_dir, f'{tool}_{version}.txt')
    ...
```

If no file exists, each analysis method falls back to a minimal inline prompt. Current versions in use:

| Tool | Active version | File |
|---|---|---|
| divergence | `v2` | `divergence_v2.txt` |
| backtranslation | `v1` | `backtranslation_v1.txt` |
| scribal | `v1` | `scribal_v1.txt` |
| numerical | `v1` | `numerical_v1.txt` |

`divergence_v1.txt` is preserved for historical reference; it is not called by any current code path.

### Budget tracking

`record_spend(amount_usd)` is **thread-safe** via `self._budget_lock`. Budget is stored in Supabase (`budget` table) with disk fallback (`data/cache/budget.json`). The budget resets automatically each calendar month (keyed by `YYYY-MM`).

```python
# Supabase schema (budget table)
month      TEXT PRIMARY KEY   -- '2025-10'
spend_usd  NUMERIC            -- running total this month
cap_usd    NUMERIC
updated_at TIMESTAMP
```

`get_budget()` returns `{'month', 'spend_usd', 'cap_usd'}`. The live cap always comes from `self._cap_usd` (the environment variable), so changing `BIBCRIT_API_CAP_USD` takes effect on the next deploy without a database migration.

### Discovery card extraction

`_extract_cards(reference, data, min_confidence)` filters `divergences` to the six "discovery-ready" types:

```python
_DISCOVERY_TYPES = {
    'translation_idiom', 'different_vorlage', 'theological_tendency',
    'omission', 'addition', 'scribal_error'
}
```

`grammatical_shift` is deliberately excluded as too technical for a general audience. Each card dict contains `reference`, `mt_word`, `lxx_word`, `divergence_type`, `confidence`, `analysis_plain`, `summary_plain`, and `cached_at`.

---

## 4. Prompt Engineering

### `divergence_v1.txt`

**Purpose:** Full verbose divergence analysis. Retained for reference; superseded by v2.

**Placeholders:** `{{REFERENCE}}`, `{{MT_TEXT}}`, `{{LXX_TEXT}}`

**Output JSON schema:**
```json
{
  "divergences": [
    {
      "mt_word": "Hebrew (English gloss)",
      "lxx_word": "Greek (English gloss)",
      "divergence_type": "theological_tendency|scribal_error|different_vorlage|translation_idiom|grammatical_shift|omission|addition",
      "confidence": 0.00,
      "hypotheses": [{"type": "...", "confidence": 0.00, "explanation": "..."}],
      "dss_witness": "fragment ID and reading, or null",
      "citations": ["Author (year) §N"],
      "analysis_technical": "3–6 sentence scholarly paragraph",
      "analysis_plain": "2–3 sentence non-specialist explanation"
    }
  ],
  "summary_technical": "2–4 sentence overall assessment",
  "summary_plain": "1–2 sentence general audience summary"
}
```

The prompt instructs Claude to cite BHS apparatus, Tov, Wevers, Pietersma, and DSS where relevant, and specifies exact confidence tier boundaries (HIGH ≥ 0.75, MEDIUM ≥ 0.45, LOW < 0.45).

### `divergence_v2.txt`

**Purpose:** Streamlined v2 prompt optimised for shorter, more consistent output. Adds the `bibcrit_hypothesis` block for Claude's original philological synthesis.

**Placeholders:** `{{REFERENCE}}`, `{{MT_TEXT}}`, `{{LXX_TEXT}}`

**Output JSON schema:** Same as v1 except:
- `analysis_technical` capped to 2–3 sentences
- `analysis_plain` capped to 1–2 sentences
- `summary_technical` capped to 1–2 sentences
- `summary_plain` reduced to 1 sentence
- **Added** top-level `bibcrit_hypothesis` object:

```json
{
  "bibcrit_hypothesis": {
    "title": "Max 8 words",
    "reasoning": "2–3 sentences of original philological analysis beyond cited scholarship",
    "plain": "1–2 sentences for a non-specialist",
    "confidence": 0.00
  }
}
```

The system prompt (`_DIVERGENCE_SYSTEM`) is prefixed with: *"Return ONLY raw JSON. No markdown, no code fences, no backticks, no prose before or after. The response must start with { and end with }."* Combined with an assistant-turn pre-fill of `'{'`, this reliably suppresses markdown wrapping.

### `backtranslation_v1.txt`

**Purpose:** Reconstruct the probable Hebrew Vorlage (source text) that the LXX translator used, using Tov's retroversion methodology.

**Placeholders:** `{{REFERENCE}}`, `{{LXX_TEXT}}`, `{{MT_TEXT}}`

**Output JSON schema:**
```json
{
  "reconstructed_words": [
    {
      "position": 1,
      "lxx_word": "Greek word or phrase",
      "vorlage_word": "Reconstructed Hebrew (or null for idiom_only)",
      "status": "agrees_mt|agrees_dss|unattested|idiom_only",
      "confidence": 0.00,
      "mt_equivalent": "corresponding MT Hebrew, or null",
      "dss_witness": "fragment and reading, or null",
      "reasoning": "2–3 sentences citing lexical parallels, translation patterns, DSS",
      "alternatives": [{"reading": "...", "confidence": 0.00, "note": "1 sentence"}]
    }
  ],
  "summary_technical": "2–3 sentence Vorlage assessment",
  "summary_plain": "1–2 sentences for non-specialists",
  "overall_confidence": 0.00,
  "bibcrit_assessment": {
    "title": "Max 8 words",
    "reasoning": "2–3 sentences identifying the most significant possible lost Hebrew variant",
    "plain": "1–2 sentences for non-specialists",
    "confidence": 0.00
  }
}
```

**Status values**: `agrees_mt` (Vorlage matches MT exactly), `agrees_dss` (matches a DSS variant), `unattested` (possible lost Hebrew reading), `idiom_only` (Greek idiom with no Hebrew equivalent).

### `scribal_v1.txt`

**Purpose:** Profile the characteristic translation tendencies of an LXX book's translator across five scholarly dimensions.

**Placeholders:** `{{BOOK_NAME}}`, `{{SAMPLE_PASSAGES}}`

The `sample_passages` placeholder is populated by `critical.py::_build_sample_passages(book)`, which pulls real MT and LXX text from the corpus using the diagnostic references in `_SCRIBAL_SAMPLE_REFS`. If corpus data is absent for a book, it falls back to `"(No sample passage text available — profile {book} from your training knowledge)"`.

**Five scored dimensions** (0.0 = not present, 1.0 = dominant tendency):

| Dimension | What it measures |
|---|---|
| `literalness` | Word-for-word isomorphic rendering (high) vs. free/idiomatic (low) |
| `anthropomorphism_reduction` | Frequency of theological smoothing of divine body parts / emotions |
| `messianic_heightening` | Amplification of messianic potential in ambiguous passages |
| `harmonization` | Frequency of textual tensions resolved against parallel passages |
| `paraphrase_rate` | Frequency of free rendering departing from word-for-word |

**Output JSON schema (abbreviated):**
```json
{
  "book": "Isaiah",
  "translator_name": "Old Greek of Isaiah",
  "translator_profile": {
    "literalness": 0.00,
    "anthropomorphism_reduction": 0.00,
    "messianic_heightening": 0.00,
    "harmonization": 0.00,
    "paraphrase_rate": 0.00
  },
  "dimensions": [
    {
      "dimension": "literalness",
      "score": 0.00,
      "confidence": 0.00,
      "summary": "2–3 sentence technical assessment",
      "summary_plain": "1–2 sentences for non-specialists",
      "examples": [
        {
          "reference": "Isaiah 7:14",
          "mt_text": "...",
          "lxx_text": "...",
          "note": "1–2 sentences on what this example shows"
        }
      ]
    }
  ],
  "overall_assessment": "3–4 sentence scholarly synthesis",
  "overall_plain": "2–3 sentences for non-specialists",
  "bibcrit_assessment": {"title": "...", "reasoning": "...", "plain": "...", "confidence": 0.00}
}
```

### `numerical_v1.txt`

**Purpose:** Analyze numerical divergences (especially patriarchal chronologies) between MT, LXX, and the Samaritan Pentateuch (SP).

**Placeholder:** `{{REFERENCE}}`

**Theory slugs** (must be used exactly): `mt_deflation`, `lxx_inflation`, `sp_harmonization`, `independent_traditions`, `scribal_error`, `theological_motivation`

**Output JSON schema (abbreviated):**
```json
{
  "reference": "Genesis 5",
  "subject": "Antediluvian patriarchal ages",
  "figures": [
    {
      "name": "Adam (Age at fatherhood)",
      "mt_value": 130,
      "lxx_value": 230,
      "sp_value": 130,
      "divergence_type": "none|minor|significant|major",
      "note": "Optional 1-sentence note or null"
    }
  ],
  "systematic_analysis": {
    "is_systematic": true,
    "pattern": "2–3 sentence mathematical pattern description",
    "pattern_plain": "1–2 sentences for non-specialists"
  },
  "theories": [
    {
      "name": "MT Deflation Theory",
      "slug": "mt_deflation",
      "score": 0.00,
      "confidence": 0.00,
      "summary": "2–3 sentence technical case",
      "summary_plain": "1–2 sentences for non-specialists",
      "supporting_evidence": ["..."],
      "weaknesses": ["..."]
    }
  ],
  "overall_assessment": "3–4 sentence scholarly synthesis",
  "overall_plain": "2–3 sentences for non-specialists",
  "bibcrit_assessment": {"title": "...", "reasoning": "...", "plain": "...", "confidence": 0.00}
}
```

### System prompts

All system prompts end with the same JSON-enforcement directive:

> *"CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, no prose before or after. The response must start with { and end with }."*

This is reinforced by pre-filling the assistant turn with `'{'` in the API call, which forces Claude to continue the JSON object rather than wrap it in a fence.

`_parse_json_response(raw)` implements a three-stage recovery strategy for any remaining format noise:
1. Direct `json.loads(raw)` — succeeds for well-formed responses
2. Strip markdown code fence with regex — handles any residual fencing
3. Walk brace depth to extract the outermost `{...}` — handles leading/trailing prose

---

## 5. i18n System

### `state.TranslationProxy`

```python
class TranslationProxy:
    def __call__(self, key: str, lang: str = 'en') -> str:
        return (
            i18n.get(lang, {}).get(key)
            or i18n.get('en', {}).get(key)
            or key               # key itself as ultimate fallback
        )

    def __getattr__(self, key: str) -> str:
        return self(key)

t = TranslationProxy()
```

`t` is a module-level singleton. In blueprints it is called as `state.t('key', lang)` or passed as `t=state.t` to `render_template`. In templates it is available as `_t('key')` via the context processor.

### `app.inject_globals()` context processor

```python
@app.context_processor
def inject_globals():
    lang = request.args.get('lang', 'en')

    def _t(key: str) -> str:
        return state.t(key, lang)

    return dict(_t=_t, lang=lang)
```

This runs before every template render. The `lang` query parameter is the source of truth; no session/cookie is used server-side. The `_t` function is a closure over the current request's `lang`.

### `data/i18n.json` structure

```json
{
  "_plan": {
    "languages": ["en", "es"],
    "planned": ["he — Hebrew (RTL)", "nl — Dutch"],
    "rtl_langs": ["he"],
    "note": "Add new keys to both en and es simultaneously. Template usage: {{ _t('key') }}"
  },
  "en": {
    "app_name": "BibCrit",
    "nav_textual": "Textual Analysis",
    ...
  },
  "es": {
    "app_name": "BibCrit",
    "nav_textual": "Análisis Textual",
    ...
  }
}
```

The `_plan` key is metadata for developers and is ignored at runtime.

Key categories:
- `nav_*` — navigation labels
- `confidence_*` — tier labels (HIGH / MEDIUM / LOW)
- `scribal_*` — Scribal Profiler page strings
- `numerical_*` — Numerical Modeler page strings
- `donate_*` — budget-exceeded modal strings
- `footer_*` — footer strings

### RTL support

`base.html` sets `dir` automatically:

```html
<html lang="{{ lang }}" dir="{{ 'rtl' if lang in ('he',) else 'ltr' }}">
```

The `he` (Hebrew) font `Noto Sans Hebrew` is already loaded in the `<head>`. Adding Hebrew translation support requires only adding `"he": {...}` to `i18n.json` and translating the strings.

### How to add a new language

1. Open `data/i18n.json`.
2. Copy the entire `"en"` block. Rename the key to your language code (e.g. `"nl"`).
3. Translate every value string. Do not remove or rename keys.
4. Add the language code to `_plan.languages` (documentation only).
5. If the language is RTL, add its code to `_plan.rtl_langs` and to the `dir` expression in `base.html`.
6. Add a `<button>` for it in the language dropdown in `base.html`:
   ```html
   <button class="lang-option{% if lang == 'nl' %} active{% endif %}" data-lang="nl">NL — Nederlands</button>
   ```
7. Remove the `disabled` attribute if it was listed as a "coming soon" stub.

No Python changes are required — `TranslationProxy` looks up any language code dynamically.

---

## 6. Frontend Architecture

### SSE streaming pattern

Every analysis page follows the same client-side pattern (shown here for the Divergence Analyzer; all tools are identical in structure):

```javascript
// 1. Open EventSource connection
var _es = new EventSource('/api/divergence/stream?ref=' + encodeURIComponent(ref));

// 2. Listen for all messages (server sends named 'message' events)
_es.addEventListener('message', function(e) {
    var msg = JSON.parse(e.data);

    if (msg.type === 'step') {
        // Intermediate progress update — show in loading banner
        setLoadingStep(msg.msg);

    } else if (msg.type === 'error') {
        _finalHandled = true;
        clearInterval(_timer);
        setLoadingStep('❌ ' + msg.msg);
        _es.close();

    } else if (msg.type === 'done') {
        _finalHandled = true;
        clearInterval(_timer);
        _es.close();
        renderResults(msg.data);   // page-specific render function
    }
});

// 3. Handle connection drop (network error, server restart)
_es.onerror = function() {
    if (_finalHandled) return;   // already finished — ignore
    clearInterval(_timer);
    setLoadingStep('❌ Connection error. Please try again.');
    if (_es) _es.close();
};
```

The `_finalHandled` flag prevents double-handling when the connection drops after a `done` message (the browser fires `onerror` when the server closes the stream).

**Elapsed timer:** All pages start a `setInterval` counter (incrementing every second) on the loading step display. It is cleared when `done` or `error` is received.

**URL update:** `history.replaceState` is called when analysis starts, so the URL reflects the current passage and is bookmarkable/shareable before the result arrives.

### `scribal.js` — radar chart with D3 v7

`scribal.js` uses D3 v7 (loaded from CDN in `scribal.html`) to render a spider/radar chart of the five translator dimensions.

**Five axes** (in display order):
```javascript
var DIMS = [
  { key: 'literalness',                label: 'Literalness' },
  { key: 'anthropomorphism_reduction', label: 'Anthrop. Reduction' },
  { key: 'messianic_heightening',      label: 'Messianic Heightening' },
  { key: 'harmonization',              label: 'Harmonization' },
  { key: 'paraphrase_rate',            label: 'Paraphrase Rate' },
];
```

**Series colors:**
```javascript
var SERIES_COLORS = ['#3a6bc4', '#e67e22'];  // primary book, comparison book
```

**Comparison mode:** When the "Compare two books" checkbox is checked and a second book is selected, `fetchSecond(book2, cb)` opens a second `EventSource` to `/api/scribal/stream`. On receipt of the `done` message from both streams, `renderScribal(_data1, _data2)` is called to draw a two-series radar chart.

**Book selector mutual exclusion:** `_syncBookSelectors(changed, other)` rebuilds the non-active dropdown to exclude the currently selected book, preventing both selectors from choosing the same book.

**Expand modal:** A full-screen radar modal is provided. The same `_drawInto(svgNode, series)` function draws into both the inline SVG and the modal SVG, keeping them in sync.

**Dimension tabs:** Each of the five dimensions gets a tab in a `<nav>` below the radar. Tabs display the dimension's score, confidence, technical summary, plain-language summary, and text examples with MT/LXX parallel columns.

**SBL export:** The "SBL Footnotes" button calls `/api/scribal/export/sbl?book=Isaiah`, which formats each dimension's summary as a footnote string, and writes them to the clipboard via `navigator.clipboard.writeText`.

### `numerical.js` — grouped patriarch timeline chart

`numerical.js` renders results from the Numerical Discrepancy Modeler using two complementary visualizations, implemented entirely with raw SVG (no D3 dependency).

**Tradition colors:**
```javascript
var TRAD_COLORS = {
    mt:  'var(--mt-color, #c0892a)',
    lxx: 'var(--lxx-color, #3a6bc4)',
    sp:  'var(--sp-color, #2c7c5f)',
};
```

**Summary table** (`renderTable`): Renders an HTML `<table>` with one row per figure. Columns: Name, MT value, LXX value, SP value (if any data present), Divergence badge. Rows with significant/major divergence receive the `num-row-divergent` class.

**Timeline chart** (`renderTimeline`): Detects whether the figures follow a patriarchal lifespan pattern (names containing "age at", "remaining years", "total lifespan"). If so, calls `_renderGroupedChart`; otherwise `_renderSimpleChart`.

`_renderGroupedChart` builds a horizontal stacked bar chart:
- Groups figures by patriarch name (stripping parenthetical suffixes)
- Extracts `ageBirth`, `remaining`, and `total` figures per patriarch
- Renders grouped horizontal bars: one row of bars per tradition (MT, LXX, SP) per patriarch
- Adds a view toggle ("Age + Remaining" vs. "Total only"), persisted in `localStorage` under key `num-timeline-mode`
- Scale is computed from the maximum value across all traditions and figures
- SVG is constructed directly via `createElementNS(NS, tag)` helper functions

**Theory tabs** (`buildTheoryTabs`): Each theory from the API response gets a tab. Tab content includes: score badge, confidence badge, technical summary, plain summary, supporting evidence bullet list, and weaknesses bullet list.

### `global.js` — theme, language, and shared utilities

`global.js` is loaded on every page from `base.html`. It runs inside an IIFE.

**Dark mode:**
- Reads/writes `localStorage.theme` (`'dark'` | `'light'`)
- Applies `data-theme="dark"` to `<html>` on load and on toggle
- Updates the icon: `'bedtime'` (dark) / `'sunny'` (light)

**Language persistence:**
- On load: if no `lang` param in URL but `localStorage['bibcrit-lang']` is non-English, redirects immediately with the stored lang param
- On language selection: writes `lang` param to URL; `localStorage` is updated on the resulting page load
- Updates the `#lang-current-code` element to show the active language code in the nav

**Nav dropdowns:** Click-to-open dropdowns with `closeAllDropdowns()` called on outside click and on opening any other dropdown.

**Share / QR modal:** Opens a modal showing the current URL in a text input with a copy button. Generates a QR code on first open using the `QRCode.js` library (loaded via CDN in templates that need it).

**Budget bar (`updateBudgetBar`):** Called on `DOMContentLoaded` on every page. Fetches `/api/budget` and updates:
- `#budget-spend` — current spend formatted as `$X.XX`
- `#budget-cap` — cap formatted as `$X.XX`
- `#budget-bar` — `style.width` percentage
- `#budget-pct` — percentage text
- `#budget-donate-btn` — shown only when usage ≥ 80%

**Shared bookmark / annotation utilities** (exported as globals for use by other scripts):
- `getBookmarks()` / `saveBookmarks(bm)` — read/write `localStorage['atlas_bookmarks']`
- `getAnnotations()` / `saveAnnotations(ann)` / `setAnnotation()` / `deleteAnnotation()` — read/write `localStorage['atlas_annotations']`

---

## 7. Adding a New Analysis Tool

This section walks through adding a complete Tier 2 analysis tool. The example is a hypothetical **Patristic Citation Tracker** (`/patristic`).

### Step 1: Write the prompt file

Create `data/prompts/patristic_v1.txt`. Define:
- A specialist persona in the system prompt area (handled via a system constant, not in the file)
- Placeholders in the form `{{REFERENCE}}`, `{{BOOK_NAME}}`, etc.
- A strict JSON output schema with all fields documented inline
- Confidence tier definitions (HIGH/MEDIUM/LOW)
- The JSON-only instruction: *"Return JSON (no fences, no prose):"*

```
# data/prompts/patristic_v1.txt

You are a specialist in patristic literature...

REFERENCE: {{REFERENCE}}

Return JSON (no fences, no prose):

{
  "citations": [...],
  "summary_technical": "...",
  "summary_plain": "...",
  "bibcrit_assessment": {...}
}
```

### Step 2: Add the system prompt and model constant

In `biblical_core/claude_pipeline.py`, add:

```python
PATRISTIC_MODEL = 'claude-sonnet-4-5-20250929'

_PATRISTIC_SYSTEM = (
    "You are a specialist in patristic literature with deep expertise in "
    "early Christian biblical quotation and textual transmission. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)
```

### Step 3: Add the analysis method to `ClaudePipeline`

```python
def analyze_patristic(self, reference: str) -> dict:
    model          = PATRISTIC_MODEL
    prompt_version = 'v1'
    tool           = 'patristic'

    cached = self.get_cached(reference, tool, prompt_version, model)
    if cached:
        return cached

    if not self._client:
        return {'error': 'No API key configured.', 'citations': [], ...}

    budget = self.get_budget()
    if budget['spend_usd'] >= self._cap_usd:
        return {'error': f"Monthly budget of ${self._cap_usd:.2f} reached.", 'citations': [], ...}

    template = self.load_prompt('patristic', prompt_version)
    user_content = template.replace('{{REFERENCE}}', reference) if template else (
        f'Reference: {reference}\nAnalyze patristic citations. Return JSON.'
    )

    response = self._client.messages.create(
        model=model,
        max_tokens=8192,
        system=_PATRISTIC_SYSTEM,
        messages=[
            {'role': 'user',      'content': user_content},
            {'role': 'assistant', 'content': '{'},
        ],
    )

    cost = (response.usage.input_tokens  * _SONNET_COST_IN +
            response.usage.output_tokens * _SONNET_COST_OUT)
    self.record_spend(cost)

    raw  = '{' + response.content[0].text
    data = _parse_json_response(raw)
    self.save_cache(reference, tool, prompt_version, model, data)
    return data
```

### Step 4: Create the blueprint

Create `blueprints/patristic.py`:

```python
"""Patristic Citation Tracker blueprint."""

import json
from flask import Blueprint, render_template, request, Response, stream_with_context
from biblical_core.claude_pipeline import PATRISTIC_MODEL
import state

patristic_bp = Blueprint('patristic', __name__)
_PATRISTIC_PROMPT = 'v1'


@patristic_bp.route('/patristic')
def patristic():
    lang = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('patristic.html', lang=lang, reference=reference, t=state.t)


@patristic_bp.route('/api/patristic/stream')
def api_patristic_stream():
    reference = request.args.get('ref', '').strip()

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        pipeline = state.pipeline
        if pipeline is None:
            yield event('error', msg='Server not ready')
            return

        yield event('step', msg='Checking analysis cache…')
        cached = pipeline.get_cached(reference, 'patristic', _PATRISTIC_PROMPT, PATRISTIC_MODEL)

        if cached:
            yield event('step', msg='Found in cache — loading instantly')
            result = cached
        else:
            yield event('step', msg='Searching patristic citations — this typically takes 30–60s…')
            result = pipeline.analyze_patristic(reference)

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['reference'] = reference
        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
```

### Step 5: Register the blueprint in `app.py`

```python
from blueprints.patristic import patristic_bp
app.register_blueprint(patristic_bp)
```

### Step 6: Create the HTML template

Create `templates/patristic.html` extending `base.html`:

```html
{% extends "base.html" %}
{% block title %}{{ _t('patristic_page_title') }}{% endblock %}

{% block head %}
<!-- Add any page-specific CSS/JS here -->
{% endblock %}

{% block content %}
<div id="empty-state">...</div>
<div id="loading-state" style="display:none">
  <span id="loading-step"></span>
  <span id="loading-timer">0s</span>
</div>
<div id="patristic-results" style="display:none">...</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='patristic.js') }}"></script>
{% endblock %}
```

### Step 7: Create the JavaScript file

Create `static/patristic.js`. Follow the SSE pattern from `numerical.js`:

```javascript
(function() {
  'use strict';

  var btnAnalyze  = document.getElementById('btn-analyze');
  var refInput    = document.getElementById('ref-input');
  var emptyState  = document.getElementById('empty-state');
  var loadState   = document.getElementById('loading-state');
  var loadStep    = document.getElementById('loading-step');
  var loadTimer   = document.getElementById('loading-timer');
  var results     = document.getElementById('patristic-results');

  var _es           = null;
  var _timer        = null;
  var _finalHandled = false;

  function analyze(ref) {
    if (!ref) return;
    if (_es) { _es.close(); _es = null; }
    clearInterval(_timer);
    _finalHandled = false;

    // show loading, hide results
    var elapsed = 0;
    _timer = setInterval(function() {
      elapsed++;
      if (loadTimer) loadTimer.textContent = elapsed + 's';
    }, 1000);

    history.replaceState(null, '', '/patristic?ref=' + encodeURIComponent(ref));
    _es = new EventSource('/api/patristic/stream?ref=' + encodeURIComponent(ref));

    _es.addEventListener('message', function(e) {
      var msg = JSON.parse(e.data);
      if (msg.type === 'step')       { loadStep.textContent = msg.msg; }
      else if (msg.type === 'error') { _finalHandled = true; clearInterval(_timer); _es.close(); }
      else if (msg.type === 'done')  { _finalHandled = true; clearInterval(_timer); _es.close(); renderPatristic(msg.data); }
    });

    _es.onerror = function() {
      if (_finalHandled) return;
      clearInterval(_timer);
      _es.close();
    };
  }

  function renderPatristic(data) {
    // ... build DOM from data.citations, data.summary_plain, etc.
  }

  if (btnAnalyze) btnAnalyze.addEventListener('click', function() {
    analyze(refInput ? refInput.value.trim() : '');
  });
})();
```

### Step 8: Add i18n keys

In `data/i18n.json`, add keys to both `en` and `es` (and any other active language):

```json
"en": {
  "nav_patristic":        "Patristic Citation Tracker",
  "patristic_page_title": "Patristic Citation Tracker — BibCrit",
  "patristic_what_title": "What is this?"
},
"es": {
  "nav_patristic":        "Rastreador de Citas Patrísticas",
  "patristic_page_title": "Rastreador de Citas Patrísticas — BibCrit",
  "patristic_what_title": "¿Qué es esto?"
}
```

### Step 9: Add the nav link

In `templates/base.html`, add the link inside the appropriate `nav-drop-menu`. For a Tier 2 Critical Analysis tool, add it below the `<hr class="nav-drop-sep">` in the Critical Analysis dropdown:

```html
<a href="/patristic?lang={{ lang }}">{{ _t('nav_patristic') }}</a>
```

Remove the `nav-future` class and any `href="#"` stub if a placeholder already exists.

### Step 10: Write tests

Add a test file `tests/test_patristic.py` following the pattern in existing test files. At minimum, test:
- `GET /patristic` returns 200
- `GET /api/patristic/stream?ref=Isaiah+7:14` returns SSE with `done` or `error` event
- The analysis method handles missing API key gracefully
- Cache hit path returns cached data without calling the API

---

## 8. Deployment

### `render.yaml` configuration

```yaml
services:
  - type: web
    name: bibcrit
    runtime: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 2 --timeout 120
    envVars:
      - key: PYTHON_VERSION
        value: "3.11"
      - key: ANTHROPIC_API_KEY
        sync: false           # set manually in Render dashboard — never committed
      - key: BIBCRIT_API_CAP_USD
        value: "10.0"
```

**Worker configuration:** Single worker with 2 threads. This is intentional: SSE streams hold a connection open for 60–90 seconds. Multiple workers would exhaust connection limits at low traffic. Two threads allow one analysis stream and one UI request to be served concurrently.

**Gunicorn timeout:** 120 seconds — accommodates Claude API calls that can take 60–90 seconds on cache miss.

### Environment variables

| Variable | Required | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | Yes (for analysis) | Claude API key. Without it the app serves cached results but cannot run new analyses. |
| `BIBCRIT_API_CAP_USD` | No | Monthly spend cap in USD. Default: `10.0`. Increase to allow more analyses per month. |
| `SUPABASE_URL` | No | Supabase project URL. Without it the app falls back to disk caching. |
| `SUPABASE_KEY` | No | Supabase `anon` or `service_role` key. |
| `BIBCRIT_ADMIN_KEY` | No | Secret key for the `POST /api/admin/discovery/flag` endpoint. Without it the endpoint returns 403. |

### Supabase setup

If `SUPABASE_URL` and `SUPABASE_KEY` are provided, the pipeline uses Supabase as the primary cache and budget store, with disk as fallback. The following tables must exist:

**`analysis_cache`**
```sql
CREATE TABLE analysis_cache (
    cache_key       TEXT PRIMARY KEY,
    reference       TEXT NOT NULL,
    tool            TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    data            JSONB NOT NULL,
    cached_at       TIMESTAMPTZ NOT NULL,
    discovery_ready BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE INDEX ON analysis_cache (discovery_ready);
CREATE INDEX ON analysis_cache (reference);
```

**`budget`**
```sql
CREATE TABLE budget (
    month       TEXT PRIMARY KEY,   -- 'YYYY-MM'
    spend_usd   NUMERIC NOT NULL DEFAULT 0,
    cap_usd     NUMERIC NOT NULL DEFAULT 10.0,
    updated_at  TIMESTAMPTZ
);
```

**`hypothesis_votes`**
```sql
CREATE TABLE hypothesis_votes (
    reference   TEXT PRIMARY KEY,
    upvotes     INTEGER NOT NULL DEFAULT 0,
    downvotes   INTEGER NOT NULL DEFAULT 0,
    updated_at  TIMESTAMPTZ
);
```

### Local development

```bash
# 1. Clone and install
pip install -r requirements.txt

# 2. Create .env (never commit this file)
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env
echo "BIBCRIT_API_CAP_USD=2.0"    >> .env
# SUPABASE_URL and SUPABASE_KEY are optional for local dev
# Without them the app uses data/cache/ on disk

# 3. Run
python app.py          # development server with hot reload
# or
gunicorn app:app --bind 0.0.0.0:5000 --workers 1 --threads 2 --timeout 120
```

The `python-dotenv` import in `app.py` is wrapped in a `try/except ImportError`, so the server starts cleanly even without `dotenv` installed. On Render, all environment variables are set directly in the service dashboard.

### Corpus data

The app ships with demo CSVs in `data/corpora/mt_etcbc/demo.csv` and `data/corpora/lxx_stepbible/demo.csv`. For production, place full ETCBC/STEPBible CSV exports in the corresponding tradition directories. The corpus loads all `*.csv` files it finds on startup.

### Health check

`GET /health` (served by `research_bp`) returns:

```json
{"status": "ok", "app": "bibcrit"}
```

Configure this as the Render health check path to ensure the worker is live before traffic is routed to it.
