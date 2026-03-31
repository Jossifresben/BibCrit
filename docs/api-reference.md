# BibCrit API Reference

**Base URL:** `http://localhost:5000` (development) or your deployed Render URL (production)

All API endpoints return JSON unless otherwise noted. SSE endpoints return `text/event-stream`.

---

## Table of Contents

1. [Global Conventions](#global-conventions)
   - [SSE Event Schema](#sse-event-schema)
   - [Authentication](#authentication)
   - [Rate Limiting & Budget Cap](#rate-limiting--budget-cap)
   - [Common Error Responses](#common-error-responses)
2. [Page Routes](#page-routes)
   - [GET /](#get-)
   - [GET /divergence](#get-divergence)
   - [GET /backtranslation](#get-backtranslation)
   - [GET /scribal](#get-scribal)
   - [GET /numerical](#get-numerical)
   - [GET /discovery](#get-discovery)
3. [Textual Analysis API](#textual-analysis-api)
   - [GET /api/divergence/stream](#get-apidivergencestream)
   - [GET /api/backtranslation/stream](#get-apibacktranslationstream)
   - [GET /api/divergence](#get-apidivergence)
   - [GET /api/divergence/export/sbl](#get-apidivergenceexportsbl)
   - [GET /api/divergence/export/bibtex](#get-apidivergenceexportbibtex)
   - [GET /api/books](#get-apibooks)
   - [GET /api/chapters](#get-apichapters)
   - [GET /api/verses](#get-apiverses)
4. [Hypothesis Voting API](#hypothesis-voting-api)
   - [GET /api/hypothesis/votes](#get-apihypothesisvotes)
   - [POST /api/hypothesis/vote](#post-apihypothesisvote)
5. [Critical Analysis API](#critical-analysis-api)
   - [GET /api/scribal/stream](#get-apiscribalstream)
   - [GET /api/numerical/stream](#get-apinumericalstream)
   - [GET /api/scribal/export/sbl](#get-apiscribalexportsbl)
   - [GET /api/numerical/export/sbl](#get-apinumericalexportsbl)
6. [Discovery API](#discovery-api)
   - [GET /api/discovery/cards](#get-apidiscoverycards)
   - [POST /api/admin/discovery/flag](#post-apiadmindiscoveryflag)
7. [Budget & Health API](#budget--health-api)
   - [GET /api/budget](#get-apibudget)
   - [GET /health](#get-health)

---

## Global Conventions

### SSE Event Schema

All streaming endpoints use [Server-Sent Events (SSE)](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events). Each event is a single `data:` line followed by a blank line:

```
data: {"type": "<event_type>", ...payload...}\n\n
```

There are three event types:

#### `step` — Progress notification

Emitted multiple times during a long-running analysis to indicate current progress stage.

| Field | Type   | Description                          |
|-------|--------|--------------------------------------|
| type  | string | Always `"step"`                      |
| msg   | string | Human-readable progress message      |

```json
{"type": "step", "msg": "Checking analysis cache…"}
```

#### `done` — Final result

Emitted exactly once when analysis is complete. The `data` field contains the full result payload (schema varies by endpoint — see individual endpoint sections).

| Field | Type   | Description                               |
|-------|--------|-------------------------------------------|
| type  | string | Always `"done"`                           |
| data  | object | Full analysis result (endpoint-specific)  |

```json
{"type": "done", "data": { ... }}
```

#### `error` — Terminal error

Emitted when a recoverable or fatal error prevents the analysis from completing. The stream ends after this event.

| Field | Type   | Description                          |
|-------|--------|--------------------------------------|
| type  | string | Always `"error"`                     |
| msg   | string | Human-readable error description     |

```json
{"type": "error", "msg": "No data found for \"Genesis 99:1\". Check spelling — e.g. \"Isaiah 7:14\""}
```

**JavaScript consumption pattern:**

```javascript
const es = new EventSource('/api/divergence/stream?ref=Isaiah+7:14');

es.onmessage = (event) => {
  const payload = JSON.parse(event.data);

  if (payload.type === 'step')  { /* update progress UI */ }
  if (payload.type === 'done')  { es.close(); renderResult(payload.data); }
  if (payload.type === 'error') { es.close(); showError(payload.msg); }
};
```

---

### Authentication

Most endpoints are public. One endpoint requires an admin key:

| Endpoint                          | Auth required        |
|-----------------------------------|----------------------|
| `POST /api/admin/discovery/flag`  | `BIBCRIT_ADMIN_KEY`  |

Pass the key as the `key` query parameter:

```
POST /api/admin/discovery/flag?ref=Isaiah+7:14&ready=true&key=<BIBCRIT_ADMIN_KEY>
```

The `BIBCRIT_ADMIN_KEY` value is set via environment variable on the server. Requests with a missing or incorrect key receive:

```json
HTTP 403
{"error": "Unauthorized"}
```

---

### Rate Limiting & Budget Cap

BibCrit enforces a **monthly Claude API spend cap** to prevent runaway costs. The cap is configured via the `BIBCRIT_API_CAP_USD` environment variable (default: `$10.00`).

- Spend is tracked in a `budget` table in Supabase (falls back to disk at `data/cache/budget.json`).
- When the monthly cap is reached, all SSE stream endpoints return an `error` event with a message indicating the budget is exhausted for the month.
- Cached analyses (already stored in Supabase or disk cache) are always served without calling the Claude API and are **never** subject to the cap.
- The cache key is `sha256(reference | tool | prompt_version | model_version)`. Cache hits are instant.
- The Claude model used for all analysis tools is **`claude-sonnet-4-5-20250929`** ($3/MTok input, $15/MTok output).

---

### Common Error Responses

| Status | Body                                                              | Cause                                      |
|--------|-------------------------------------------------------------------|--------------------------------------------|
| 400    | `{"error": "ref parameter required"}`                            | Missing required query parameter           |
| 400    | `{"error": "chapter must be an integer"}`                        | Non-integer value for `chapter`            |
| 400    | `{"error": "offset and limit must be integers"}`                 | Non-integer pagination params              |
| 403    | `{"error": "Unauthorized"}`                                      | Missing/wrong admin key                    |
| 404    | `{"error": "No data found for \"...\". Check spelling"}`         | Reference not in corpus                    |
| 404    | `{"error": "No cached analysis for \"...\". Run ... first."}`    | Export requested before analysis run       |
| 501    | `{"error": "Numerical SBL export not yet implemented"}`          | Feature stub                               |
| 503    | `{"error": "Server not ready — corpus or pipeline not initialized"}` | App still booting or init failed       |

---

## Page Routes

These routes render full HTML pages. They accept optional `lang` and reference query parameters for i18n and pre-population.

### GET /

**Description:** Home / landing page.

| Parameter | Type   | Required | Default | Description             |
|-----------|--------|----------|---------|-------------------------|
| lang      | string | optional | `en`    | UI language code        |

**Example:**
```bash
curl http://localhost:5000/
curl http://localhost:5000/?lang=en
```

---

### GET /divergence

**Description:** MT/LXX Divergence Analyzer page. Optionally pre-populates the reference field.

| Parameter | Type   | Required | Default | Description                             |
|-----------|--------|----------|---------|-----------------------------------------|
| lang      | string | optional | `en`    | UI language code                        |
| ref       | string | optional | `""`    | Biblical reference to pre-load, e.g. `Isaiah 7:14` |

**Example:**
```bash
curl "http://localhost:5000/divergence?ref=Isaiah+7:14"
```

---

### GET /backtranslation

**Description:** Vorlage Back-Translation page. Optionally pre-populates the reference field.

| Parameter | Type   | Required | Default | Description                             |
|-----------|--------|----------|---------|-----------------------------------------|
| lang      | string | optional | `en`    | UI language code                        |
| ref       | string | optional | `""`    | Biblical reference to pre-load          |

**Example:**
```bash
curl "http://localhost:5000/backtranslation?ref=Isaiah+53:4"
```

---

### GET /scribal

**Description:** Scribal Tendency Profiler page. Optionally pre-populates the book selector.

| Parameter | Type   | Required | Default | Description                         |
|-----------|--------|----------|---------|-------------------------------------|
| lang      | string | optional | `en`    | UI language code                    |
| book      | string | optional | `""`    | Book name to pre-select, e.g. `Isaiah` |

**Example:**
```bash
curl "http://localhost:5000/scribal?book=Isaiah"
```

---

### GET /numerical

**Description:** Numerical Discrepancy Modeler page. Optionally pre-populates the reference field.

| Parameter | Type   | Required | Default | Description                             |
|-----------|--------|----------|---------|-----------------------------------------|
| lang      | string | optional | `en`    | UI language code                        |
| ref       | string | optional | `""`    | Biblical reference to pre-load          |

**Example:**
```bash
curl "http://localhost:5000/numerical?ref=Genesis+5:3"
```

---

### GET /discovery

**Description:** Discovery page — public-facing, plain-language findings cards. The first 12 cards are server-rendered; additional cards are loaded via the `/api/discovery/cards` endpoint.

| Parameter | Type   | Required | Default | Description      |
|-----------|--------|----------|---------|------------------|
| lang      | string | optional | `en`    | UI language code |

**Example:**
```bash
curl http://localhost:5000/discovery
```

---

## Textual Analysis API

### GET /api/divergence/stream

**Description:** SSE stream. Runs MT/LXX divergence analysis for a single biblical reference, serving from cache when available or calling Claude when not. Streams step-by-step progress then the full result.

**Response format:** `text/event-stream`

**Headers returned:**
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`

#### Query Parameters

| Parameter | Type   | Required | Description                                          | Example       |
|-----------|--------|----------|------------------------------------------------------|---------------|
| ref       | string | required | Biblical reference in "Book Chapter:Verse" format    | `Isaiah 7:14` |

#### SSE Event Sequence

1. `step` — `"Loading verse text…"`
2. `step` — `"Checking analysis cache…"`
3. `step` — one of:
   - `"Found in cache — loading instantly"` (cache hit)
   - `"Analyzing — new passages typically take 60–90s…"` (cache miss, calls Claude)
4. `done` — full result payload (see below), **or** `error` if anything fails

#### `done` Payload Schema

```json
{
  "type": "done",
  "data": {
    "reference": "Isaiah 7:14",
    "mt_words": [
      {
        "position": 1,
        "word_text": "לָכֵן",
        "lemma": "לָכֵן",
        "morph": "AdvP",
        "strong": "H3651"
      }
    ],
    "lxx_words": [
      {
        "position": 1,
        "word_text": "διὰ",
        "lemma": "διά",
        "morph": "Prep",
        "strong": "G1223"
      }
    ],
    "divergences": [
      {
        "divergence_type": "different_vorlage",
        "mt_text": "הָעַלְמָה",
        "lxx_text": "ἡ παρθένος",
        "confidence": 0.92,
        "explanation": "The LXX renders the Hebrew עַלְמָה as παρθένος ('virgin') rather than the more general 'young woman', suggesting a theological interpretive choice or a different Vorlage.",
        "scholarly_note": "This divergence has been extensively discussed in textual criticism and New Testament scholarship.",
        "references": ["Isa 7:14 LXX", "Matt 1:23"]
      }
    ],
    "summary": "Isaiah 7:14 shows a significant theological divergence…",
    "analysis_plain": "In plain language, the translators of the LXX made a choice here…",
    "hypothesis": "The LXX translator interpreted עַלְמָה in light of messianic expectation…",
    "confidence": 0.88,
    "model": "claude-sonnet-4-5-20250929",
    "cached": true
  }
}
```

**`mt_words` / `lxx_words` item schema:**

| Field      | Type    | Description                            |
|------------|---------|----------------------------------------|
| position   | integer | 1-based word position in verse         |
| word_text  | string  | Surface form (Hebrew or Greek)         |
| lemma      | string  | Dictionary/lemma form                  |
| morph      | string  | Morphological tag                      |
| strong     | string  | Strong's number (e.g. `H3651`, `G1223`) |

**`divergences` item schema:**

| Field           | Type    | Description                                             |
|-----------------|---------|---------------------------------------------------------|
| divergence_type | string  | Classification — see type list below                   |
| mt_text         | string  | Hebrew word(s) involved                                 |
| lxx_text        | string  | Greek word(s) involved                                  |
| confidence      | float   | 0.0–1.0 confidence score                                |
| explanation     | string  | Scholarly explanation of the divergence                 |
| scholarly_note  | string  | Additional notes, manuscript references                 |
| references      | array   | List of related reference strings                       |

**Divergence type values:** `different_vorlage`, `theological_tendency`, `scribal_error`, `translation_technique`, `plus`, `minus`, `transposition`, `harmonization`, `other`

#### Example curl

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:5000/api/divergence/stream?ref=Isaiah+7:14"
```

#### Example SSE output

```
data: {"type": "step", "msg": "📖 Loading verse text…"}

data: {"type": "step", "msg": "🔍 Checking analysis cache…"}

data: {"type": "step", "msg": "⚡ Found in cache — loading instantly"}

data: {"type": "done", "data": {"reference": "Isaiah 7:14", "divergences": [...], ...}}
```

---

### GET /api/backtranslation/stream

**Description:** SSE stream. Reconstructs the probable Hebrew Vorlage underlying a given LXX passage using Tov's retroversion methodology. Streams progress then the full result.

**Response format:** `text/event-stream`

**Headers returned:**
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`

#### Query Parameters

| Parameter | Type   | Required | Description                                          | Example        |
|-----------|--------|----------|------------------------------------------------------|----------------|
| ref       | string | required | Biblical reference in "Book Chapter:Verse" format    | `Isaiah 53:4`  |

#### SSE Event Sequence

1. `step` — `"Loading verse text…"`
2. `step` — `"Checking analysis cache…"`
3. `step` — one of:
   - `"Found in cache — loading instantly"` (cache hit)
   - `"Reconstructing Vorlage — new passages typically take 60–90s…"` (cache miss)
4. `done` — full result payload, **or** `error` if LXX data is not found or analysis fails

**Note:** This endpoint requires LXX data for the reference. If the LXX is unavailable, an `error` event is emitted: `"No LXX data found for \"...\". Check spelling"`. MT data is supplementary and will not cause failure if absent.

#### `done` Payload Schema

```json
{
  "type": "done",
  "data": {
    "reference": "Isaiah 53:4",
    "lxx_words": [ { "position": 1, "word_text": "οὗτος", "lemma": "οὗτος", "morph": "DPro", "strong": "G3778" } ],
    "mt_words":  [ { "position": 1, "word_text": "אָכֵן", "lemma": "אָכֵן", "morph": "Adv", "strong": "H0403" } ],
    "vorlage_reconstructions": [
      {
        "lxx_word": "ἀσθενείας",
        "probable_vorlage": "חֳלָיֵנוּ",
        "confidence": 0.85,
        "retroversion_method": "semantic",
        "note": "LXX reflects the MT reading; no Vorlage difference posited here.",
        "dss_evidence": "1QIsa-a agrees with MT"
      }
    ],
    "overall_assessment": "The LXX translator of Isaiah 53:4 worked from a Vorlage…",
    "analysis_plain": "In plain language, the LXX translator here…",
    "hypothesis": "The divergences suggest the translator interpreted חֳלָיֵנוּ differently…",
    "confidence": 0.82,
    "model": "claude-sonnet-4-5-20250929",
    "cached": false
  }
}
```

**`vorlage_reconstructions` item schema:**

| Field               | Type   | Description                                                   |
|---------------------|--------|---------------------------------------------------------------|
| lxx_word            | string | The Greek word being analyzed                                 |
| probable_vorlage    | string | Reconstructed Hebrew Vorlage word                             |
| confidence          | float  | 0.0–1.0 confidence score                                      |
| retroversion_method | string | Method used: `semantic`, `phonetic`, `contextual`, etc.       |
| note                | string | Scholarly justification                                       |
| dss_evidence        | string | Dead Sea Scrolls evidence, if any                             |

#### Example curl

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:5000/api/backtranslation/stream?ref=Isaiah+53:4"
```

---

### GET /api/divergence

**Description:** Synchronous (non-streaming) divergence analysis. Returns the same payload as the `done` event of `/api/divergence/stream` but as a standard JSON response. Prefer the streaming endpoint for UI use — this endpoint is suitable for programmatic/batch use.

**Response format:** `application/json`

#### Query Parameters

| Parameter | Type   | Required | Description                          | Example       |
|-----------|--------|----------|--------------------------------------|---------------|
| ref       | string | required | Biblical reference                   | `Isaiah 7:14` |

#### Example curl

```bash
curl "http://localhost:5000/api/divergence?ref=Isaiah+7:14"
```

#### Example response

```json
{
  "reference": "Isaiah 7:14",
  "mt_words": [ ... ],
  "lxx_words": [ ... ],
  "divergences": [ ... ],
  "summary": "...",
  "analysis_plain": "...",
  "hypothesis": "...",
  "confidence": 0.88,
  "model": "claude-sonnet-4-5-20250929",
  "cached": true
}
```

---

### GET /api/divergence/export/sbl

**Description:** Returns SBL-style footnote strings for each divergence in a previously-analyzed passage. The analysis must have been run first (i.e., a cache entry must exist). Intended for copy-paste into academic papers.

**Response format:** `application/json`

#### Query Parameters

| Parameter | Type   | Required | Description              | Example       |
|-----------|--------|----------|--------------------------|---------------|
| ref       | string | required | Biblical reference        | `Isaiah 7:14` |

#### Example curl

```bash
curl "http://localhost:5000/api/divergence/export/sbl?ref=Isaiah+7:14"
```

#### Example response

```json
{
  "reference": "Isaiah 7:14",
  "footnotes": [
    "MT reads הָעַלְמָה; LXX ἡ παρθένος. The Greek translator rendered the Hebrew with παρθένος ('virgin'), a term more specific than the source. Cf. Matt 1:23.",
    "..."
  ]
}
```

**Error — analysis not yet run:**
```json
HTTP 404
{
  "error": "No cached analysis for \"Isaiah 7:14\". Run the Divergence Analyzer first."
}
```

---

### GET /api/divergence/export/bibtex

**Description:** Returns BibTeX entry strings for each divergence in a previously-analyzed passage. The analysis must have been run first.

**Response format:** `application/json`

#### Query Parameters

| Parameter | Type   | Required | Description              | Example       |
|-----------|--------|----------|--------------------------|---------------|
| ref       | string | required | Biblical reference        | `Isaiah 7:14` |

#### Example curl

```bash
curl "http://localhost:5000/api/divergence/export/bibtex?ref=Isaiah+7:14"
```

#### Example response

```json
{
  "reference": "Isaiah 7:14",
  "bibtex": "@misc{Isaiah_7_14_div1,\n  title = {MT/LXX divergence at Isaiah 7:14},\n  note  = {LXX ἡ παρθένος vs. MT הָעַלְמָה. Different Vorlage or theological tendency.}\n}\n\n@misc{..."
}
```

---

### GET /api/books

**Description:** Returns a list of book names available in the corpus for a given textual tradition.

**Response format:** `application/json`

#### Query Parameters

| Parameter  | Type   | Required | Default | Description                        | Example |
|------------|--------|----------|---------|------------------------------------|---------|
| tradition  | string | optional | `MT`    | Textual tradition: `MT` or `LXX`   | `LXX`   |

#### Example curl

```bash
curl "http://localhost:5000/api/books?tradition=MT"
curl "http://localhost:5000/api/books?tradition=LXX"
```

#### Example response

```json
{
  "books": ["Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Isaiah", "Psalms"]
}
```

**Note:** Returns `{"books": []}` if the corpus is not yet initialized rather than a 503 error.

---

### GET /api/chapters

**Description:** Returns available chapter numbers for a given book and textual tradition.

**Response format:** `application/json`

#### Query Parameters

| Parameter  | Type   | Required | Default | Description                         | Example   |
|------------|--------|----------|---------|-------------------------------------|-----------|
| book       | string | required |         | Book name                           | `Isaiah`  |
| tradition  | string | optional | `MT`    | Textual tradition: `MT` or `LXX`    | `MT`      |

#### Example curl

```bash
curl "http://localhost:5000/api/chapters?book=Isaiah&tradition=MT"
```

#### Example response

```json
{
  "chapters": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
}
```

---

### GET /api/verses

**Description:** Returns available verse numbers for a given book, chapter, and textual tradition.

**Response format:** `application/json`

#### Query Parameters

| Parameter  | Type    | Required | Default | Description                          | Example  |
|------------|---------|----------|---------|--------------------------------------|----------|
| book       | string  | required |         | Book name                            | `Isaiah` |
| chapter    | integer | optional | `1`     | Chapter number (must be an integer)  | `7`      |
| tradition  | string  | optional | `MT`    | Textual tradition: `MT` or `LXX`     | `MT`     |

#### Example curl

```bash
curl "http://localhost:5000/api/verses?book=Isaiah&chapter=7&tradition=MT"
```

#### Example response

```json
{
  "verses": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25]
}
```

---

## Hypothesis Voting API

These endpoints allow users to upvote or downvote the central scholarly hypothesis for a given reference. Votes are stored in Supabase (`hypothesis_votes` table) with a disk fallback at `data/cache/votes.json`.

### GET /api/hypothesis/votes

**Description:** Returns the current upvote and downvote counts for a reference.

**Response format:** `application/json`

#### Query Parameters

| Parameter | Type   | Required | Description        | Example       |
|-----------|--------|----------|--------------------|---------------|
| ref       | string | required | Biblical reference  | `Isaiah 7:14` |

#### Example curl

```bash
curl "http://localhost:5000/api/hypothesis/votes?ref=Isaiah+7:14"
```

#### Example response

```json
{
  "upvotes": 14,
  "downvotes": 2
}
```

---

### POST /api/hypothesis/vote

**Description:** Casts or retracts a single vote on the hypothesis for a reference. Votes are clamped at 0 (cannot go negative). All parameters are passed as query parameters.

**Response format:** `application/json`

#### Query Parameters

| Parameter | Type   | Required | Description                                     | Example       |
|-----------|--------|----------|-------------------------------------------------|---------------|
| ref       | string | required | Biblical reference                               | `Isaiah 7:14` |
| direction | string | required | Vote direction: `up` or `down`                  | `up`          |
| action    | string | optional | `cast` (default) to add, or `retract` to remove | `cast`        |

#### Example curl — cast an upvote

```bash
curl -X POST \
  "http://localhost:5000/api/hypothesis/vote?ref=Isaiah+7:14&direction=up&action=cast"
```

#### Example curl — retract an upvote

```bash
curl -X POST \
  "http://localhost:5000/api/hypothesis/vote?ref=Isaiah+7:14&direction=up&action=retract"
```

#### Example response

```json
{
  "upvotes": 15,
  "downvotes": 2
}
```

**Error — missing or invalid parameters:**
```json
HTTP 400
{"error": "ref and direction (up|down) required"}
```

---

## Critical Analysis API

### GET /api/scribal/stream

**Description:** SSE stream. Profiles the scribal tendencies of the LXX translator of a given biblical book across multiple dimensions (literalness, theological tendency, expansion vs. abbreviation, etc.). Builds sample passages from the corpus where available, then calls Claude.

**Response format:** `text/event-stream`

**Headers returned:**
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`

#### Query Parameters

| Parameter | Type   | Required | Description                                           | Example   |
|-----------|--------|----------|-------------------------------------------------------|-----------|
| book      | string | required | Biblical book name                                    | `Isaiah`  |

**Books with pre-configured sample passages:** Isaiah, Jeremiah, Psalms, Genesis, Deuteronomy, Exodus, Proverbs, Job, Micah, Zechariah. Other books fall back to Claude's training knowledge.

#### SSE Event Sequence

1. `step` — `"Loading sample passages…"`
2. `step` — `"Checking analysis cache…"`
3. `step` — one of:
   - `"Found in cache — loading instantly"` (cache hit)
   - `"Profiling scribal tendencies — this typically takes 60–90s…"` (cache miss)
4. `done` — full result payload, **or** `error`

#### `done` Payload Schema

```json
{
  "type": "done",
  "data": {
    "book": "Isaiah",
    "translator_name": "LXX Isaiah",
    "dimensions": [
      {
        "dimension": "translation_literalness",
        "score": 0.72,
        "summary": "The translator of Isaiah is moderately literal, with significant freedom in poetic passages.",
        "examples": [
          {
            "reference": "Isaiah 7:14",
            "note": "παρθένος for עַלְמָה shows interpretive rather than literal translation."
          }
        ]
      },
      {
        "dimension": "theological_tendency",
        "score": 0.65,
        "summary": "Consistent Messianic intensification throughout the book.",
        "examples": []
      }
    ],
    "overall_profile": "The LXX translator of Isaiah was a theologically sophisticated interpreter…",
    "analysis_plain": "In plain language, this translator tended to…",
    "confidence": 0.85,
    "model": "claude-sonnet-4-5-20250929",
    "cached": false
  }
}
```

**`dimensions` item schema:**

| Field     | Type   | Description                                               |
|-----------|--------|-----------------------------------------------------------|
| dimension | string | Dimension name, snake_case                                |
| score     | float  | 0.0–1.0 score for this dimension                          |
| summary   | string | Prose summary of the translator's tendency on this axis   |
| examples  | array  | Supporting examples (each has `reference` and `note`)     |

#### Example curl

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:5000/api/scribal/stream?book=Isaiah"
```

---

### GET /api/numerical/stream

**Description:** SSE stream. Models the numerical discrepancies between the MT, LXX, and Samaritan Pentateuch for a given reference (particularly useful for patriarchal chronologies and genealogies). Calls Claude for analysis.

**Response format:** `text/event-stream`

**Headers returned:**
- `Cache-Control: no-cache`
- `X-Accel-Buffering: no`

#### Query Parameters

| Parameter | Type   | Required | Description                                           | Example      |
|-----------|--------|----------|-------------------------------------------------------|--------------|
| ref       | string | required | Biblical reference                                    | `Genesis 5:3` |

#### SSE Event Sequence

1. `step` — `"Checking analysis cache…"`
2. `step` — one of:
   - `"Found in cache — loading instantly"` (cache hit)
   - `"Modeling numerical traditions — this typically takes 30–60s…"` (cache miss)
3. `done` — full result payload, **or** `error`

**Note:** Unlike the divergence and backtranslation streams, the numerical stream does not load corpus text before the cache check (it passes only the reference to Claude, which draws on training knowledge about numerical traditions).

#### `done` Payload Schema

```json
{
  "type": "done",
  "data": {
    "reference": "Genesis 5:3",
    "mt_value": 130,
    "lxx_value": 230,
    "sp_value": 130,
    "discrepancy_type": "chronological",
    "explanations": [
      {
        "theory": "LXX inflation theory",
        "description": "The LXX systematically adds 100 years to the ages of pre-flood patriarchs at the birth of their first son.",
        "confidence": 0.88,
        "scholarly_support": "Hendel, Methuselah's Begats (2007)"
      }
    ],
    "overall_assessment": "The LXX preserves an independent numerical tradition…",
    "analysis_plain": "The Greek Bible records Adam being 230 when Seth was born, versus 130 in the Hebrew…",
    "confidence": 0.83,
    "model": "claude-sonnet-4-5-20250929",
    "cached": true
  }
}
```

#### Example curl

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:5000/api/numerical/stream?ref=Genesis+5:3"
```

---

### GET /api/scribal/export/sbl

**Description:** Returns SBL-style footnote strings summarizing each scribal tendency dimension for a previously-analyzed book. The scribal analysis must have been run first.

**Response format:** `application/json`

#### Query Parameters

| Parameter | Type   | Required | Description    | Example  |
|-----------|--------|----------|----------------|----------|
| book      | string | required | Biblical book  | `Isaiah` |

#### Example curl

```bash
curl "http://localhost:5000/api/scribal/export/sbl?book=Isaiah"
```

#### Example response

```json
{
  "book": "Isaiah",
  "footnotes": [
    "LXX Isaiah (Translation Literalness score: 0.72): The translator of Isaiah is moderately literal, with significant freedom in poetic passages. Cf. Isaiah 7:14: παρθένος for עַלְמָה shows interpretive rather than literal translation.",
    "LXX Isaiah (Theological Tendency score: 0.65): Consistent Messianic intensification throughout the book."
  ]
}
```

**Error — analysis not yet run:**
```json
HTTP 404
{"error": "No cached analysis for \"Isaiah\". Run the Scribal Profiler first."}
```

---

### GET /api/numerical/export/sbl

**Description:** SBL export for numerical analysis. **Not yet implemented.**

**Response format:** `application/json`

#### Example response

```json
HTTP 501
{"error": "Numerical SBL export not yet implemented"}
```

---

## Discovery API

### GET /api/discovery/cards

**Description:** Returns a paginated list of discovery cards — plain-language findings drawn from the analysis cache where `discovery_ready=true`. Designed for infinite-scroll / load-more patterns. The first card (index 0 at offset 0) is selected from the most compelling divergence types (`different_vorlage`, `theological_tendency`, `scribal_error`); remaining cards are shuffled for variety. Requests are capped at 50 cards per page.

**Response format:** `application/json`

#### Query Parameters

| Parameter | Type    | Required | Default | Description                                | Example |
|-----------|---------|----------|---------|--------------------------------------------|---------|
| offset    | integer | optional | `0`     | Number of cards to skip (for pagination)   | `12`    |
| limit     | integer | optional | `12`    | Max cards to return (server cap: 50)       | `12`    |

#### Example curl

```bash
# First page
curl "http://localhost:5000/api/discovery/cards"

# Second page
curl "http://localhost:5000/api/discovery/cards?offset=12&limit=12"
```

#### Example response

```json
{
  "cards": [
    {
      "reference": "Isaiah 7:14",
      "divergence_type": "theological_tendency",
      "analysis_plain": "The Greek translators chose 'virgin' (παρθένος) where the Hebrew has 'young woman' (עַלְמָה), a choice that profoundly shaped later Christian interpretation of this passage.",
      "confidence": 0.92,
      "title": "A Word That Changed History"
    },
    {
      "reference": "Deuteronomy 32:8",
      "divergence_type": "different_vorlage",
      "analysis_plain": "...",
      "confidence": 0.87,
      "title": "..."
    }
  ],
  "offset": 0,
  "limit": 12,
  "total": 34,
  "has_more": true
}
```

**Response fields:**

| Field    | Type    | Description                                            |
|----------|---------|--------------------------------------------------------|
| cards    | array   | Array of discovery card objects (see below)            |
| offset   | integer | Offset used for this response                          |
| limit    | integer | Limit used for this response                           |
| total    | integer | Total number of available cards                        |
| has_more | boolean | Whether more cards exist beyond this page              |

**Discovery card object:**

| Field           | Type   | Description                                               |
|-----------------|--------|-----------------------------------------------------------|
| reference       | string | Biblical reference, e.g. `"Isaiah 7:14"`                  |
| divergence_type | string | Divergence classification (see type list above)           |
| analysis_plain  | string | Plain-language description suitable for general audiences |
| confidence      | float  | 0.0–1.0 confidence score from the original analysis      |
| title           | string | Short display title for the card (if present)             |

**Fallback behavior:** If fewer than 3 `discovery_ready=true` entries exist in the cache, the endpoint falls back to returning all cached analyses with `confidence >= 0.6`. This supports early-content / demo mode.

---

### POST /api/admin/discovery/flag

**Description:** Toggles the `discovery_ready` flag on a cached analysis entry, controlling whether it appears in the public Discovery feed. Requires the `BIBCRIT_ADMIN_KEY` environment variable to be set on the server, and the matching key to be passed as the `key` query parameter.

**Response format:** `application/json`

**Authentication required:** Yes — see [Authentication](#authentication)

#### Query Parameters

| Parameter | Type   | Required | Description                                                         | Example       |
|-----------|--------|----------|---------------------------------------------------------------------|---------------|
| ref       | string | required | Biblical reference to flag                                          | `Isaiah 7:14` |
| ready     | string | optional | `"true"` (default) to publish, `"false"` to unpublish              | `true`        |
| key       | string | required | Must match `BIBCRIT_ADMIN_KEY` environment variable                 | `mySecretKey` |

#### Example curl — publish a card

```bash
curl -X POST \
  "http://localhost:5000/api/admin/discovery/flag?ref=Isaiah+7:14&ready=true&key=mySecretKey"
```

#### Example curl — unpublish a card

```bash
curl -X POST \
  "http://localhost:5000/api/admin/discovery/flag?ref=Isaiah+7:14&ready=false&key=mySecretKey"
```

#### Example response — success

```json
{
  "reference": "Isaiah 7:14",
  "discovery_ready": true
}
```

#### Error responses

```json
HTTP 403
{"error": "Unauthorized"}
```

```json
HTTP 404
{"error": "No cached analysis found for \"Isaiah 7:14\""}
```

```json
HTTP 503
{"error": "Pipeline not initialized"}
```

---

## Budget & Health API

### GET /api/budget

**Description:** Returns the current monthly Claude API spend, the configured cap, and the percentage of cap consumed. Useful for monitoring dashboards.

**Response format:** `application/json`

#### Query Parameters

None.

#### Example curl

```bash
curl http://localhost:5000/api/budget
```

#### Example response

```json
{
  "spend_usd": 1.23,
  "cap_usd": 10.0,
  "pct": 12.3,
  "month": "2026-03"
}
```

**Response fields:**

| Field     | Type   | Description                                                                    |
|-----------|--------|--------------------------------------------------------------------------------|
| spend_usd | float  | Total spend in USD for the current calendar month                              |
| cap_usd   | float  | Configured monthly cap in USD (set via `BIBCRIT_API_CAP_USD`, default `10.0`) |
| pct       | float  | `(spend_usd / cap_usd) * 100`, rounded to 1 decimal place                     |
| month     | string | Current month in `YYYY-MM` format                                              |

**Note:** If the pipeline is not initialized, returns `{"spend_usd": 0.0, "cap_usd": 10.0, "pct": 0.0, "month": ""}` rather than an error.

---

### GET /health

**Description:** Simple health check endpoint. Returns `200 OK` when the server is running.

**Response format:** `application/json`

#### Example curl

```bash
curl http://localhost:5000/health
```

#### Example response

```json
{
  "status": "ok",
  "app": "bibcrit"
}
```

**Note:** This endpoint does not check whether the corpus or pipeline are initialized — it only confirms the Flask application is responding. Use `/api/budget` or attempt an analysis request to verify full readiness.

---

## Environment Variables Summary

| Variable              | Default | Description                                                               |
|-----------------------|---------|---------------------------------------------------------------------------|
| `ANTHROPIC_API_KEY`   | —       | Required for any analysis that is not cached. No default.                 |
| `BIBCRIT_API_CAP_USD` | `10.0`  | Monthly Claude API spend cap in USD                                       |
| `BIBCRIT_ADMIN_KEY`   | —       | Secret key for admin endpoints. If unset, all admin requests return 403.  |
| `SUPABASE_URL`        | `""`    | Supabase project URL for persistent cache and budget tracking             |
| `SUPABASE_KEY`        | `""`    | Supabase service role or anon key                                         |

When `SUPABASE_URL` / `SUPABASE_KEY` are not set, BibCrit falls back to disk-based storage under `data/cache/`.
