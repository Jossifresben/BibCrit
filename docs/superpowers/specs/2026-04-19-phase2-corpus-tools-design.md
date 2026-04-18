# BibCrit Phase 2: Targum Corpus, NT Text Analyzer, Vulgate Corpus

## Overview

Phase 2 adds two new analytical tools and two new corpus traditions to BibCrit. All work slots into the existing three-layer architecture (corpus → pipeline → presentation) without changes to core patterns.

**Goal:** Ship the Targum Comparator and NT Textual Tradition Analyzer as fully data-driven tools, backed by real Aramaic and Latin corpora, while enriching three existing tools with Vulgate witness data.

**Architecture:** New tools follow the established 9-file pattern (blueprint, pipeline method, prompt, template, JS, i18n, ref_utils, app.py route, preseed). New corpora add tradition keys to `corpus.py._TRADITION_DIRS` and ingest scripts that output CSV files in the standard schema.

**Tech Stack:** Flask, Anthropic Claude API (`claude-sonnet-4-5-20250929`), Sefaria GitHub export (Targum), scrollmapper/bible_databases GitHub (Clementine Vulgate), existing SBLGNT (NT tool).

---

## Build Order

| # | Deliverable | Corpus dependency |
|---|---|---|
| 1 | `scripts/ingest_targum_sefaria.py` + `data/corpora/targ_sefaria/` | Sefaria GitHub export |
| 2 | Targum Comparator tool (`/targum`) | Step 1 |
| 3 | NT Textual Tradition Analyzer (`/nt-text`) | SBLGNT (already loaded) |
| 4 | `scripts/ingest_vulgate_clementine.py` + `data/corpora/vul_clementine/` | scrollmapper GitHub |
| 5 | Vulgate integration into 3 existing pipeline methods | Step 4 |

---

## Section 1: Targum Corpus

### Source

Sefaria GitHub export: `github.com/Sefaria/Sefaria-Export`

Bulk JSON files, no API rate limits, no scraping. License: CC BY-SA (compatible with BibCrit Apache 2.0 for analysis purposes; Sefaria text content attributed in Acknowledgements).

### Coverage

| Targum | Books | Estimated tokens |
|---|---|---|
| Onkelos | Genesis, Exodus, Leviticus, Numbers, Deuteronomy (5 books) | ~95,000 |
| Jonathan | Joshua, Judges, 1–2 Samuel, 1–2 Kings, Isaiah, Jeremiah, Ezekiel, 12 Minor Prophets (21 books) | ~190,000 |

**Total: ~285,000 Aramaic word tokens across 26 books.**

### Ingest Script: `scripts/ingest_targum_sefaria.py`

- Downloads JSON from `Sefaria-Export/json/` for each Targum book
- Splits Aramaic text into word tokens by whitespace (no morphological tagger available for plain Sefaria text)
- Writes one CSV per book: `data/corpora/targ_sefaria/{book_slug}_{targum}.csv`
  - e.g. `genesis_onkelos.csv`, `isaiah_jonathan.csv`
- CSV schema: `book_order, book, chapter, verse, reference, position, word_text, lemma, morph, strong, manuscript, tradition`
  - `tradition = 'TARG'`
  - `manuscript = 'Onkelos'` (Torah) or `'Jonathan'` (Prophets)
  - `lemma`, `morph`, `strong` = empty string (plain text only)

### Corpus registration

`biblical_core/corpus.py` — add to `_TRADITION_DIRS`:

```python
'TARG': 'targ_sefaria',
```

---

## Section 2: Targum Comparator Tool (`/targum`)

### Route

`GET /targum` → renders `templates/targum.html`
`GET /api/targum/stream?ref={ref}&lang={lang}` → SSE stream

### Pipeline method

`biblical_core/claude_pipeline.py` → `analyze_targum(reference, mt_text, lxx_text, targ_text, manuscript)`

- `manuscript`: `'Onkelos'` (if ref in Torah) or `'Jonathan'` (if ref in Prophets)
- Prompt file: `data/prompts/targum_v1.txt`
- Cache key: `SHA-256("{reference}|targum|v1|{model}")`
- Model: `claude-sonnet-4-5-20250929`

### Blueprint: `blueprints/targum.py`

Fetches:
```python
mt_words   = corpus.get_verse_words(reference, 'MT')
lxx_words  = corpus.get_verse_words(reference, 'LXX')
targ_words = corpus.get_verse_words(reference, 'TARG')

mt_text   = ' '.join(w.word_text for w in mt_words)   or ''
lxx_text  = ' '.join(w.word_text for w in lxx_words)  or ''
targ_text = ' '.join(w.word_text for w in targ_words) or ''

# detect manuscript from first targ word's .manuscript field
manuscript = targ_words[0].manuscript if targ_words else 'Onkelos'
```

### Prompt schema (`targum_v1.txt`)

Output JSON with keys:

| Key | Content |
|---|---|
| `synthesis` | 2–3 sentence overview of how the Targum renders this passage |
| `rendering_fidelity` | Word-level comparison: close rendering vs. substitution vs. expansion |
| `theological_modifications` | Divine name substitutions (Memra), anthropomorphism softening, angelological insertions |
| `targumic_expansions` | Paraphrastic additions absent from MT/LXX; parallels to Midrash where relevant |
| `messianic_reinterpretation` | Where Targum introduces messianic reading absent from MT |
| `lxx_alignment` | Where Targum and LXX agree against MT |
| `key_divergences` | Array of `{mt_word, targ_word, type, explanation}` objects |
| `assessment` | BibCrit confidence rating + recommended scholarly next steps |
| `citations` | SBL and BibTeX for Samely, Smelik, McNamara, Grossfeld |

Scholarly framework cited in prompt: Samely (1992), Smelik (1995), McNamara (1966), Grossfeld (1988).

### Template: `templates/targum.html`

- Extends `base.html`
- Passage input bar (same component as other tools)
- Three-column text display: MT Hebrew | Targum Aramaic | LXX Greek
- Manuscript badge: "Onkelos" (Torah) or "Jonathan" (Prophets)
- Structured result sections rendered via SSE (same pattern as `/dss`)
- Featured passages: Genesis 22:8, Isaiah 53:5, Exodus 3:14, Genesis 3:22

### JS: `static/targum.js`

Standard apparatus pattern: SSE connection, step indicators, progressive section reveal, copy/export buttons.

### i18n additions (`data/i18n.json`)

Keys needed (en + es):
- `targum_tool_title`, `targum_tool_description`
- `targum_rendering_fidelity`, `targum_theological_modifications`
- `targum_expansions`, `targum_messianic`, `targum_lxx_alignment`
- `targum_manuscript_onkelos`, `targum_manuscript_jonathan`
- `targum_featured_label`

### `ref_utils.py` validation

Targum covers Torah + Prophets only. Validate that input reference is in one of these 26 books; return a clear error for Writings (Psalms, Proverbs, Job, etc.).

---

## Section 3: NT Textual Tradition Analyzer (`/nt-text`)

### Route

`GET /nt-text` → renders `templates/nt_text.html`
`GET /api/nt-text/stream?ref={ref}&lang={lang}` → SSE stream

Note: URL uses hyphen (`nt-text`); `ENDPOINT_OVERRIDES` in `preseed_featured.py` already handles hyphenated endpoints (`{"nt_ot": "nt-ot"}` pattern — add `"nt_text": "nt-text"`).

### Pipeline method

`biblical_core/claude_pipeline.py` → `analyze_nt_text(reference, gnt_text)`

- Fetches SBLGNT words; passes Greek text + reference to Claude
- Prompt file: `data/prompts/nt_text_v1.txt`
- Cache key: `SHA-256("{reference}|nt_text|v1|{model}")`
- Model: `claude-sonnet-4-5-20250929`

### Blueprint: `blueprints/nt_text.py`

```python
gnt_words = corpus.get_verse_words(reference, 'GNT')
gnt_text  = ' '.join(w.word_text for w in gnt_words) or ''
```

### Prompt schema (`nt_text_v1.txt`)

Output JSON with keys:

| Key | Content |
|---|---|
| `text_basis` | SBLGNT reading; NA28/UBS5 alignment note; flag if known disputed locus |
| `manuscript_families` | Analysis of Alexandrian, Western, Byzantine, Caesarean support for received text |
| `metzger_rating` | A/B/C/D confidence rating per Metzger *Textual Commentary* methodology |
| `variant_register` | Array (up to 5): `{variant_text, manuscript_support, intrinsic_probability, transcriptional_probability, assessment}` |
| `disputed_passage` | Extended section triggered for Mark 16:9-20, John 7:53–8:11, Luke 22:43-44, 1 John 5:7-8, Acts 8:37, Romans 16:25-27 — null otherwise |
| `synthesis` | 2–3 sentence overview of the passage's text-critical stability |
| `assessment` | BibCrit rating + recommended reading + key open questions |
| `citations` | SBL and BibTeX for Metzger, Aland/Aland, Ehrman, Parker |

**Manuscript family witnesses cited in prompt:**
- Alexandrian: P66, P75, א (Sinaiticus), B (Vaticanus)
- Western: D (Bezae), Old Latin, Diatessaron
- Byzantine: Majority Text, Textus Receptus
- Caesarean: P45, W (Freer Gospels), family 1, family 13

### Template: `templates/nt_text.html`

- SBLGNT text display at top
- Manuscript family support visualization (bar or badge row)
- Metzger rating badge (A/B/C/D with colour coding)
- Variant register table
- Disputed passage extended section (shown/hidden based on `disputed_passage` null check)
- Featured passages: Mark 16:9, John 7:53, 1 John 5:7, Matthew 1:16

### JS: `static/nt_text.js`

Standard apparatus pattern + logic to show/hide `disputed_passage` section.

### i18n additions

Keys needed:
- `nt_text_tool_title`, `nt_text_tool_description`
- `nt_text_basis`, `nt_text_manuscript_families`, `nt_text_metzger_rating`
- `nt_text_variant_register`, `nt_text_disputed_passage`
- `nt_text_alexandrian`, `nt_text_western`, `nt_text_byzantine`, `nt_text_caesarean`
- `nt_text_rating_a`, `nt_text_rating_b`, `nt_text_rating_c`, `nt_text_rating_d`

### `ref_utils.py` validation

NT references only (Matthew–Revelation, 27 books). Reject OT references with clear error message pointing to the Ancient Witness Bridge for OT manuscript comparison.

---

## Section 4: Vulgate Corpus

### Source

`github.com/scrollmapper/bible_databases` — Clementine Vulgate in structured JSON/CSV format, verse-aligned, public domain.

### Coverage

All 73 books: 46 OT (including deuterocanonicals Tobit, Judith, 1–2 Maccabees, Sirach, Wisdom, Baruch) + 27 NT.

Estimated: ~600,000 Latin word tokens.

### Ingest Script: `scripts/ingest_vulgate_clementine.py`

- Downloads from scrollmapper GitHub
- Outputs one CSV per book in `data/corpora/vul_clementine/`
- `tradition = 'VUL'`, `manuscript = 'Clementine'`
- `lemma`, `morph`, `strong` = empty string (plain text only)

### Corpus registration

`biblical_core/corpus.py` — add to `_TRADITION_DIRS`:

```python
'VUL': 'vul_clementine',
```

---

## Section 5: Vulgate Integration into Existing Tools

Three existing pipeline methods updated. Pattern identical to how Peshitta was wired into `analyze_dss()`:

```python
vul_words = corpus.get_verse_words(reference, 'VUL')
vul_text  = ' '.join(w.word_text for w in vul_words) if vul_words else ''
# pass as: vul_text or "(corpus not loaded — use training knowledge)"
```

### Ancient Witness Bridge (`analyze_dss`)

Add `vul_text` parameter. Claude uses Vulgate as 4th-century Latin witness — particularly valuable for passages where Jerome chose the Hebrew Vorlage over LXX (e.g. Isaiah, Job) and for deuterocanonicals absent from MT.

### Manuscript Genealogy (`analyze_genealogy`)

Add `vul_text` parameter. Vulgate appears as a node in the Western transmission line. Jerome's translation decisions are cited as text-form evidence.

### Theological Revision Detector (`analyze_theological`)

Add `vul_text` parameter. Jerome's renderings as evidence for intentional theological shaping — especially Isaiah 7:14 (*almah* → *virgo*), Genesis 3:15 (*ipsa* vs. *ipse* controversy), Psalm 22:16 (*foderunt* vs. *leones*).

**No template changes required** for any of these three tools — tradition display is already flexible.

---

## Files Created or Modified

| File | Action |
|---|---|
| `scripts/ingest_targum_sefaria.py` | **New** |
| `scripts/ingest_vulgate_clementine.py` | **New** |
| `data/corpora/targ_sefaria/` | **New directory** (populated by ingest script) |
| `data/corpora/vul_clementine/` | **New directory** (populated by ingest script) |
| `biblical_core/corpus.py` | Modify — add `'TARG'` and `'VUL'` to `_TRADITION_DIRS` |
| `biblical_core/claude_pipeline.py` | Modify — add `analyze_targum()`, `analyze_nt_text()`; update `analyze_dss()`, `analyze_genealogy()`, `analyze_theological()` |
| `data/prompts/targum_v1.txt` | **New** |
| `data/prompts/nt_text_v1.txt` | **New** |
| `blueprints/targum.py` | **New** |
| `blueprints/nt_text.py` | **New** |
| `templates/targum.html` | **New** |
| `templates/nt_text.html` | **New** |
| `static/targum.js` | **New** |
| `static/nt_text.js` | **New** |
| `data/i18n.json` | Modify — add ~25 keys (en + es) |
| `biblical_core/ref_utils.py` | Modify — add Targum book validation, NT-only validation |
| `app.py` | Modify — register `/targum` and `/nt-text` blueprints + routes |
| `scripts/preseed_featured.py` | Modify — add 8 new featured passages (4 Targum + 4 NT) |
| `README.md` | Update — add two new tools to tool table; update corpus stats |
| `paper.md` | Update — update tool count (13), corpus traditions count (8); update word counts |

---

## Verification Checklist

1. `ls data/corpora/targ_sefaria/*.csv | wc -l` → 26 files (5 Onkelos + 21 Jonathan)
2. `ls data/corpora/vul_clementine/*.csv | wc -l` → 73 files
3. `python3 -c "from biblical_core.corpus import BiblicalCorpus; c = BiblicalCorpus(); c.set_data_dir('data'); words = c.get_verse_words('Genesis 22:8', 'TARG'); print([w.word_text for w in words])"` → list of Aramaic word tokens
4. `python3 -c "from biblical_core.corpus import BiblicalCorpus; c = BiblicalCorpus(); c.set_data_dir('data'); words = c.get_verse_words('Isaiah 7:14', 'VUL'); print([w.word_text for w in words])"` → Latin tokens including *virgo*
5. `/targum?ref=Genesis+22:8` → three-column view with Aramaic Targum text
6. `/nt-text?ref=Mark+16:9` → disputed passage extended section visible
7. `/dss?ref=Isaiah+7:14` → Vulgate column shows *virgo* reading
8. `python3 scripts/preseed_featured.py --tool targum` → all 4 passages cached
9. `python3 scripts/preseed_featured.py --tool nt_text` → all 4 passages cached
