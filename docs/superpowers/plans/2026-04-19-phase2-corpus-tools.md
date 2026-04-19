# BibCrit Phase 2: Corpus Additions & New Tools — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the Targum Comparator (`/targum`) and NT Textual Tradition Analyzer (`/nt-text`) as fully data-driven tools, backed by real Aramaic and Latin corpora, while enriching three existing tools (DSS Bridge, Genealogy, Theological Revision) with Vulgate witness data.

**Architecture:** New tools follow the 9-file pattern: prompt, pipeline method, blueprint, template, JS, i18n keys, ref_utils validation, app.py registration, preseed entries. New corpora add tradition keys to `corpus.py._TRADITION_DIRS` and ingest scripts that output CSVs in the standard schema. Vulgate integration bumps prompt versions for three existing methods (dss v6→v7, genealogy v1→v2, theological v1→v2) to avoid invalidating existing caches.

**Tech Stack:** Flask, Anthropic `claude-sonnet-4-5-20250929`, Sefaria JSON API (Targum), scrollmapper/bible_databases CSV (Vulgate), SBLGNT already loaded (NT tool).

**All paths are relative to the worktree root:** `.worktrees/phase1-literary-tools/`

---

## Task 1: Register TARG and VUL traditions + create corpus directories

**Files:**
- Modify: `biblical_core/corpus.py`

- [ ] **Step 1: Add TARG and VUL to _TRADITION_DIRS**

In `biblical_core/corpus.py`, find the `_TRADITION_DIRS` dict and add two entries:

```python
# Before (existing):
_TRADITION_DIRS: dict = {
    'MT': 'mt_etcbc', 'LXX': 'lxx_stepbible', 'GNT': 'gnt_opengnt',
    'DSS': 'dss', 'SP': 'sp_etcbc', 'PESH': 'pesh_etcbc',
}

# After:
_TRADITION_DIRS: dict = {
    'MT': 'mt_etcbc', 'LXX': 'lxx_stepbible', 'GNT': 'gnt_opengnt',
    'DSS': 'dss', 'SP': 'sp_etcbc', 'PESH': 'pesh_etcbc',
    'TARG': 'targ_sefaria', 'VUL': 'vul_clementine',
}
```

- [ ] **Step 2: Create corpus output directories**

```bash
mkdir -p data/corpora/targ_sefaria
mkdir -p data/corpora/vul_clementine
```

- [ ] **Step 3: Verify corpus recognises the new traditions**

```bash
python3 -c "
from biblical_core.corpus import BiblicalCorpus
c = BiblicalCorpus()
c.set_data_dir('data')
print('TARG' in c._TRADITION_DIRS)   # True
print('VUL'  in c._TRADITION_DIRS)   # True
"
```

Expected: two lines of `True`.

- [ ] **Step 4: Commit**

```bash
git add biblical_core/corpus.py
git commit -m "feat: register TARG and VUL traditions in corpus.py"
```

---

## Task 2: Targum ingest script

**Files:**
- Create: `scripts/ingest_targum_sefaria.py`

This script downloads Aramaic text from the Sefaria JSON API and writes one CSV per book into `data/corpora/targ_sefaria/`.

- [ ] **Step 1: Create the ingest script**

```python
#!/usr/bin/env python3
"""Download Targum Onkelos (Torah) and Targum Jonathan (Prophets) from Sefaria.

Usage:
    python scripts/ingest_targum_sefaria.py --out data/corpora/targ_sefaria/

Writes one CSV per book, e.g. genesis_onkelos.csv, isaiah_jonathan.csv.
Schema: book_order,book,chapter,verse,reference,position,word_text,lemma,morph,strong,manuscript,tradition
"""

import argparse
import csv
import os
import sys
import time
import urllib.request
import urllib.parse
import json

# Targum Onkelos: Torah (5 books)
ONKELOS_BOOKS = [
    ('Genesis',     1,  50, 'genesis_onkelos'),
    ('Exodus',      2,  40, 'exodus_onkelos'),
    ('Leviticus',   3,  27, 'leviticus_onkelos'),
    ('Numbers',     4,  36, 'numbers_onkelos'),
    ('Deuteronomy', 5,  34, 'deuteronomy_onkelos'),
]

# Targum Jonathan: Former + Latter Prophets (21 books)
JONATHAN_BOOKS = [
    ('Joshua',      6,  24, 'joshua_jonathan'),
    ('Judges',      7,  21, 'judges_jonathan'),
    ('1 Samuel',    9,  31, '1samuel_jonathan'),
    ('2 Samuel',    10, 24, '2samuel_jonathan'),
    ('1 Kings',     11, 22, '1kings_jonathan'),
    ('2 Kings',     12, 25, '2kings_jonathan'),
    ('Isaiah',      23, 66, 'isaiah_jonathan'),
    ('Jeremiah',    24, 52, 'jeremiah_jonathan'),
    ('Ezekiel',     26, 48, 'ezekiel_jonathan'),
    ('Hosea',       28, 14, 'hosea_jonathan'),
    ('Joel',        29, 3,  'joel_jonathan'),
    ('Amos',        30, 9,  'amos_jonathan'),
    ('Obadiah',     31, 1,  'obadiah_jonathan'),
    ('Jonah',       32, 4,  'jonah_jonathan'),
    ('Micah',       33, 7,  'micah_jonathan'),
    ('Nahum',       34, 3,  'nahum_jonathan'),
    ('Habakkuk',    35, 3,  'habakkuk_jonathan'),
    ('Zephaniah',   36, 3,  'zephaniah_jonathan'),
    ('Haggai',      37, 2,  'haggai_jonathan'),
    ('Zechariah',   38, 14, 'zechariah_jonathan'),
    ('Malachi',     39, 4,  'malachi_jonathan'),
]

SEFARIA_API = 'https://www.sefaria.org/api/texts'

SEFARIA_SLUGS = {
    'Genesis': 'Onkelos_Genesis',
    'Exodus': 'Onkelos_Exodus',
    'Leviticus': 'Onkelos_Leviticus',
    'Numbers': 'Onkelos_Numbers',
    'Deuteronomy': 'Onkelos_Deuteronomy',
    'Joshua': 'Targum_Jonathan_on_Joshua',
    'Judges': 'Targum_Jonathan_on_Judges',
    '1 Samuel': 'Targum_Jonathan_on_1_Samuel',
    '2 Samuel': 'Targum_Jonathan_on_2_Samuel',
    '1 Kings': 'Targum_Jonathan_on_1_Kings',
    '2 Kings': 'Targum_Jonathan_on_2_Kings',
    'Isaiah': 'Targum_Jonathan_on_Isaiah',
    'Jeremiah': 'Targum_Jonathan_on_Jeremiah',
    'Ezekiel': 'Targum_Jonathan_on_Ezekiel',
    'Hosea': 'Targum_Jonathan_on_Hosea',
    'Joel': 'Targum_Jonathan_on_Joel',
    'Amos': 'Targum_Jonathan_on_Amos',
    'Obadiah': 'Targum_Jonathan_on_Obadiah',
    'Jonah': 'Targum_Jonathan_on_Jonah',
    'Micah': 'Targum_Jonathan_on_Micah',
    'Nahum': 'Targum_Jonathan_on_Nahum',
    'Habakkuk': 'Targum_Jonathan_on_Habakkuk',
    'Zephaniah': 'Targum_Jonathan_on_Zephaniah',
    'Haggai': 'Targum_Jonathan_on_Haggai',
    'Zechariah': 'Targum_Jonathan_on_Zechariah',
    'Malachi': 'Targum_Jonathan_on_Malachi',
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong',
    'manuscript', 'tradition',
]


def fetch_chapter(slug: str, chapter: int) -> list[str] | None:
    """Fetch one chapter from Sefaria. Returns list of verse strings (Aramaic)."""
    url = f'{SEFARIA_API}/{urllib.parse.quote(slug)}.{chapter}?lang=he&context=0'
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        # 'he' field = Aramaic text array (one string per verse)
        verses = data.get('he', [])
        if isinstance(verses, str):
            return [verses]
        return verses if isinstance(verses, list) else []
    except Exception as e:
        print(f'    WARN fetch failed for {slug}.{chapter}: {e}', file=sys.stderr)
        return None


def strip_html(text: str) -> str:
    """Remove simple HTML tags from Sefaria text."""
    import re
    return re.sub(r'<[^>]+>', '', text).strip()


def process_book(book: str, book_order: int, num_chapters: int,
                 filename: str, manuscript: str, out_dir: str) -> int:
    """Download all chapters of a book and write CSV. Returns word count."""
    slug = SEFARIA_SLUGS[book]
    out_path = os.path.join(out_dir, f'{filename}.csv')
    word_count = 0

    with open(out_path, 'w', newline='', encoding='utf-8') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()

        for chapter in range(1, num_chapters + 1):
            verses = fetch_chapter(slug, chapter)
            if verses is None:
                # retry once after a short wait
                time.sleep(2)
                verses = fetch_chapter(slug, chapter)
            if not verses:
                continue

            for verse_idx, verse_text in enumerate(verses, start=1):
                cleaned = strip_html(verse_text)
                if not cleaned:
                    continue
                reference = f'{book} {chapter}:{verse_idx}'
                words = cleaned.split()
                for pos, word in enumerate(words, start=1):
                    writer.writerow({
                        'book_order': book_order,
                        'book':       book,
                        'chapter':    chapter,
                        'verse':      verse_idx,
                        'reference':  reference,
                        'position':   pos,
                        'word_text':  word,
                        'lemma':      '',
                        'morph':      '',
                        'strong':     '',
                        'manuscript': manuscript,
                        'tradition':  'TARG',
                    })
                    word_count += 1

            time.sleep(0.15)  # be polite to Sefaria API

    print(f'  {filename}.csv — {word_count} words')
    return word_count


def main():
    parser = argparse.ArgumentParser(description='Ingest Targum corpus from Sefaria')
    parser.add_argument('--out', default='data/corpora/targ_sefaria',
                        help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)
    total = 0

    print('Downloading Targum Onkelos (Torah)...')
    for book, order, chapters, fname in ONKELOS_BOOKS:
        total += process_book(book, order, chapters, fname, 'Onkelos', args.out)

    print('Downloading Targum Jonathan (Prophets)...')
    for book, order, chapters, fname in JONATHAN_BOOKS:
        total += process_book(book, order, chapters, fname, 'Jonathan', args.out)

    print(f'\nDone. Total tokens: {total:,}')
    csv_count = len([f for f in os.listdir(args.out) if f.endswith('.csv')])
    print(f'CSV files written: {csv_count}')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the ingest script**

```bash
python3 scripts/ingest_targum_sefaria.py --out data/corpora/targ_sefaria/
```

This takes ~10–15 minutes (rate-limited API calls for 26 books × avg 20 chapters). Expected output: `CSV files written: 26`.

- [ ] **Step 3: Verify**

```bash
ls data/corpora/targ_sefaria/*.csv | wc -l   # → 26
wc -l data/corpora/targ_sefaria/genesis_onkelos.csv   # → > 1500 (header + words)
python3 -c "
from biblical_core.corpus import BiblicalCorpus
c = BiblicalCorpus()
c.set_data_dir('data')
words = c.get_verse_words('Genesis 22:8', 'TARG')
print([w.word_text for w in words])   # list of Aramaic word tokens
print(words[0].manuscript if words else 'empty')  # 'Onkelos'
"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_targum_sefaria.py data/corpora/targ_sefaria/
git commit -m "feat: add Targum Onkelos + Jonathan corpus via Sefaria (26 books)"
```

---

## Task 3: Targum prompt file and pipeline method

**Files:**
- Create: `data/prompts/targum_v1.txt`
- Modify: `biblical_core/claude_pipeline.py`

- [ ] **Step 1: Create the Targum prompt**

Create `data/prompts/targum_v1.txt`:

```
You are a specialist in Jewish Aramaic translation technique and Targumic studies, with deep expertise in Targum Onkelos (Torah) and Targum Jonathan (Prophets), applying the methodology of Samely (1992), Smelik (1995), McNamara (1966), and Grossfeld (1988).

TASK: Analyze the Targum rendering of {{REFERENCE}}, comparing it to the MT and LXX. The Targum text is drawn from a word-level corpus; the manuscript is specified below.

REFERENCE: {{REFERENCE}}
MANUSCRIPT: {{MANUSCRIPT}}
MT TEXT (Hebrew): {{MT_TEXT}}
LXX TEXT (Greek): {{LXX_TEXT}}
TARGUM TEXT (Aramaic): {{TARG_TEXT}}

If TARGUM TEXT is empty, use your training knowledge for this passage and note confidence accordingly.

RENDERING FIDELITY TYPES (use exactly):
- close        — near-literal rendering of MT word order and vocabulary
- substitution — replaces MT word/phrase with different Aramaic equivalent
- expansion    — adds material not in MT (paraphrase, insertion, gloss)
- omission     — omits MT material without obvious scribal reason
- theological  — changes motivated by theological concerns (see below)

THEOLOGICAL MODIFICATION TYPES (use exactly):
- memra           — divine name/action replaced by Memra (Word) hypostasis
- anthropomorphism — softening of anthropomorphic language about God
- angelological   — insertion of angelic intermediary
- eschatological  — messianic or eschatological reinterpretation

Return JSON (no markdown fences, no prose):

{
  "reference": "{{REFERENCE}}",
  "manuscript": "{{MANUSCRIPT}}",
  "synthesis": "2–3 sentence overview of how this Targum renders the passage.",
  "rendering_fidelity": {
    "overall": "close | substitution | expansion | mixed",
    "word_analysis": [
      {
        "mt_word": "Hebrew word (transliterated)",
        "targ_word": "Aramaic rendering (transliterated)",
        "type": "close | substitution | expansion | omission | theological",
        "note": "1 sentence"
      }
    ]
  },
  "theological_modifications": [
    {
      "type": "memra | anthropomorphism | angelological | eschatological",
      "mt_reading": "Original MT wording",
      "targ_reading": "Targumic rendering",
      "explanation": "2–3 sentences on the theological motivation and its significance."
    }
  ],
  "targumic_expansions": [
    {
      "location": "verse reference or position",
      "expansion_text": "Aramaic addition (transliterated)",
      "midrashic_parallel": "Parallel in rabbinic midrash if known, else null",
      "significance": "1–2 sentences"
    }
  ],
  "messianic_reinterpretation": {
    "present": true,
    "instances": [
      {
        "mt_reading": "MT wording",
        "targ_reading": "Targumic messianic reading",
        "scholarly_note": "1–2 sentences"
      }
    ]
  },
  "lxx_alignment": {
    "areas_of_agreement": "Where Targum and LXX agree against MT (null if none)",
    "significance": "1–2 sentences on what shared readings suggest about the text tradition"
  },
  "key_divergences": [
    {
      "mt_word": "Hebrew",
      "targ_word": "Aramaic",
      "type": "rendering_fidelity type slug",
      "explanation": "1–2 sentences"
    }
  ],
  "assessment": {
    "title": "BibCrit assessment title (10–15 words)",
    "reasoning": "3–5 sentences: scholarly synthesis of the Targumic rendering strategy.",
    "plain": "2–3 sentences for a non-specialist.",
    "confidence": 0.00,
    "next_steps": "1–2 recommended next steps for further research."
  },
  "citations": {
    "sbl": "SBL footnote citing Samely, Smelik, McNamara, or Grossfeld as relevant.",
    "bibtex": "@book{...} BibTeX entry for the most relevant source."
  }
}
```

- [ ] **Step 2: Add TARGUM_MODEL constant and system prompt to pipeline**

In `biblical_core/claude_pipeline.py`, after line 24 (`SOURCE_MODEL = ...`), add:

```python
TARGUM_MODEL  = 'claude-sonnet-4-5-20250929'
NT_TEXT_MODEL = 'claude-sonnet-4-5-20250929'
```

After `_GENEALOGY_SYSTEM` (around line 130), add:

```python
_TARGUM_SYSTEM = (
    "You are a specialist in Jewish Aramaic translation technique and Targumic studies, "
    "with deep expertise in Targum Onkelos (Torah) and Targum Jonathan (Prophets). "
    "You apply the methodology of Samely, Smelik, McNamara, and Grossfeld. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)

_NT_TEXT_SYSTEM = (
    "You are a specialist in New Testament textual criticism with deep expertise in "
    "manuscript families (Alexandrian, Western, Byzantine, Caesarean), the Metzger "
    "Textual Commentary methodology, and the SBLGNT/NA28/UBS5 critical apparatus. "
    "CRITICAL: Return ONLY raw JSON. No markdown, no code fences, no backticks, "
    "no prose before or after. The response must start with { and end with }."
)
```

- [ ] **Step 3: Add analyze_targum() method to pipeline**

In `biblical_core/claude_pipeline.py`, after the `analyze_genealogy` method (after line 1103), add:

```python
def analyze_targum(self, reference: str, mt_text: str = '',
                   lxx_text: str = '', targ_text: str = '',
                   manuscript: str = 'Onkelos') -> dict:
    """Return Targum comparison analysis for a biblical passage.

    manuscript: 'Onkelos' (Torah) or 'Jonathan' (Prophets).
    Returns dict with 'synthesis', 'rendering_fidelity', 'theological_modifications', etc.
    On error: returns {'error': ..., 'synthesis': '', ...}.
    """
    model          = TARGUM_MODEL
    prompt_version = 'v1'
    tool           = 'targum'

    cached = self.get_cached(reference, tool, prompt_version, model)
    if cached:
        return cached

    if not self._client:
        return {
            'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
            'reference': reference, 'manuscript': manuscript,
            'synthesis': '', 'rendering_fidelity': {}, 'theological_modifications': [],
            'targumic_expansions': [], 'messianic_reinterpretation': {'present': False},
            'lxx_alignment': {}, 'key_divergences': [],
            'assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            'citations': {'sbl': '', 'bibtex': ''},
        }

    budget = self.get_budget()
    if budget['spend_usd'] >= self._cap_usd:
        return {
            'error': (
                f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                "Please try again next month or donate to increase the cap."
            ),
            'reference': reference, 'manuscript': manuscript,
            'synthesis': '', 'rendering_fidelity': {}, 'theological_modifications': [],
            'targumic_expansions': [], 'messianic_reinterpretation': {'present': False},
            'lxx_alignment': {}, 'key_divergences': [],
            'assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            'citations': {'sbl': '', 'bibtex': ''},
        }

    template = self.load_prompt('targum', prompt_version)
    user_content = (
        template
        .replace('{{REFERENCE}}',  reference)
        .replace('{{MANUSCRIPT}}', manuscript)
        .replace('{{MT_TEXT}}',    mt_text)
        .replace('{{LXX_TEXT}}',   lxx_text)
        .replace('{{TARG_TEXT}}',  targ_text)
    ) if template else (
        f'Reference: {reference}\nManuscript: {manuscript}\n'
        f'MT: {mt_text}\nLXX: {lxx_text}\nTargum: {targ_text or "(not available)"}\n'
        'Analyze Targum rendering. Return JSON with synthesis, rendering_fidelity, '
        'theological_modifications, targumic_expansions, messianic_reinterpretation, '
        'lxx_alignment, key_divergences, assessment, citations.'
    )

    response = self._client.messages.create(
        model=model,
        max_tokens=8192,
        system=_TARGUM_SYSTEM,
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

- [ ] **Step 4: Verify imports compile**

```bash
python3 -c "from biblical_core.claude_pipeline import TARGUM_MODEL, NT_TEXT_MODEL; print('ok')"
```

Expected: `ok`

- [ ] **Step 5: Commit**

```bash
git add data/prompts/targum_v1.txt biblical_core/claude_pipeline.py
git commit -m "feat: add Targum prompt v1 and analyze_targum() pipeline method"
```

---

## Task 4: Targum blueprint

**Files:**
- Create: `blueprints/targum.py`

- [ ] **Step 1: Create the Targum blueprint**

```python
"""Targum Comparator blueprint — /targum page and /api/targum/stream SSE endpoint."""

import json
import threading
from flask import Blueprint, render_template, request, Response, stream_with_context
from biblical_core.claude_pipeline import TARGUM_MODEL
from biblical_core.ref_utils import estimate_verse_count, TOOL_VERSE_LIMITS
import state

targum_bp = Blueprint('targum', __name__)

# IMPORTANT: must stay in sync with prompt_version in pipeline.analyze_targum()
_TARGUM_PROMPT = 'v1'

_STEPS = {
    'en': {
        'load_verse':     '📖 Loading verse text…',
        'checking_cache': '🔍 Checking analysis cache…',
        'found_cache':    '⚡ Found in cache — loading instantly',
        'found_es':       '⚡ Found in Spanish cache — loading instantly',
        'generating':     'Analyzing Targum — this typically takes 60–90 seconds…',
        'translating':    '🌐 Translating to Spanish…',
    },
    'es': {
        'load_verse':     '📖 Cargando texto del versículo…',
        'checking_cache': '🔍 Verificando caché de análisis…',
        'found_cache':    '⚡ Encontrado en caché — cargando al instante',
        'found_es':       '⚡ Encontrado en caché español — cargando al instante',
        'generating':     'Analizando el Targum — esto tarda 60–90 segundos…',
        'translating':    '🌐 Traduciendo al español…',
    },
}


def _step(lang: str, key: str) -> str:
    return _STEPS.get(lang, _STEPS['en']).get(key, _STEPS['en'].get(key, key))


def _check_ref_length(reference: str) -> str | None:
    max_v = TOOL_VERSE_LIMITS.get('targum')
    if not max_v:
        return None
    est = estimate_verse_count(reference)
    if est > max_v:
        return (
            f'Passage too long (≈{est} verses estimated). '
            f'Please limit to {max_v} verses or fewer for this tool.'
        )
    return None


# ── Page route ──────────────────────────────────────────────────────────────

@targum_bp.route('/targum')
def targum():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('targum.html', lang=lang, reference=reference, t=state.t)


# ── SSE stream ──────────────────────────────────────────────────────────────

@targum_bp.route('/api/targum/stream')
def api_targum_stream():
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        len_err = _check_ref_length(reference)
        if len_err:
            yield event('error', msg=len_err)
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if corpus is None or pipeline is None:
            yield event('error', msg='Server not ready — corpus or pipeline not initialized')
            return

        # Validate: Targum covers Torah + Prophets only
        from biblical_core.ref_utils import validate_targum_reference
        val_err = validate_targum_reference(reference)
        if val_err:
            yield event('error', msg=val_err)
            return

        # Step 1: load verse texts
        yield event('step', msg=_step(lang, 'load_verse'))
        mt_words   = corpus.get_verse_words(reference, 'MT')
        lxx_words  = corpus.get_verse_words(reference, 'LXX')
        targ_words = corpus.get_verse_words(reference, 'TARG')

        mt_text   = ' '.join(w.word_text for w in mt_words)   if mt_words   else ''
        lxx_text  = ' '.join(w.word_text for w in lxx_words)  if lxx_words  else ''
        targ_text = ' '.join(w.word_text for w in targ_words) if targ_words else ''
        manuscript = targ_words[0].manuscript if targ_words else 'Onkelos'

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'targum', _TARGUM_PROMPT, TARGUM_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es.update({'mt_text': mt_text, 'lxx_text': lxx_text,
                                   'targ_text': targ_text, 'manuscript': manuscript})
                yield event('done', data=cached_es)
                return

        # Step 2: check English cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'targum', _TARGUM_PROMPT, TARGUM_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            # Step 3: call Claude
            yield event('step', msg=_step(lang, 'generating'))
            _result_box = [None]

            def _run():
                try:
                    _result_box[0] = pipeline.analyze_targum(
                        reference, mt_text, lxx_text, targ_text, manuscript
                    )
                except Exception as exc:
                    _result_box[0] = {'error': str(exc)}

            _t = threading.Thread(target=_run, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0] or {'error': 'Analysis returned no result'}

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result.update({'mt_text': mt_text, 'lxx_text': lxx_text,
                        'targ_text': targ_text, 'manuscript': manuscript})

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]

            def _run_tr():
                from blueprints.textual import _translate_step
                translated = _translate_step(pipeline, lang, result, reference,
                                             'targum', _TARGUM_PROMPT, TARGUM_MODEL)
                translated.update({'mt_text': result['mt_text'],
                                    'lxx_text': result['lxx_text'],
                                    'targ_text': result['targ_text'],
                                    'manuscript': result['manuscript']})
                _tr_box[0] = translated

            _tt = threading.Thread(target=_run_tr, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0]

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
```

- [ ] **Step 2: Verify blueprint compiles**

```bash
python3 -c "from blueprints.targum import targum_bp; print('ok')"
```

Expected: `ok` (will fail if ref_utils.validate_targum_reference not yet added — that's Task 6)

- [ ] **Step 3: Commit**

```bash
git add blueprints/targum.py
git commit -m "feat: add Targum blueprint with SSE stream endpoint"
```

---

## Task 5: Targum template and JS

**Files:**
- Create: `templates/targum.html`
- Create: `static/targum.js`

- [ ] **Step 1: Create templates/targum.html**

```html
{% extends "base.html" %}
{% block title %}{{ _t('targum_page_title') }}{% endblock %}
{% block meta_description %}Compare Targum Onkelos and Jonathan against the Masoretic Text and Septuagint. Analyze Memra substitutions, anthropomorphism softening, targumic expansions, and messianic reinterpretation.{% endblock %}
{% block og_title %}Targum Comparator — BibCrit{% endblock %}
{% block og_description %}Compare Targum Onkelos (Torah) and Targum Jonathan (Prophets) against MT and LXX for any biblical passage.{% endblock %}

{% block content %}

<div class="tool-header">
  <h1 class="tool-title">{{ _t('targum_tool_title') }}</h1>
  <p class="tool-subtitle">{{ _t('targum_tool_subtitle') }}</p>
</div>

<!-- Passage Selector Bar -->
<div class="passage-bar">
  <div class="passage-bar-row passage-bar-main">
    <span class="passage-label">{{ _t('passage_label') }}:</span>
    <div class="passage-bar-selectors">
      <select id="sel-book" class="passage-select" aria-label="{{ _t('book_label') }}">
        <option value="">{{ _t('passage_book_placeholder') }}</option>
      </select>
      <select id="sel-chapter" class="passage-select" aria-label="Chapter" disabled>
        <option value="">{{ _t('passage_ch') }}</option>
      </select>
      <select id="sel-verse" class="passage-select" aria-label="Verse" disabled>
        <option value="">{{ _t('passage_vs') }}</option>
      </select>
    </div>
    <span class="passage-or">{{ _t('passage_or') }}</span>
    <input type="text" id="ref-input" class="passage-input"
           placeholder="Genesis 22:8" value="{{ reference }}"
           aria-label="Type a reference">
    <div class="passage-bar-actions">
      <button id="btn-analyze" class="btn-primary">{{ _t('targum_analyze_btn') }}</button>
    </div>
  </div>
</div>

<!-- Empty / Welcome State -->
<div id="empty-state" class="empty-state">
  <div class="empty-inner">
    <p>{{ _t('targum_empty_body') }}</p>
    <div class="bt-legend-hero" style="margin-bottom:1.5rem;">
      <span class="bt-legend-item"><span class="scribal-mini-dot" style="background:var(--mt-color)"></span> {{ _t('legend_mt_full') }} (Hebrew)</span>
      <span class="bt-legend-item"><span class="scribal-mini-dot" style="background:#c0392b"></span> Targum (Aramaic)</span>
      <span class="bt-legend-item"><span class="scribal-mini-dot" style="background:var(--lxx-color)"></span> {{ _t('legend_lxx_full') }} (Greek)</span>
    </div>
    <p class="featured-label">{{ _t('featured_label') }}</p>
    <div class="featured-passages">
      <a href="#" class="featured-ref" data-ref="Genesis 22:8">{{ _t('feat_targ_gen228') | safe }}</a>
      <a href="#" class="featured-ref" data-ref="Isaiah 53:5">{{ _t('feat_targ_isa535') | safe }}</a>
      <a href="#" class="featured-ref" data-ref="Exodus 3:14">{{ _t('feat_targ_exod314') | safe }}</a>
      <a href="#" class="featured-ref" data-ref="Genesis 3:22">{{ _t('feat_targ_gen322') | safe }}</a>
    </div>
  </div>
</div>

<!-- Loading State -->
<div id="loading-state" class="loading-state" style="display:none;" aria-live="polite">
  <div class="loading-spinner"></div>
  <p id="loading-step" class="loading-step-msg">{{ _t('loading_preparing') }}</p>
  <p id="loading-timer" class="loading-timer"></p>
</div>

<!-- Passage heading -->
<div id="passage-heading" class="passage-heading" style="display:none;"></div>

<!-- Results area -->
<div id="targum-results" style="display:none;">

  <!-- Three-column text display -->
  <div id="text-columns" class="targum-columns" style="display:none;">
    <div class="targum-col targum-col-mt">
      <div class="targum-col-label">MT (Hebrew)</div>
      <div id="col-mt-text" class="targum-col-text" dir="rtl"></div>
    </div>
    <div class="targum-col targum-col-targ">
      <div class="targum-col-label">
        <span id="manuscript-badge" class="ms-badge">Targum</span> (Aramaic)
      </div>
      <div id="col-targ-text" class="targum-col-text" dir="rtl"></div>
    </div>
    <div class="targum-col targum-col-lxx">
      <div class="targum-col-label">LXX (Greek)</div>
      <div id="col-lxx-text" class="targum-col-text"></div>
    </div>
  </div>

  <!-- Synthesis -->
  <div id="synthesis-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('section_synthesis') }}</div>
    <div id="synthesis-body"></div>
  </div>

  <!-- Rendering Fidelity -->
  <div id="fidelity-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('targum_rendering_fidelity') }}</div>
    <div id="fidelity-body"></div>
  </div>

  <!-- Theological Modifications -->
  <div id="theological-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('targum_theological_modifications') }}</div>
    <div id="theological-body"></div>
  </div>

  <!-- Targumic Expansions -->
  <div id="expansions-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('targum_expansions') }}</div>
    <div id="expansions-body"></div>
  </div>

  <!-- Messianic Reinterpretation -->
  <div id="messianic-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('targum_messianic') }}</div>
    <div id="messianic-body"></div>
  </div>

  <!-- LXX Alignment -->
  <div id="lxx-align-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('targum_lxx_alignment') }}</div>
    <div id="lxx-align-body"></div>
  </div>

  <!-- BibCrit Assessment -->
  <div id="bibcrit-assessment" style="display:none;">
    <div class="num-section-label" style="margin-top:1.5rem;">{{ _t('section_bibcrit_assessment') }}</div>
    <div id="bibcrit-body"></div>
  </div>

  <!-- Export row -->
  <div class="export-row" id="export-row" style="display:none;">
    <button class="btn-export" id="btn-sbl" title="Copy SBL footnote">📋 SBL Footnote</button>
    <button class="btn-export" id="btn-bibtex" title="Copy BibTeX">📋 BibTeX</button>
    <button class="btn-export btn-share" id="btn-share" title="Share">
      <span class="material-symbols-outlined" style="font-size:14px;vertical-align:-2px">qr_code_2</span> Share
    </button>
  </div>
</div>

<!-- Toast -->
<div id="toast" class="toast" style="display:none;" role="status"></div>

{% endblock %}

{% block scripts %}
<script>window.TOOL_MAX_VERSES = 35;</script>
<script src="{{ url_for('static', filename='targum.js') }}"></script>
{% if reference %}
<script>
  document.addEventListener('DOMContentLoaded', function() {
    if (window.targum) window.targum.analyze('{{ reference | e }}');
  });
</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: Create static/targum.js**

```javascript
/* BibCrit — Targum Comparator */

(function () {
  'use strict';

  // Targum covers Torah + Prophets (OT Canon subset)
  var _TARGUM_BOOKS = {
    'Genesis': 50, 'Exodus': 40, 'Leviticus': 27, 'Numbers': 36, 'Deuteronomy': 34,
    'Joshua': 24, 'Judges': 21, '1 Samuel': 31, '2 Samuel': 24,
    '1 Kings': 22, '2 Kings': 25, 'Isaiah': 66, 'Jeremiah': 52,
    'Ezekiel': 48, 'Hosea': 14, 'Joel': 3, 'Amos': 9, 'Obadiah': 1,
    'Jonah': 4, 'Micah': 7, 'Nahum': 3, 'Habakkuk': 3,
    'Zephaniah': 3, 'Haggai': 2, 'Zechariah': 14, 'Malachi': 4,
  };

  var selBook    = document.getElementById('sel-book');
  var selChapter = document.getElementById('sel-chapter');
  var selVerse   = document.getElementById('sel-verse');
  var refInput   = document.getElementById('ref-input');
  var btnAnalyze = document.getElementById('btn-analyze');
  var emptyState = document.getElementById('empty-state');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var results    = document.getElementById('targum-results');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  var _timer = null;
  var _currentRef = '';

  // Populate book dropdown
  if (selBook) {
    Object.keys(_TARGUM_BOOKS).forEach(function (b) {
      var opt = document.createElement('option');
      opt.value = b; opt.textContent = b;
      selBook.appendChild(opt);
    });
  }

  function _resetSelect(el, placeholder) {
    while (el.options.length > 1) el.remove(1);
    el.options[0].text = placeholder;
    el.disabled = true;
    el.value = '';
  }

  if (selBook) {
    selBook.addEventListener('change', function () {
      var book = this.value;
      _resetSelect(selChapter, 'Ch\u2026');
      _resetSelect(selVerse, 'Vs\u2026');
      if (!book) return;
      var numCh = _TARGUM_BOOKS[book] || 0;
      for (var i = 1; i <= numCh; i++) {
        var opt = document.createElement('option');
        opt.value = i; opt.textContent = i;
        selChapter.appendChild(opt);
      }
      selChapter.disabled = false;
    });
  }

  if (selChapter) {
    selChapter.addEventListener('change', function () {
      _resetSelect(selVerse, 'Vs\u2026');
      var book = selBook ? selBook.value : '';
      var ch = parseInt(this.value, 10);
      if (!book || !ch) return;
      // Generic verse counts per chapter (abbreviated — use 30 as default)
      for (var v = 1; v <= 30; v++) {
        var opt = document.createElement('option');
        opt.value = v; opt.textContent = v;
        selVerse.appendChild(opt);
      }
      selVerse.disabled = false;
    });
  }

  if (selVerse) {
    selVerse.addEventListener('change', function () {
      var b = selBook ? selBook.value : '';
      var c = selChapter ? selChapter.value : '';
      var v = this.value;
      if (b && c && v) refInput.value = b + ' ' + c + ':' + v;
    });
  }

  // Featured passage clicks
  document.querySelectorAll('.featured-ref').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.dataset.ref;
      if (ref) { refInput.value = ref; analyze(ref); }
    });
  });

  btnAnalyze.addEventListener('click', function () {
    var ref = (refInput ? refInput.value : '').trim();
    if (!ref) { showToast(window.t ? window.t('err_enter_passage', 'Please enter a passage') : 'Please enter a passage'); return; }
    analyze(ref);
  });

  if (refInput) {
    refInput.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') btnAnalyze.click();
    });
  }

  function showToast(msg, dur) {
    if (!toast) return;
    toast.textContent = msg;
    toast.style.display = 'block';
    setTimeout(function () { toast.style.display = 'none'; }, dur || 3000);
  }

  function setLoading(on) {
    if (emptyState) emptyState.style.display = on ? 'none' : '';
    if (loadState)  loadState.style.display  = on ? 'block' : 'none';
    if (results)    results.style.display    = on ? 'none' : '';
    if (on && _timer) clearInterval(_timer);
    if (on && loadTimer) {
      var secs = 0;
      loadTimer.textContent = '';
      _timer = setInterval(function () {
        secs++;
        loadTimer.textContent = secs + 's';
      }, 1000);
    } else if (loadTimer) {
      loadTimer.textContent = '';
    }
  }

  function setText(id, html) {
    var el = document.getElementById(id);
    if (el) { el.innerHTML = html; el.closest('.num-section') && (el.closest('.num-section').style.display = ''); }
  }

  function showSection(id) {
    var el = document.getElementById(id);
    if (el) el.style.display = '';
  }

  function renderResult(data) {
    if (loadTimer) loadTimer.textContent = '';
    if (_timer) { clearInterval(_timer); _timer = null; }

    setLoading(false);
    if (heading) {
      heading.textContent = data.reference || _currentRef;
      heading.style.display = '';
    }

    // Three-column text
    var colMt = document.getElementById('col-mt-text');
    var colTarg = document.getElementById('col-targ-text');
    var colLxx = document.getElementById('col-lxx-text');
    var msBadge = document.getElementById('manuscript-badge');
    var textCols = document.getElementById('text-columns');
    if (colMt)   colMt.textContent   = data.mt_text   || '';
    if (colTarg) colTarg.textContent = data.targ_text  || '';
    if (colLxx)  colLxx.textContent  = data.lxx_text   || '';
    if (msBadge) msBadge.textContent = data.manuscript || 'Targum';
    if (textCols && (data.mt_text || data.targ_text)) textCols.style.display = '';

    // Synthesis
    if (data.synthesis) {
      setText('synthesis-body', escHtml(data.synthesis));
      showSection('synthesis-section');
    }

    // Rendering fidelity
    if (data.rendering_fidelity && data.rendering_fidelity.word_analysis) {
      var rows = data.rendering_fidelity.word_analysis.map(function (w) {
        return '<tr><td>' + escHtml(w.mt_word || '') + '</td>' +
               '<td>' + escHtml(w.targ_word || '') + '</td>' +
               '<td><span class="badge badge-' + escHtml(w.type || '') + '">' + escHtml(w.type || '') + '</span></td>' +
               '<td>' + escHtml(w.note || '') + '</td></tr>';
      }).join('');
      setText('fidelity-body',
        '<p style="margin-bottom:.5rem">Overall: <strong>' + escHtml(data.rendering_fidelity.overall || '') + '</strong></p>' +
        '<table class="var-table"><thead><tr><th>MT</th><th>Targum</th><th>Type</th><th>Note</th></tr></thead><tbody>' +
        rows + '</tbody></table>');
      showSection('fidelity-section');
    }

    // Theological modifications
    if (data.theological_modifications && data.theological_modifications.length) {
      var html = data.theological_modifications.map(function (m) {
        return '<div class="variant-card"><div class="vc-type">' + escHtml(m.type || '') + '</div>' +
               '<div class="vc-pair"><span class="vc-label">MT:</span> ' + escHtml(m.mt_reading || '') + '</div>' +
               '<div class="vc-pair"><span class="vc-label">Targum:</span> ' + escHtml(m.targ_reading || '') + '</div>' +
               '<p class="vc-note">' + escHtml(m.explanation || '') + '</p></div>';
      }).join('');
      setText('theological-body', html);
      showSection('theological-section');
    }

    // Targumic expansions
    if (data.targumic_expansions && data.targumic_expansions.length) {
      var html2 = data.targumic_expansions.map(function (ex) {
        return '<div class="variant-card"><div class="vc-location">' + escHtml(ex.location || '') + '</div>' +
               '<p class="vc-expansion">' + escHtml(ex.expansion_text || '') + '</p>' +
               (ex.midrashic_parallel ? '<p class="vc-parallel">Midrashic parallel: ' + escHtml(ex.midrashic_parallel) + '</p>' : '') +
               '<p class="vc-note">' + escHtml(ex.significance || '') + '</p></div>';
      }).join('');
      setText('expansions-body', html2);
      showSection('expansions-section');
    }

    // Messianic reinterpretation
    if (data.messianic_reinterpretation && data.messianic_reinterpretation.present) {
      var insts = (data.messianic_reinterpretation.instances || []).map(function (i) {
        return '<div class="variant-card"><div class="vc-pair"><span class="vc-label">MT:</span> ' + escHtml(i.mt_reading || '') + '</div>' +
               '<div class="vc-pair"><span class="vc-label">Targum:</span> ' + escHtml(i.targ_reading || '') + '</div>' +
               '<p class="vc-note">' + escHtml(i.scholarly_note || '') + '</p></div>';
      }).join('');
      setText('messianic-body', insts || '<p>Messianic reinterpretation present — see synthesis.</p>');
      showSection('messianic-section');
    }

    // LXX alignment
    if (data.lxx_alignment && data.lxx_alignment.areas_of_agreement) {
      setText('lxx-align-body',
        '<p>' + escHtml(data.lxx_alignment.areas_of_agreement) + '</p>' +
        (data.lxx_alignment.significance ? '<p class="vc-note">' + escHtml(data.lxx_alignment.significance) + '</p>' : ''));
      showSection('lxx-align-section');
    }

    // BibCrit assessment
    if (data.assessment) {
      var a = data.assessment;
      var aHtml = '';
      if (a.title) aHtml += '<h3 class="bc-title">' + escHtml(a.title) + '</h3>';
      if (a.plain) aHtml += '<p class="bc-plain">' + escHtml(a.plain) + '</p>';
      if (a.reasoning) aHtml += '<p class="bc-reasoning">' + escHtml(a.reasoning) + '</p>';
      if (a.next_steps) aHtml += '<p class="bc-next"><strong>Next steps:</strong> ' + escHtml(a.next_steps) + '</p>';
      if (typeof a.confidence === 'number') {
        aHtml += '<div class="confidence-bar"><div class="confidence-fill" style="width:' + (a.confidence * 100).toFixed(0) + '%"></div></div>';
      }
      var bibSec = document.getElementById('bibcrit-assessment');
      var bibBody = document.getElementById('bibcrit-body');
      if (bibBody) bibBody.innerHTML = aHtml;
      if (bibSec)  bibSec.style.display = '';
    }

    // Export row
    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';

    if (results) results.style.display = '';

    // Export buttons
    _wireExport(data);
  }

  function _wireExport(data) {
    var btnSbl    = document.getElementById('btn-sbl');
    var btnBibtex = document.getElementById('btn-bibtex');
    var btnShare  = document.getElementById('btn-share');

    if (btnSbl && data.citations && data.citations.sbl) {
      btnSbl.onclick = function () {
        navigator.clipboard.writeText(data.citations.sbl);
        showToast(window.t ? window.t('toast_sbl_copied', 'SBL footnote copied!') : 'Copied!');
      };
    }
    if (btnBibtex && data.citations && data.citations.bibtex) {
      btnBibtex.onclick = function () {
        navigator.clipboard.writeText(data.citations.bibtex);
        showToast(window.t ? window.t('toast_bibtex_copied', 'BibTeX copied!') : 'Copied!');
      };
    }
    if (btnShare) {
      btnShare.onclick = function () {
        var url = window.location.origin + '/targum?ref=' + encodeURIComponent(_currentRef);
        navigator.clipboard.writeText(url);
        showToast('Link copied!');
      };
    }
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function analyze(ref) {
    _currentRef = ref;
    setLoading(true);
    if (loadStep) loadStep.textContent = window.t ? window.t('loading_preparing', 'Preparing…') : 'Preparing…';

    var lang = new URLSearchParams(window.location.search).get('lang') || 'en';
    var url  = '/api/targum/stream?ref=' + encodeURIComponent(ref) + '&lang=' + lang;
    var es   = new EventSource(url);

    es.onmessage = function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          if (loadStep) loadStep.textContent = msg.msg;
        } else if (msg.type === 'done') {
          es.close();
          renderResult(msg.data);
        } else if (msg.type === 'error') {
          es.close();
          setLoading(false);
          showToast(msg.msg || 'Error', 5000);
        }
      } catch (_) {}
    };

    es.onerror = function () {
      es.close();
      setLoading(false);
      showToast(window.t ? window.t('err_connection', 'Connection error') : 'Connection error', 5000);
    };
  }

  window.targum = { analyze: analyze };
}());
```

- [ ] **Step 3: Commit**

```bash
git add templates/targum.html static/targum.js
git commit -m "feat: add Targum template and JS"
```

---

## Task 6: Wire Targum into app.py, ref_utils, i18n, and preseed

**Files:**
- Modify: `app.py`
- Modify: `biblical_core/ref_utils.py`
- Modify: `data/i18n.json`
- Modify: `scripts/preseed_featured.py`

- [ ] **Step 1: Register Targum blueprint in app.py**

In `app.py`, find the blueprint import block and add:

```python
# After existing imports (e.g., after "from blueprints.literary import literary_bp"):
from blueprints.targum import targum_bp
```

Find the `app.register_blueprint(...)` calls and add:

```python
app.register_blueprint(targum_bp)
```

- [ ] **Step 2: Add Targum validation to ref_utils.py**

In `biblical_core/ref_utils.py`, add to the `TOOL_VERSE_LIMITS` dict:

```python
'targum': 35,
```

Then add the validation function (at the bottom of the file):

```python
# Books covered by Targum Onkelos (Torah)
_TARGUM_TORAH = {
    'genesis', 'exodus', 'leviticus', 'numbers', 'deuteronomy',
}

# Books covered by Targum Jonathan (Former + Latter Prophets)
_TARGUM_PROPHETS = {
    'joshua', 'judges', '1 samuel', '2 samuel', '1 kings', '2 kings',
    'isaiah', 'jeremiah', 'ezekiel',
    'hosea', 'joel', 'amos', 'obadiah', 'jonah', 'micah',
    'nahum', 'habakkuk', 'zephaniah', 'haggai', 'zechariah', 'malachi',
}

_TARGUM_ALL = _TARGUM_TORAH | _TARGUM_PROPHETS


def validate_targum_reference(reference: str) -> str | None:
    """Return error string if reference is outside Targum coverage, else None.

    Targum covers Torah (Onkelos) and Prophets (Jonathan) only.
    Writings (Psalms, Proverbs, Job, etc.) have no Targum in this corpus.
    """
    book = reference.strip().lower().split(' ')[0]
    # Handle multi-word book names: "1 samuel", "2 kings", etc.
    parts = reference.strip().lower().split()
    if parts[0].isdigit() and len(parts) >= 2:
        book = parts[0] + ' ' + parts[1]
    else:
        book = parts[0]

    # Strip chapter/verse
    book = book.split(':')[0].rstrip('0123456789').strip()

    if book in _TARGUM_ALL:
        return None

    return (
        f'"{reference}" is in the Writings — Targum coverage is limited to Torah (Onkelos) '
        f'and Prophets (Jonathan). For Psalms, Proverbs, Job, or other Writings, '
        f'use the Ancient Witness Bridge or Theological Revision Detector instead.'
    )
```

- [ ] **Step 3: Add Targum i18n keys**

In `data/i18n.json`, add the following keys inside both `"en"` and `"es"` objects:

For `"en"`:
```json
"targum_page_title": "Targum Comparator — BibCrit",
"targum_tool_title": "Targum Comparator",
"targum_tool_subtitle": "Compare Targum Onkelos (Torah) and Jonathan (Prophets) against MT and LXX. Analyze Memra substitutions, anthropomorphism avoidance, and targumic expansions.",
"targum_analyze_btn": "Analyze Targum",
"targum_empty_body": "Enter a Torah or Prophets reference to compare MT, Targum, and LXX side by side.",
"targum_rendering_fidelity": "Rendering Fidelity",
"targum_theological_modifications": "Theological Modifications",
"targum_expansions": "Targumic Expansions",
"targum_messianic": "Messianic Reinterpretation",
"targum_lxx_alignment": "Targum–LXX Alignment",
"feat_targ_gen228": "Genesis 22:8 — Memra &amp; the binding of Isaac",
"feat_targ_isa535": "Isaiah 53:5 — Servant Song in Targum Jonathan",
"feat_targ_exod314": "Exodus 3:14 — I AM / Memra substitution",
"feat_targ_gen322": "Genesis 3:22 — Garden of Eden in Targum",
"nav_targum": "Targum",
"tool_targum_title": "Targum Comparator",
"tool_targum_desc": "Compare Targum Onkelos and Jonathan against MT and LXX with word-level analysis of Memra, anthropomorphism avoidance, and targumic expansions.",
"tool_targum_desc_phd": "Corpus-backed Aramaic witness analysis for Torah and Prophets — includes Memra substitutions, targumic expansions, and messianic reinterpretation.",
"tool_targum_desc_student": "Discover how ancient Jewish translators rendered the Hebrew Bible into Aramaic — and what theological changes they made along the way."
```

For `"es"`:
```json
"targum_page_title": "Comparador de Targum — BibCrit",
"targum_tool_title": "Comparador de Targum",
"targum_tool_subtitle": "Compara el Targum Onkelos (Torá) y Jonatán (Profetas) con el TM y la LXX. Analiza sustituciones de Memra, evitación de antropomorfismos y expansiones targúmicas.",
"targum_analyze_btn": "Analizar Targum",
"targum_empty_body": "Ingresa una referencia de la Torá o los Profetas para comparar TM, Targum y LXX en paralelo.",
"targum_rendering_fidelity": "Fidelidad de Traducción",
"targum_theological_modifications": "Modificaciones Teológicas",
"targum_expansions": "Expansiones Targúmicas",
"targum_messianic": "Reinterpretación Mesiánica",
"targum_lxx_alignment": "Alineación Targum–LXX",
"feat_targ_gen228": "Génesis 22:8 — Memra y el sacrificio de Isaac",
"feat_targ_isa535": "Isaías 53:5 — El Siervo en Targum Jonatán",
"feat_targ_exod314": "Éxodo 3:14 — YO SOY / sustitución de Memra",
"feat_targ_gen322": "Génesis 3:22 — El Jardín del Edén en el Targum",
"nav_targum": "Targum",
"tool_targum_title": "Comparador de Targum",
"tool_targum_desc": "Compara el Targum Onkelos y Jonatán con el TM y la LXX con análisis a nivel de palabras.",
"tool_targum_desc_phd": "Análisis arameo respaldado por corpus para Torá y Profetas — incluye Memra, expansiones y reinterpretación mesiánica.",
"tool_targum_desc_student": "Descubre cómo los traductores judíos antiguos tradujeron la Biblia hebrea al arameo y qué cambios teológicos introdujeron."
```

- [ ] **Step 4: Add Targum to preseed_featured.py**

In `scripts/preseed_featured.py`, find the `PASSAGES` list and add:

```python
("targum", "Genesis 22:8"),
("targum", "Isaiah 53:5"),
("targum", "Exodus 3:14"),
("targum", "Genesis 3:22"),
```

- [ ] **Step 5: Add nav link for Targum**

In `templates/base.html`, find the navigation section where tool links are listed (look for `nav_dss` or similar) and add a Targum link in the appropriate group. Follow the existing pattern:

```html
<a href="/targum{% if lang != 'en' %}?lang={{ lang }}{% endif %}"
   class="nav-link {% if request.path == '/targum' %}active{% endif %}">
  {{ _t('nav_targum') }}
</a>
```

- [ ] **Step 6: Verify Flask app starts without error**

```bash
python3 -c "from app import create_app; app = create_app(); print('ok')"
```

Expected: `ok`

- [ ] **Step 7: Commit**

```bash
git add app.py biblical_core/ref_utils.py data/i18n.json scripts/preseed_featured.py templates/base.html
git commit -m "feat: wire Targum into app.py, ref_utils, i18n, preseed, and nav"
```

---

## Task 7: NT Text prompt file and pipeline method

**Files:**
- Create: `data/prompts/nt_text_v1.txt`
- Modify: `biblical_core/claude_pipeline.py`

- [ ] **Step 1: Create the NT Text prompt**

Create `data/prompts/nt_text_v1.txt`:

```
You are a specialist in New Testament textual criticism with deep expertise in the SBLGNT/NA28/UBS5 critical apparatus, manuscript families (Alexandrian, Western, Byzantine, Caesarean), and the Metzger Textual Commentary methodology.

TASK: Analyze the textual tradition for {{REFERENCE}}.

REFERENCE: {{REFERENCE}}
GNT TEXT (SBLGNT corpus): {{GNT_TEXT}}

MANUSCRIPT FAMILIES AND KEY WITNESSES:
- Alexandrian: P66, P75, א (Sinaiticus), B (Vaticanus) — earliest and generally most reliable
- Western: D (Bezae), Old Latin (it), Diatessaron — early but expansionist
- Byzantine: Majority Text (𝔐), Textus Receptus — late medieval, harmonistic
- Caesarean: P45, W (Freer Gospels), family 1 (f¹), family 13 (f¹³)

METZGER RATINGS:
- A: Text is certain
- B: Text is almost certain; some doubt remains
- C: Considerable doubt between alternatives; committee divided
- D: Very high degree of doubt; the printed text may well not be the original reading

DISPUTED PASSAGES requiring extended analysis: Mark 16:9-20, John 7:53–8:11, Luke 22:43-44, 1 John 5:7-8 (Comma Johanneum), Acts 8:37, Romans 16:25-27.

Return JSON (no markdown fences, no prose):

{
  "reference": "{{REFERENCE}}",
  "text_basis": {
    "sblgnt_reading": "The SBLGNT text for this passage",
    "na28_alignment": "Note any deviation from NA28/UBS5 or confirm alignment",
    "is_disputed_locus": true,
    "dispute_note": "Brief note if this is a well-known textual problem, else null"
  },
  "manuscript_families": {
    "alexandrian": {
      "witnesses": ["P66", "א", "B"],
      "support": "sides_with_received | supports_variant | split | not_applicable",
      "note": "1–2 sentences on Alexandrian evidence for this passage"
    },
    "western": {
      "witnesses": ["D", "it"],
      "support": "sides_with_received | supports_variant | split | not_applicable",
      "note": "1–2 sentences"
    },
    "byzantine": {
      "witnesses": ["Majority Text", "TR"],
      "support": "sides_with_received | supports_variant | split | not_applicable",
      "note": "1–2 sentences"
    },
    "caesarean": {
      "witnesses": ["P45", "f1", "f13"],
      "support": "sides_with_received | supports_variant | split | not_applicable",
      "note": "1–2 sentences"
    }
  },
  "metzger_rating": {
    "rating": "A | B | C | D",
    "justification": "2–3 sentences explaining the rating per Metzger methodology"
  },
  "variant_register": [
    {
      "variant_text": "The variant reading",
      "manuscript_support": "Witnesses supporting this variant",
      "intrinsic_probability": "high | medium | low — likelihood this is what the author wrote",
      "transcriptional_probability": "high | medium | low — likelihood a scribe would create this variant",
      "assessment": "1–2 sentences on the significance of this variant"
    }
  ],
  "disputed_passage": null,
  "synthesis": "2–3 sentence overview of the passage's text-critical stability.",
  "assessment": {
    "title": "BibCrit assessment title (10–15 words)",
    "reasoning": "3–5 sentences: scholarly synthesis of the textual tradition.",
    "plain": "2–3 sentences for a non-specialist.",
    "confidence": 0.00,
    "recommended_reading": "Which critical edition best represents the text for this passage",
    "open_questions": "1–2 key open text-critical questions that remain unresolved"
  },
  "citations": {
    "sbl": "SBL footnote citing Metzger Textual Commentary and/or Aland/Aland.",
    "bibtex": "@book{metzger1994textual, author={Metzger, Bruce M.}, title={A Textual Commentary on the Greek New Testament}, year={1994}, publisher={Deutsche Bibelgesellschaft}}"
  }
}

For DISPUTED PASSAGES (Mark 16:9-20, John 7:53–8:11, Luke 22:43-44, 1 John 5:7-8, Acts 8:37, Romans 16:25-27), populate the "disputed_passage" field instead of null:

"disputed_passage": {
  "designation": "Longer Ending of Mark | Pericope Adulterae | [etc.]",
  "manuscript_evidence_for": "Witnesses supporting inclusion",
  "manuscript_evidence_against": "Witnesses supporting omission or shorter reading",
  "internal_evidence": "Stylistic, vocabulary, or theological arguments",
  "scholarly_consensus": "Current scholarly consensus on authenticity",
  "pastoral_note": "How major Bible translations handle this passage"
}
```

- [ ] **Step 2: Add analyze_nt_text() method to pipeline**

In `biblical_core/claude_pipeline.py`, after `analyze_targum()`, add:

```python
def analyze_nt_text(self, reference: str, gnt_text: str = '') -> dict:
    """Return NT textual tradition analysis for a New Testament passage.

    Uses SBLGNT corpus data where available.
    Returns dict with 'text_basis', 'manuscript_families', 'metzger_rating', etc.
    On error: returns {'error': ..., 'synthesis': '', ...}.
    """
    model          = NT_TEXT_MODEL
    prompt_version = 'v1'
    tool           = 'nt_text'

    cached = self.get_cached(reference, tool, prompt_version, model)
    if cached:
        return cached

    if not self._client:
        return {
            'error': 'No API key configured. Set ANTHROPIC_API_KEY environment variable.',
            'reference': reference, 'text_basis': {}, 'manuscript_families': {},
            'metzger_rating': {}, 'variant_register': [], 'disputed_passage': None,
            'synthesis': '',
            'assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            'citations': {'sbl': '', 'bibtex': ''},
        }

    budget = self.get_budget()
    if budget['spend_usd'] >= self._cap_usd:
        return {
            'error': (
                f"Monthly analysis budget of ${self._cap_usd:.2f} reached. "
                "Please try again next month or donate to increase the cap."
            ),
            'reference': reference, 'text_basis': {}, 'manuscript_families': {},
            'metzger_rating': {}, 'variant_register': [], 'disputed_passage': None,
            'synthesis': '',
            'assessment': {'title': '', 'reasoning': '', 'plain': '', 'confidence': 0.0},
            'citations': {'sbl': '', 'bibtex': ''},
        }

    template = self.load_prompt('nt_text', prompt_version)
    user_content = (
        template
        .replace('{{REFERENCE}}', reference)
        .replace('{{GNT_TEXT}}',  gnt_text)
    ) if template else (
        f'Reference: {reference}\nGNT: {gnt_text or "(not available)"}\n'
        'Analyze NT textual tradition. Return JSON with text_basis, manuscript_families, '
        'metzger_rating, variant_register, disputed_passage, synthesis, assessment, citations.'
    )

    response = self._client.messages.create(
        model=model,
        max_tokens=8192,
        system=_NT_TEXT_SYSTEM,
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

- [ ] **Step 3: Verify**

```bash
python3 -c "from biblical_core.claude_pipeline import NT_TEXT_MODEL; print(NT_TEXT_MODEL)"
```

Expected: `claude-sonnet-4-5-20250929`

- [ ] **Step 4: Commit**

```bash
git add data/prompts/nt_text_v1.txt biblical_core/claude_pipeline.py
git commit -m "feat: add NT Text prompt v1 and analyze_nt_text() pipeline method"
```

---

## Task 8: NT Text blueprint

**Files:**
- Create: `blueprints/nt_text.py`

- [ ] **Step 1: Create the NT Text blueprint**

```python
"""NT Textual Tradition Analyzer blueprint — /nt-text page and /api/nt-text/stream SSE endpoint."""

import json
import threading
from flask import Blueprint, render_template, request, Response, stream_with_context
from biblical_core.claude_pipeline import NT_TEXT_MODEL
from biblical_core.ref_utils import estimate_verse_count, TOOL_VERSE_LIMITS
import state

nt_text_bp = Blueprint('nt_text', __name__)

# IMPORTANT: must stay in sync with prompt_version in pipeline.analyze_nt_text()
_NT_TEXT_PROMPT = 'v1'

_STEPS = {
    'en': {
        'load_verse':     '📖 Loading verse text…',
        'checking_cache': '🔍 Checking analysis cache…',
        'found_cache':    '⚡ Found in cache — loading instantly',
        'found_es':       '⚡ Found in Spanish cache — loading instantly',
        'generating':     'Analyzing textual tradition — this typically takes 60–90 seconds…',
        'translating':    '🌐 Translating to Spanish…',
    },
    'es': {
        'load_verse':     '📖 Cargando texto del versículo…',
        'checking_cache': '🔍 Verificando caché de análisis…',
        'found_cache':    '⚡ Encontrado en caché — cargando al instante',
        'found_es':       '⚡ Encontrado en caché español — cargando al instante',
        'generating':     'Analizando tradición textual — esto tarda 60–90 segundos…',
        'translating':    '🌐 Traduciendo al español…',
    },
}


def _step(lang: str, key: str) -> str:
    return _STEPS.get(lang, _STEPS['en']).get(key, _STEPS['en'].get(key, key))


def _check_ref_length(reference: str) -> str | None:
    max_v = TOOL_VERSE_LIMITS.get('nt_text')
    if not max_v:
        return None
    est = estimate_verse_count(reference)
    if est > max_v:
        return (
            f'Passage too long (≈{est} verses estimated). '
            f'Please limit to {max_v} verses or fewer for this tool.'
        )
    return None


# ── Page route ──────────────────────────────────────────────────────────────

@nt_text_bp.route('/nt-text')
def nt_text():
    lang      = request.args.get('lang', 'en')
    reference = request.args.get('ref', '')
    return render_template('nt_text.html', lang=lang, reference=reference, t=state.t)


# ── SSE stream ──────────────────────────────────────────────────────────────

@nt_text_bp.route('/api/nt-text/stream')
def api_nt_text_stream():
    reference = request.args.get('ref', '').strip()
    lang      = request.args.get('lang', 'en')

    def generate():
        def event(type_, **kwargs):
            payload = json.dumps({'type': type_, **kwargs})
            return f'data: {payload}\n\n'

        if not reference:
            yield event('error', msg='ref parameter required')
            return

        len_err = _check_ref_length(reference)
        if len_err:
            yield event('error', msg=len_err)
            return

        corpus   = state.corpus
        pipeline = state.pipeline

        if corpus is None or pipeline is None:
            yield event('error', msg='Server not ready — corpus or pipeline not initialized')
            return

        # Validate: NT references only
        from biblical_core.ref_utils import validate_nt_reference
        val_err = validate_nt_reference(reference)
        if val_err:
            yield event('error', msg=val_err)
            return

        # Step 1: load verse text
        yield event('step', msg=_step(lang, 'load_verse'))
        gnt_words = corpus.get_verse_words(reference, 'GNT')
        gnt_text  = ' '.join(w.word_text for w in gnt_words) if gnt_words else ''

        if lang == 'es':
            cached_es = pipeline.get_cached_es(reference, 'nt_text', _NT_TEXT_PROMPT, NT_TEXT_MODEL)
            if cached_es:
                yield event('step', msg=_step(lang, 'found_es'))
                cached_es['gnt_text'] = gnt_text
                yield event('done', data=cached_es)
                return

        # Step 2: check English cache
        yield event('step', msg=_step(lang, 'checking_cache'))
        cached = pipeline.get_cached(reference, 'nt_text', _NT_TEXT_PROMPT, NT_TEXT_MODEL)

        if cached:
            yield event('step', msg=_step(lang, 'found_cache'))
            result = cached
        else:
            # Step 3: call Claude
            yield event('step', msg=_step(lang, 'generating'))
            _result_box = [None]

            def _run():
                try:
                    _result_box[0] = pipeline.analyze_nt_text(reference, gnt_text)
                except Exception as exc:
                    _result_box[0] = {'error': str(exc)}

            _t = threading.Thread(target=_run, daemon=True)
            _t.start()
            while _t.is_alive():
                _t.join(timeout=8)
                if _t.is_alive():
                    yield ': keepalive\n\n'
            result = _result_box[0] or {'error': 'Analysis returned no result'}

        if result.get('error'):
            yield event('error', msg=result['error'])
            return

        result['gnt_text'] = gnt_text

        if lang == 'es':
            yield event('step', msg=_step(lang, 'translating'))
            _tr_box = [result]

            def _run_tr():
                from blueprints.textual import _translate_step
                translated = _translate_step(pipeline, lang, result, reference,
                                             'nt_text', _NT_TEXT_PROMPT, NT_TEXT_MODEL)
                translated['gnt_text'] = result['gnt_text']
                _tr_box[0] = translated

            _tt = threading.Thread(target=_run_tr, daemon=True)
            _tt.start()
            while _tt.is_alive():
                _tt.join(timeout=8)
                if _tt.is_alive():
                    yield ': keepalive\n\n'
            result = _tr_box[0]

        yield event('done', data=result)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={'Cache-Control': 'no-cache', 'X-Accel-Buffering': 'no'},
    )
```

- [ ] **Step 2: Verify blueprint compiles**

```bash
python3 -c "from blueprints.nt_text import nt_text_bp; print('ok')"
```

- [ ] **Step 3: Commit**

```bash
git add blueprints/nt_text.py
git commit -m "feat: add NT Text blueprint with SSE stream endpoint"
```

---

## Task 9: NT Text template and JS

**Files:**
- Create: `templates/nt_text.html`
- Create: `static/nt_text.js`

- [ ] **Step 1: Create templates/nt_text.html**

```html
{% extends "base.html" %}
{% block title %}{{ _t('nt_text_page_title') }}{% endblock %}
{% block meta_description %}Analyze the textual tradition of any New Testament passage. Manuscript family support, Metzger A/B/C/D ratings, variant register, and extended analysis for disputed passages.{% endblock %}
{% block og_title %}NT Textual Tradition Analyzer — BibCrit{% endblock %}
{% block og_description %}Manuscript family support, Metzger ratings, and variant register for any NT passage.{% endblock %}

{% block content %}

<div class="tool-header">
  <h1 class="tool-title">{{ _t('nt_text_tool_title') }}</h1>
  <p class="tool-subtitle">{{ _t('nt_text_tool_subtitle') }}</p>
</div>

<!-- Passage Selector Bar -->
<div class="passage-bar">
  <div class="passage-bar-row passage-bar-main">
    <span class="passage-label">{{ _t('passage_label') }}:</span>
    <div class="passage-bar-selectors">
      <select id="sel-book" class="passage-select" aria-label="{{ _t('book_label') }}">
        <option value="">{{ _t('passage_book_placeholder') }}</option>
      </select>
      <select id="sel-chapter" class="passage-select" aria-label="Chapter" disabled>
        <option value="">{{ _t('passage_ch') }}</option>
      </select>
      <select id="sel-verse" class="passage-select" aria-label="Verse" disabled>
        <option value="">{{ _t('passage_vs') }}</option>
      </select>
    </div>
    <span class="passage-or">{{ _t('passage_or') }}</span>
    <input type="text" id="ref-input" class="passage-input"
           placeholder="Mark 16:9" value="{{ reference }}"
           aria-label="Type a reference">
    <div class="passage-bar-actions">
      <button id="btn-analyze" class="btn-primary">{{ _t('nt_text_analyze_btn') }}</button>
    </div>
  </div>
</div>

<!-- Empty / Welcome State -->
<div id="empty-state" class="empty-state">
  <div class="empty-inner">
    <p>{{ _t('nt_text_empty_body') }}</p>
    <div class="bt-legend-hero" style="margin-bottom:1.5rem;">
      <span class="bt-legend-item"><span class="ms-rating-badge rating-a">A</span> Certain</span>
      <span class="bt-legend-item"><span class="ms-rating-badge rating-b">B</span> Almost certain</span>
      <span class="bt-legend-item"><span class="ms-rating-badge rating-c">C</span> Considerable doubt</span>
      <span class="bt-legend-item"><span class="ms-rating-badge rating-d">D</span> Very high doubt</span>
    </div>
    <p class="featured-label">{{ _t('featured_label') }}</p>
    <div class="featured-passages">
      <a href="#" class="featured-ref" data-ref="Mark 16:9">{{ _t('feat_nt_mark169') | safe }}</a>
      <a href="#" class="featured-ref" data-ref="John 7:53">{{ _t('feat_nt_john753') | safe }}</a>
      <a href="#" class="featured-ref" data-ref="1 John 5:7">{{ _t('feat_nt_1jn57') | safe }}</a>
      <a href="#" class="featured-ref" data-ref="Matthew 1:16">{{ _t('feat_nt_matt116') | safe }}</a>
    </div>
  </div>
</div>

<!-- Loading State -->
<div id="loading-state" class="loading-state" style="display:none;" aria-live="polite">
  <div class="loading-spinner"></div>
  <p id="loading-step" class="loading-step-msg">{{ _t('loading_preparing') }}</p>
  <p id="loading-timer" class="loading-timer"></p>
</div>

<!-- Passage heading -->
<div id="passage-heading" class="passage-heading" style="display:none;"></div>

<!-- Results area -->
<div id="nt-text-results" style="display:none;">

  <!-- GNT text display -->
  <div id="gnt-text-display" class="num-section" style="display:none;">
    <div class="num-section-label">SBLGNT Text</div>
    <div id="gnt-text-body" class="gnt-text-body"></div>
  </div>

  <!-- Metzger rating badge -->
  <div id="metzger-section" style="display:none;">
    <div class="metzger-rating-row">
      <span class="metzger-label">Metzger Rating:</span>
      <span id="metzger-badge" class="ms-rating-badge rating-?">?</span>
      <span id="metzger-justification" class="metzger-just"></span>
    </div>
  </div>

  <!-- Manuscript family support -->
  <div id="ms-families-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('nt_text_manuscript_families') }}</div>
    <div id="ms-families-body"></div>
  </div>

  <!-- Variant register -->
  <div id="variant-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('nt_text_variant_register') }}</div>
    <div id="variant-body"></div>
  </div>

  <!-- Disputed passage extended section (shown only when disputed_passage is non-null) -->
  <div id="disputed-section" class="num-section disputed-section" style="display:none;">
    <div class="num-section-label">⚠️ {{ _t('nt_text_disputed_passage') }}</div>
    <div id="disputed-body"></div>
  </div>

  <!-- Synthesis -->
  <div id="synthesis-section" class="num-section" style="display:none;">
    <div class="num-section-label">{{ _t('section_synthesis') }}</div>
    <div id="synthesis-body"></div>
  </div>

  <!-- BibCrit Assessment -->
  <div id="bibcrit-assessment" style="display:none;">
    <div class="num-section-label" style="margin-top:1.5rem;">{{ _t('section_bibcrit_assessment') }}</div>
    <div id="bibcrit-body"></div>
  </div>

  <!-- Export row -->
  <div class="export-row" id="export-row" style="display:none;">
    <button class="btn-export" id="btn-sbl" title="Copy SBL footnote">📋 SBL Footnote</button>
    <button class="btn-export" id="btn-bibtex" title="Copy BibTeX">📋 BibTeX</button>
    <button class="btn-export btn-share" id="btn-share" title="Share">
      <span class="material-symbols-outlined" style="font-size:14px;vertical-align:-2px">qr_code_2</span> Share
    </button>
  </div>
</div>

<!-- Toast -->
<div id="toast" class="toast" style="display:none;" role="status"></div>

{% endblock %}

{% block scripts %}
<script>window.TOOL_MAX_VERSES = 30;</script>
<script src="{{ url_for('static', filename='nt_text.js') }}"></script>
{% if reference %}
<script>
  document.addEventListener('DOMContentLoaded', function() {
    if (window.ntText) window.ntText.analyze('{{ reference | e }}');
  });
</script>
{% endif %}
{% endblock %}
```

- [ ] **Step 2: Create static/nt_text.js**

```javascript
/* BibCrit — NT Textual Tradition Analyzer */

(function () {
  'use strict';

  var _NT_BOOKS = {
    'Matthew': 28, 'Mark': 16, 'Luke': 24, 'John': 21, 'Acts': 28,
    'Romans': 16, '1 Corinthians': 16, '2 Corinthians': 13,
    'Galatians': 6, 'Ephesians': 6, 'Philippians': 4, 'Colossians': 4,
    '1 Thessalonians': 5, '2 Thessalonians': 3, '1 Timothy': 6,
    '2 Timothy': 4, 'Titus': 3, 'Philemon': 1, 'Hebrews': 13,
    'James': 5, '1 Peter': 5, '2 Peter': 3, '1 John': 5,
    '2 John': 1, '3 John': 1, 'Jude': 1, 'Revelation': 22,
  };

  var selBook    = document.getElementById('sel-book');
  var selChapter = document.getElementById('sel-chapter');
  var selVerse   = document.getElementById('sel-verse');
  var refInput   = document.getElementById('ref-input');
  var btnAnalyze = document.getElementById('btn-analyze');
  var emptyState = document.getElementById('empty-state');
  var loadState  = document.getElementById('loading-state');
  var loadStep   = document.getElementById('loading-step');
  var loadTimer  = document.getElementById('loading-timer');
  var heading    = document.getElementById('passage-heading');
  var results    = document.getElementById('nt-text-results');
  var toast      = document.getElementById('toast');

  if (!btnAnalyze) return;

  var _timer = null;
  var _currentRef = '';

  if (selBook) {
    Object.keys(_NT_BOOKS).forEach(function (b) {
      var opt = document.createElement('option');
      opt.value = b; opt.textContent = b;
      selBook.appendChild(opt);
    });
  }

  function _resetSelect(el, ph) {
    while (el.options.length > 1) el.remove(1);
    el.options[0].text = ph;
    el.disabled = true; el.value = '';
  }

  if (selBook) {
    selBook.addEventListener('change', function () {
      _resetSelect(selChapter, 'Ch\u2026');
      _resetSelect(selVerse, 'Vs\u2026');
      var n = _NT_BOOKS[this.value] || 0;
      for (var i = 1; i <= n; i++) {
        var o = document.createElement('option');
        o.value = i; o.textContent = i; selChapter.appendChild(o);
      }
      if (n) selChapter.disabled = false;
    });
  }

  if (selChapter) {
    selChapter.addEventListener('change', function () {
      _resetSelect(selVerse, 'Vs\u2026');
      for (var v = 1; v <= 30; v++) {
        var o = document.createElement('option');
        o.value = v; o.textContent = v; selVerse.appendChild(o);
      }
      selVerse.disabled = false;
    });
  }

  if (selVerse) {
    selVerse.addEventListener('change', function () {
      var b = selBook ? selBook.value : '';
      var c = selChapter ? selChapter.value : '';
      if (b && c && this.value) refInput.value = b + ' ' + c + ':' + this.value;
    });
  }

  document.querySelectorAll('.featured-ref').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var ref = this.dataset.ref;
      if (ref) { refInput.value = ref; analyze(ref); }
    });
  });

  btnAnalyze.addEventListener('click', function () {
    var ref = (refInput ? refInput.value : '').trim();
    if (!ref) { showToast(window.t ? window.t('err_enter_passage', 'Please enter a passage') : 'Please enter a passage'); return; }
    analyze(ref);
  });

  if (refInput) refInput.addEventListener('keydown', function (e) { if (e.key === 'Enter') btnAnalyze.click(); });

  function showToast(msg, dur) {
    if (!toast) return;
    toast.textContent = msg; toast.style.display = 'block';
    setTimeout(function () { toast.style.display = 'none'; }, dur || 3000);
  }

  function setLoading(on) {
    if (emptyState) emptyState.style.display = on ? 'none' : '';
    if (loadState)  loadState.style.display  = on ? 'block' : 'none';
    if (results)    results.style.display    = on ? 'none' : '';
    if (on && _timer) clearInterval(_timer);
    if (on && loadTimer) {
      var s = 0; loadTimer.textContent = '';
      _timer = setInterval(function () { loadTimer.textContent = (++s) + 's'; }, 1000);
    } else if (loadTimer) { loadTimer.textContent = ''; }
  }

  function esc(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function renderResult(data) {
    if (_timer) { clearInterval(_timer); _timer = null; }
    if (loadTimer) loadTimer.textContent = '';
    setLoading(false);
    if (heading) { heading.textContent = data.reference || _currentRef; heading.style.display = ''; }

    // GNT text
    if (data.gnt_text) {
      var gntEl = document.getElementById('gnt-text-body');
      var gntSec = document.getElementById('gnt-text-display');
      if (gntEl) gntEl.textContent = data.gnt_text;
      if (gntSec) gntSec.style.display = '';
    }

    // Metzger rating
    if (data.metzger_rating && data.metzger_rating.rating) {
      var badge = document.getElementById('metzger-badge');
      var just  = document.getElementById('metzger-justification');
      var mSec  = document.getElementById('metzger-section');
      var r     = data.metzger_rating.rating.toUpperCase();
      if (badge) {
        badge.textContent = r;
        badge.className = 'ms-rating-badge rating-' + r.toLowerCase();
      }
      if (just) just.textContent = data.metzger_rating.justification || '';
      if (mSec) mSec.style.display = '';
    }

    // Manuscript families
    if (data.manuscript_families) {
      var mfHtml = '';
      var families = ['alexandrian', 'western', 'byzantine', 'caesarean'];
      families.forEach(function (f) {
        var fm = data.manuscript_families[f];
        if (!fm) return;
        var supportClass = 'support-' + (fm.support || 'unknown').replace(/_/g, '-');
        mfHtml += '<div class="ms-family-row">' +
          '<span class="ms-family-name">' + esc(f.charAt(0).toUpperCase() + f.slice(1)) + '</span>' +
          '<span class="ms-family-witnesses">' + esc((fm.witnesses || []).join(', ')) + '</span>' +
          '<span class="ms-support ' + supportClass + '">' + esc(fm.support || '') + '</span>' +
          '<p class="ms-family-note">' + esc(fm.note || '') + '</p></div>';
      });
      var mfEl  = document.getElementById('ms-families-body');
      var mfSec = document.getElementById('ms-families-section');
      if (mfEl) mfEl.innerHTML = mfHtml;
      if (mfSec && mfHtml) mfSec.style.display = '';
    }

    // Variant register
    if (data.variant_register && data.variant_register.length) {
      var vrHtml = data.variant_register.map(function (v, i) {
        return '<div class="variant-card">' +
          '<div class="vc-type">Variant ' + (i + 1) + '</div>' +
          '<p class="vc-text">' + esc(v.variant_text || '') + '</p>' +
          '<div class="vc-pair"><span class="vc-label">Support:</span> ' + esc(v.manuscript_support || '') + '</div>' +
          '<div class="vc-pair">' +
            '<span class="vc-label">Intrinsic:</span> ' + esc(v.intrinsic_probability || '') +
            ' &nbsp;|&nbsp; <span class="vc-label">Transcriptional:</span> ' + esc(v.transcriptional_probability || '') +
          '</div>' +
          '<p class="vc-note">' + esc(v.assessment || '') + '</p></div>';
      }).join('');
      var vrEl  = document.getElementById('variant-body');
      var vrSec = document.getElementById('variant-section');
      if (vrEl) vrEl.innerHTML = vrHtml;
      if (vrSec) vrSec.style.display = '';
    }

    // Disputed passage
    if (data.disputed_passage) {
      var dp = data.disputed_passage;
      var dpHtml =
        '<div class="disputed-designation">' + esc(dp.designation || '') + '</div>' +
        '<div class="dp-row"><strong>Evidence for inclusion:</strong> ' + esc(dp.manuscript_evidence_for || '') + '</div>' +
        '<div class="dp-row"><strong>Evidence against:</strong> ' + esc(dp.manuscript_evidence_against || '') + '</div>' +
        '<div class="dp-row"><strong>Internal evidence:</strong> ' + esc(dp.internal_evidence || '') + '</div>' +
        '<div class="dp-row"><strong>Scholarly consensus:</strong> ' + esc(dp.scholarly_consensus || '') + '</div>' +
        '<div class="dp-row"><strong>In major translations:</strong> ' + esc(dp.pastoral_note || '') + '</div>';
      var dpEl  = document.getElementById('disputed-body');
      var dpSec = document.getElementById('disputed-section');
      if (dpEl) dpEl.innerHTML = dpHtml;
      if (dpSec) dpSec.style.display = '';
    }

    // Synthesis
    if (data.synthesis) {
      var synEl  = document.getElementById('synthesis-body');
      var synSec = document.getElementById('synthesis-section');
      if (synEl) synEl.textContent = data.synthesis;
      if (synSec) synSec.style.display = '';
    }

    // Assessment
    if (data.assessment) {
      var a = data.assessment;
      var aHtml = '';
      if (a.title)    aHtml += '<h3 class="bc-title">' + esc(a.title) + '</h3>';
      if (a.plain)    aHtml += '<p class="bc-plain">' + esc(a.plain) + '</p>';
      if (a.reasoning) aHtml += '<p>' + esc(a.reasoning) + '</p>';
      if (a.recommended_reading) aHtml += '<p><strong>Recommended edition:</strong> ' + esc(a.recommended_reading) + '</p>';
      if (a.open_questions) aHtml += '<p><strong>Open questions:</strong> ' + esc(a.open_questions) + '</p>';
      if (typeof a.confidence === 'number') {
        aHtml += '<div class="confidence-bar"><div class="confidence-fill" style="width:' + (a.confidence * 100).toFixed(0) + '%"></div></div>';
      }
      var bibBody = document.getElementById('bibcrit-body');
      var bibSec  = document.getElementById('bibcrit-assessment');
      if (bibBody) bibBody.innerHTML = aHtml;
      if (bibSec)  bibSec.style.display = '';
    }

    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';
    _wireExport(data);
  }

  function _wireExport(data) {
    var btnSbl    = document.getElementById('btn-sbl');
    var btnBibtex = document.getElementById('btn-bibtex');
    var btnShare  = document.getElementById('btn-share');
    if (btnSbl && data.citations && data.citations.sbl) {
      btnSbl.onclick = function () { navigator.clipboard.writeText(data.citations.sbl); showToast('SBL copied!'); };
    }
    if (btnBibtex && data.citations && data.citations.bibtex) {
      btnBibtex.onclick = function () { navigator.clipboard.writeText(data.citations.bibtex); showToast('BibTeX copied!'); };
    }
    if (btnShare) {
      btnShare.onclick = function () {
        var url = window.location.origin + '/nt-text?ref=' + encodeURIComponent(_currentRef);
        navigator.clipboard.writeText(url); showToast('Link copied!');
      };
    }
  }

  function analyze(ref) {
    _currentRef = ref;
    setLoading(true);
    if (loadStep) loadStep.textContent = window.t ? window.t('loading_preparing', 'Preparing…') : 'Preparing…';

    // Hide all result sections
    ['gnt-text-display', 'metzger-section', 'ms-families-section', 'variant-section',
     'disputed-section', 'synthesis-section', 'bibcrit-assessment', 'export-row'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.style.display = 'none';
    });

    var lang = new URLSearchParams(window.location.search).get('lang') || 'en';
    var url  = '/api/nt-text/stream?ref=' + encodeURIComponent(ref) + '&lang=' + lang;
    var es   = new EventSource(url);

    es.onmessage = function (e) {
      try {
        var msg = JSON.parse(e.data);
        if (msg.type === 'step') {
          if (loadStep) loadStep.textContent = msg.msg;
        } else if (msg.type === 'done') {
          es.close(); renderResult(msg.data);
        } else if (msg.type === 'error') {
          es.close(); setLoading(false); showToast(msg.msg || 'Error', 5000);
        }
      } catch (_) {}
    };

    es.onerror = function () {
      es.close(); setLoading(false);
      showToast(window.t ? window.t('err_connection', 'Connection error') : 'Connection error', 5000);
    };
  }

  window.ntText = { analyze: analyze };
}());
```

- [ ] **Step 3: Commit**

```bash
git add templates/nt_text.html static/nt_text.js
git commit -m "feat: add NT Text template and JS"
```

---

*— End of Tasks 1–9. Tasks 10–16 follow in the next section. —*

---

## Task 10: Wire NT Text into app.py, ref_utils, i18n, and preseed

**Files:**
- Modify: `app.py`
- Modify: `biblical_core/ref_utils.py`
- Modify: `data/i18n.json`
- Modify: `scripts/preseed_featured.py`

- [ ] **Step 1: Register NT Text blueprint in app.py**

Add after the Targum import (from Task 6):

```python
from blueprints.nt_text import nt_text_bp
```

Add after `app.register_blueprint(targum_bp)`:

```python
app.register_blueprint(nt_text_bp)
```

- [ ] **Step 2: Add NT Text limits and validation to ref_utils.py**

Add to `TOOL_VERSE_LIMITS`:

```python
'nt_text': 30,
```

Add the NT validation function:

```python
# NT books (Matthew–Revelation, 27 books)
_NT_BOOKS = {
    'matthew', 'mark', 'luke', 'john', 'acts', 'romans',
    '1 corinthians', '2 corinthians', 'galatians', 'ephesians',
    'philippians', 'colossians', '1 thessalonians', '2 thessalonians',
    '1 timothy', '2 timothy', 'titus', 'philemon', 'hebrews',
    'james', '1 peter', '2 peter', '1 john', '2 john', '3 john',
    'jude', 'revelation',
}


def validate_nt_reference(reference: str) -> str | None:
    """Return error string if reference is outside the NT canon, else None.

    The NT Text Analyzer is for Matthew–Revelation only.
    For OT manuscript comparison use the Ancient Witness Bridge.
    """
    parts = reference.strip().lower().split()
    if parts[0].isdigit() and len(parts) >= 2:
        book = parts[0] + ' ' + parts[1].split(':')[0]
    else:
        book = parts[0].split(':')[0]

    if book in _NT_BOOKS:
        return None

    return (
        f'"{reference}" appears to be an Old Testament reference. '
        'The NT Textual Tradition Analyzer covers Matthew–Revelation only. '
        'For OT manuscript comparison, use the Ancient Witness Bridge (/dss).'
    )
```

- [ ] **Step 3: Add NT Text i18n keys**

In `data/i18n.json`, add to `"en"`:

```json
"nt_text_page_title": "NT Textual Tradition Analyzer — BibCrit",
"nt_text_tool_title": "NT Textual Tradition Analyzer",
"nt_text_tool_subtitle": "Manuscript family support (Alexandrian, Western, Byzantine, Caesarean), Metzger A/B/C/D ratings, and variant register for any NT passage. Extended analysis for disputed passages.",
"nt_text_analyze_btn": "Analyze",
"nt_text_empty_body": "Enter any New Testament reference to see its textual tradition, manuscript family support, and Metzger confidence rating.",
"nt_text_manuscript_families": "Manuscript Family Support",
"nt_text_variant_register": "Variant Register",
"nt_text_disputed_passage": "Disputed Passage",
"feat_nt_mark169": "Mark 16:9 — Longer Ending of Mark",
"feat_nt_john753": "John 7:53 — Pericope Adulterae",
"feat_nt_1jn57": "1 John 5:7 — Comma Johanneum",
"feat_nt_matt116": "Matthew 1:16 — Birth of Jesus (textual variation)",
"nav_nt_text": "NT Text",
"tool_nt_text_title": "NT Textual Tradition Analyzer",
"tool_nt_text_desc": "Manuscript family support (Alexandrian, Western, Byzantine, Caesarean), Metzger A/B/C/D ratings, and full variant register for any NT passage.",
"tool_nt_text_desc_phd": "SBLGNT-grounded textual analysis with Metzger methodology, manuscript family attestation, and extended treatment of all major disputed passages.",
"tool_nt_text_desc_student": "Discover how different ancient manuscripts of the New Testament vary — and what scholars think the original text said."
```

Add to `"es"`:

```json
"nt_text_page_title": "Analizador de Tradición Textual NT — BibCrit",
"nt_text_tool_title": "Analizador de Tradición Textual NT",
"nt_text_tool_subtitle": "Soporte de familias de manuscritos (Alejandrina, Occidental, Bizantina, Cesarense), calificaciones Metzger A/B/C/D y registro de variantes para cualquier pasaje del NT.",
"nt_text_analyze_btn": "Analizar",
"nt_text_empty_body": "Ingresa cualquier referencia del Nuevo Testamento para ver su tradición textual, soporte de familias de manuscritos y calificación Metzger.",
"nt_text_manuscript_families": "Soporte de Familias de Manuscritos",
"nt_text_variant_register": "Registro de Variantes",
"nt_text_disputed_passage": "Pasaje Disputado",
"feat_nt_mark169": "Marcos 16:9 — Final largo de Marcos",
"feat_nt_john753": "Juan 7:53 — Pericope Adulterae",
"feat_nt_1jn57": "1 Juan 5:7 — Comma Johanneum",
"feat_nt_matt116": "Mateo 1:16 — Nacimiento de Jesús (variación textual)",
"nav_nt_text": "Texto NT",
"tool_nt_text_title": "Analizador de Tradición Textual NT",
"tool_nt_text_desc": "Soporte de familias de manuscritos, calificaciones Metzger y registro de variantes para cualquier pasaje del NT.",
"tool_nt_text_desc_phd": "Análisis textual respaldado por SBLGNT con metodología Metzger y tratamiento extendido de pasajes disputados.",
"tool_nt_text_desc_student": "Descubre cómo los manuscritos antiguos del Nuevo Testamento varían y qué piensan los eruditos sobre el texto original."
```

- [ ] **Step 4: Add NT Text to preseed and ENDPOINT_OVERRIDES**

In `scripts/preseed_featured.py`, find `ENDPOINT_OVERRIDES` and add:

```python
ENDPOINT_OVERRIDES = {"nt_ot": "nt-ot", "nt_text": "nt-text"}
```

Add to `PASSAGES`:

```python
("nt_text", "Mark 16:9"),
("nt_text", "John 7:53"),
("nt_text", "1 John 5:7"),
("nt_text", "Matthew 1:16"),
```

- [ ] **Step 5: Add nav link for NT Text**

In `templates/base.html`, following the Targum nav link added in Task 6, add:

```html
<a href="/nt-text{% if lang != 'en' %}?lang={{ lang }}{% endif %}"
   class="nav-link {% if request.path == '/nt-text' %}active{% endif %}">
  {{ _t('nav_nt_text') }}
</a>
```

- [ ] **Step 6: Verify app starts and routes resolve**

```bash
python3 -c "from app import create_app; app = create_app(); print('ok')"
python3 -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    r1 = c.get('/targum')
    r2 = c.get('/nt-text')
    print(r1.status_code, r2.status_code)   # 200 200
"
```

- [ ] **Step 7: Commit**

```bash
git add app.py biblical_core/ref_utils.py data/i18n.json scripts/preseed_featured.py templates/base.html
git commit -m "feat: wire NT Text into app.py, ref_utils, i18n, preseed, and nav"
```

---

## Task 11: Vulgate ingest script

**Files:**
- Create: `scripts/ingest_vulgate_clementine.py`

The scrollmapper/bible_databases Clementine Vulgate is a single CSV at:
`https://raw.githubusercontent.com/scrollmapper/bible_databases/master/formats/csv/t_vul.csv`

Columns: `b` (book 1–73), `c` (chapter), `v` (verse), `t` (Latin text).
Books 1–39 = OT (Protestant canon order), 40–46 = deuterocanonicals, 47–73 = NT (1=Matthew).

- [ ] **Step 1: Create the Vulgate ingest script**

```python
#!/usr/bin/env python3
"""Download Clementine Vulgate from scrollmapper/bible_databases and split into per-book CSVs.

Usage:
    python scripts/ingest_vulgate_clementine.py --out data/corpora/vul_clementine/

Writes one CSV per book, e.g. genesis.csv, matthew.csv.
Schema: book_order,book,chapter,verse,reference,position,word_text,lemma,morph,strong,manuscript,tradition
"""

import argparse
import csv
import io
import os
import sys
import urllib.request

VUL_CSV_URL = (
    'https://raw.githubusercontent.com/scrollmapper/'
    'bible_databases/master/formats/csv/t_vul.csv'
)

# Book mapping: scrollmapper b-number → (canonical_name, our_book_order)
# scrollmapper uses b=1..66 for Protestant ordering (Gen=1 .. Rev=66)
# Deuterocanonicals are skipped (not in our MT/LXX reference set)
BOOK_MAP = {
    1:  ('Genesis',         1),
    2:  ('Exodus',          2),
    3:  ('Leviticus',       3),
    4:  ('Numbers',         4),
    5:  ('Deuteronomy',     5),
    6:  ('Joshua',          6),
    7:  ('Judges',          7),
    8:  ('Ruth',            8),
    9:  ('1 Samuel',        9),
    10: ('2 Samuel',       10),
    11: ('1 Kings',        11),
    12: ('2 Kings',        12),
    13: ('1 Chronicles',   13),
    14: ('2 Chronicles',   14),
    15: ('Ezra',           15),
    16: ('Nehemiah',       16),
    17: ('Esther',         17),
    18: ('Job',            18),
    19: ('Psalms',         19),
    20: ('Proverbs',       20),
    21: ('Ecclesiastes',   21),
    22: ('Song of Songs',  22),
    23: ('Isaiah',         23),
    24: ('Jeremiah',       24),
    25: ('Lamentations',   25),
    26: ('Ezekiel',        26),
    27: ('Daniel',         27),
    28: ('Hosea',          28),
    29: ('Joel',           29),
    30: ('Amos',           30),
    31: ('Obadiah',        31),
    32: ('Jonah',          32),
    33: ('Micah',          33),
    34: ('Nahum',          34),
    35: ('Habakkuk',       35),
    36: ('Zephaniah',      36),
    37: ('Haggai',         37),
    38: ('Zechariah',      38),
    39: ('Malachi',        39),
    # NT: scrollmapper uses 40=Matthew in some versions; check actual file
    40: ('Matthew',        41),
    41: ('Mark',           42),
    42: ('Luke',           43),
    43: ('John',           44),
    44: ('Acts',           45),
    45: ('Romans',         46),
    46: ('1 Corinthians',  47),
    47: ('2 Corinthians',  48),
    48: ('Galatians',      49),
    49: ('Ephesians',      50),
    50: ('Philippians',    51),
    51: ('Colossians',     52),
    52: ('1 Thessalonians',53),
    53: ('2 Thessalonians',54),
    54: ('1 Timothy',      55),
    55: ('2 Timothy',      56),
    56: ('Titus',          57),
    57: ('Philemon',       58),
    58: ('Hebrews',        59),
    59: ('James',          60),
    60: ('1 Peter',        61),
    61: ('2 Peter',        62),
    62: ('1 John',         63),
    63: ('2 John',         64),
    64: ('3 John',         65),
    65: ('Jude',           66),
    66: ('Revelation',     67),
}

FIELDNAMES = [
    'book_order', 'book', 'chapter', 'verse', 'reference',
    'position', 'word_text', 'lemma', 'morph', 'strong',
    'manuscript', 'tradition',
]


def book_slug(name: str) -> str:
    return name.lower().replace(' ', '_').replace("'", '')


def main():
    parser = argparse.ArgumentParser(description='Ingest Clementine Vulgate from scrollmapper')
    parser.add_argument('--out', default='data/corpora/vul_clementine',
                        help='Output directory')
    args = parser.parse_args()

    os.makedirs(args.out, exist_ok=True)

    print(f'Downloading {VUL_CSV_URL} …')
    with urllib.request.urlopen(VUL_CSV_URL, timeout=60) as resp:
        raw_bytes = resp.read()

    print(f'Downloaded {len(raw_bytes):,} bytes. Parsing…')

    # Group rows by book number
    book_rows: dict[int, list] = {}
    reader = csv.DictReader(io.StringIO(raw_bytes.decode('utf-8')))

    # Detect actual column names (may be 'b','c','v','t' or 'book','chapter','verse','text')
    for row in reader:
        keys = list(row.keys())
        b_key = 'b' if 'b' in keys else ('book' if 'book' in keys else keys[0])
        c_key = 'c' if 'c' in keys else ('chapter' if 'chapter' in keys else keys[1])
        v_key = 'v' if 'v' in keys else ('verse' if 'verse' in keys else keys[2])
        t_key = 't' if 't' in keys else ('text' if 'text' in keys else keys[3])

        try:
            b = int(row[b_key])
        except (ValueError, KeyError):
            continue

        if b not in BOOK_MAP:
            continue

        book_rows.setdefault(b, []).append({
            'c': int(row[c_key]),
            'v': int(row[v_key]),
            't': row[t_key].strip(),
        })

    total_words = 0
    files_written = 0

    for b_num, rows in sorted(book_rows.items()):
        book_name, book_order = BOOK_MAP[b_num]
        slug = book_slug(book_name)
        out_path = os.path.join(args.out, f'{slug}.csv')
        word_count = 0

        with open(out_path, 'w', newline='', encoding='utf-8') as fh:
            writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
            writer.writeheader()
            for row in rows:
                verse_text = row['t']
                if not verse_text:
                    continue
                reference = f"{book_name} {row['c']}:{row['v']}"
                words = verse_text.split()
                for pos, word in enumerate(words, start=1):
                    writer.writerow({
                        'book_order': book_order,
                        'book':       book_name,
                        'chapter':    row['c'],
                        'verse':      row['v'],
                        'reference':  reference,
                        'position':   pos,
                        'word_text':  word,
                        'lemma':      '',
                        'morph':      '',
                        'strong':     '',
                        'manuscript': 'Clementine',
                        'tradition':  'VUL',
                    })
                    word_count += 1

        print(f'  {slug}.csv — {word_count} words')
        total_words += word_count
        files_written += 1

    print(f'\nDone. {files_written} CSV files, {total_words:,} total words.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Run the ingest script**

```bash
python3 scripts/ingest_vulgate_clementine.py --out data/corpora/vul_clementine/
```

Expected: 66 CSV files, ~600,000 words total.

- [ ] **Step 3: Verify**

```bash
ls data/corpora/vul_clementine/*.csv | wc -l   # → 66
python3 -c "
from biblical_core.corpus import BiblicalCorpus
c = BiblicalCorpus()
c.set_data_dir('data')
words = c.get_verse_words('Isaiah 7:14', 'VUL')
print([w.word_text for w in words])   # should contain 'virgo'
"
```

- [ ] **Step 4: Commit**

```bash
git add scripts/ingest_vulgate_clementine.py data/corpora/vul_clementine/
git commit -m "feat: add Clementine Vulgate corpus via scrollmapper (66 books)"
```

---

## Task 12: Add Vulgate to DSS Bridge (dss_v7 prompt + pipeline + blueprint)

**Files:**
- Create: `data/prompts/dss_v7.txt` (copy of v6 + VUL_TEXT)
- Modify: `biblical_core/claude_pipeline.py` (analyze_dss: v6→v7, add vul_text param)
- Modify: `blueprints/textual.py` (DSS stream: fetch VUL corpus, bump _DSS_PROMPT)

- [ ] **Step 1: Create dss_v7.txt**

Copy `data/prompts/dss_v6.txt` to `data/prompts/dss_v7.txt`:

```bash
cp data/prompts/dss_v6.txt data/prompts/dss_v7.txt
```

Open `data/prompts/dss_v7.txt` and make two changes:

1. Add `VULGATE TEXT (Latin): {{VUL_TEXT}}` after `PESHITTA TEXT` line.

2. Add Vulgate alignment classification: add `sides_with_vul — reading agrees with the Vulgate tradition` to the ALIGNMENT CLASSIFICATIONS list.

3. Add the following instruction paragraph after the Peshitta instruction paragraph:

```
If {{VUL_TEXT}} is non-empty, populate vul_witness with full analysis treating the Vulgate as a 4th-century Latin witness. Jerome's translation from the Hebrew veritas (hebraica veritas) makes the Vulgate especially valuable for passages where it diverges from both MT and LXX (e.g. Isaiah 7:14 virgo, Genesis 3:15 ipsa, Psalm 22:16 foderunt). If {{VUL_TEXT}} is empty, set vul_witness to null.
```

4. Add `"vul_witness"` to the return JSON schema, same structure as `"pesh_witness"` but for Latin:

```json
"vul_witness": {
  "present": true,
  "alignment": "sides_with_mt | sides_with_lxx | independent | absent",
  "alignment_confidence": 0.00,
  "vul_text": "Latin Vulgate text",
  "key_readings": [
    {
      "word_position": 1,
      "mt_reading": "Hebrew MT",
      "vul_reading": "Latin Vulgate",
      "classification": "orthographic | lexical | theological | plus | minus",
      "note": "1 sentence on Jerome's translation choice"
    }
  ],
  "overall_note": "2–3 sentences on Jerome's rendering strategy for this passage"
}
```

5. Update the system field comment at the top to say `v7`.

- [ ] **Step 2: Update analyze_dss() in pipeline**

In `biblical_core/claude_pipeline.py`, find `analyze_dss()` and make these changes:

Change the signature to add `vul_text`:

```python
def analyze_dss(self, reference: str, mt_text: str = '',
                lxx_text: str = '', dss_text: str = '',
                sp_text: str = '', pesh_text: str = '',
                vul_text: str = '') -> dict:
```

Change the prompt version line:

```python
prompt_version = 'v7'   # was 'v6'
```

Add `vul_text` to the template replace chain:

```python
.replace('{{VUL_TEXT}}',  vul_text)
```

After the pesh_witness fallback block (around line 910), add a parallel vul_witness fallback:

```python
if vul_text and not data.get('vul_witness'):
    data['vul_witness'] = {
        'present': True,
        'alignment': 'independent',
        'alignment_confidence': 0.0,
        'vul_text': vul_text,
        'key_readings': [],
        'overall_note': (
            'Vulgate text is available for this passage '
            'but alignment analysis could not be generated automatically.'
        ),
    }
```

- [ ] **Step 3: Update textual.py DSS blueprint**

In `blueprints/textual.py`, change the prompt constant:

```python
_DSS_PROMPT = 'v7'   # was 'v6'
```

In `api_dss_stream()`, after fetching `pesh_words`, add:

```python
vul_words = corpus.get_verse_words(reference, 'VUL')
vul_text  = ' '.join(w.word_text for w in vul_words) if vul_words else ''
```

Pass `vul_text` to `pipeline.analyze_dss()`:

```python
_result_box[0] = pipeline.analyze_dss(
    reference, mt_text, lxx_text, dss_text, sp_text, pesh_text, vul_text
)
```

Do the same in the non-thread cached path and the Spanish translate path.

- [ ] **Step 4: Verify**

```bash
python3 -c "
from biblical_core.claude_pipeline import ClaudePipeline
import inspect
sig = inspect.signature(ClaudePipeline.analyze_dss)
print(list(sig.parameters.keys()))   # should include 'vul_text'
"
```

Expected: list includes `vul_text`.

- [ ] **Step 5: Commit**

```bash
git add data/prompts/dss_v7.txt biblical_core/claude_pipeline.py blueprints/textual.py
git commit -m "feat: add Vulgate witness to DSS Bridge (dss_v7, analyze_dss vul_text)"
```

---

## Task 13: Add Vulgate to Genealogy (genealogy_v2 prompt + pipeline + blueprint)

**Files:**
- Create: `data/prompts/genealogy_v2.txt`
- Modify: `biblical_core/claude_pipeline.py` (analyze_genealogy)
- Modify: `blueprints/textual.py` (_GENEALOGY_PROMPT + api_genealogy_stream)

- [ ] **Step 1: Create genealogy_v2.txt**

```bash
cp data/prompts/genealogy_v1.txt data/prompts/genealogy_v2.txt
```

In `data/prompts/genealogy_v2.txt`, add the following after `BOOK: {{BOOK}}`:

```
VULGATE SAMPLE TEXT (Latin, first verse of book if available): {{VUL_TEXT}}

If VUL_TEXT is non-empty, ensure the Vulgate branch node in the stemma reflects Jerome's actual translation strategy for this book. For {{BOOK}}, note whether Jerome followed the Hebrew veritas (his usual approach) or occasionally used the LXX.
```

The stemma already has a Vulgate branch node defined in the existing prompt — v2 adds corpus grounding for it.

- [ ] **Step 2: Update analyze_genealogy() in pipeline**

Change the signature:

```python
def analyze_genealogy(self, book: str, vul_text: str = '') -> dict:
```

Change the prompt version:

```python
prompt_version = 'v2'   # was 'v1'
```

Add to the template replace chain:

```python
user_content = (
    template
    .replace('{{BOOK}}',     book)
    .replace('{{VUL_TEXT}}', vul_text)
) if template else (
    f'Book: {book}\nVulgate sample: {vul_text or "(not loaded)"}\n'
    'Construct a manuscript transmission genealogy (stemma). Return JSON with stemma_nodes and stemma_edges arrays.'
)
```

- [ ] **Step 3: Update textual.py Genealogy blueprint**

Change the prompt constant:

```python
_GENEALOGY_PROMPT = 'v2'   # was 'v1'
```

In `api_genealogy_stream()`, after fetching book-level data, add:

```python
# Fetch first verse of the book as Vulgate grounding sample
vul_sample_ref = f'{book} 1:1'
vul_words = corpus.get_verse_words(vul_sample_ref, 'VUL')
vul_text  = ' '.join(w.word_text for w in vul_words) if vul_words else ''
```

Pass `vul_text` to `pipeline.analyze_genealogy()`:

```python
_result_box[0] = pipeline.analyze_genealogy(book, vul_text)
```

- [ ] **Step 4: Commit**

```bash
git add data/prompts/genealogy_v2.txt biblical_core/claude_pipeline.py blueprints/textual.py
git commit -m "feat: add Vulgate corpus grounding to Genealogy tool (genealogy_v2)"
```

---

## Task 14: Add Vulgate to Theological Revision Detector (theological_v2 + pipeline + blueprint)

**Files:**
- Create: `data/prompts/theological_v2.txt`
- Modify: `biblical_core/claude_pipeline.py` (analyze_theological)
- Modify: `blueprints/critical.py` (_THEOLOGICAL_PROMPT + api_theological_stream)

- [ ] **Step 1: Create theological_v2.txt**

```bash
cp data/prompts/theological_v1.txt data/prompts/theological_v2.txt
```

In `data/prompts/theological_v2.txt`, find the `REFERENCE: {{REFERENCE}}` line and add below it:

```
VULGATE TEXT (Latin): {{VUL_TEXT}}

Use {{VUL_TEXT}} as corpus evidence for Jerome's Vulgate renderings. Key theological revision sites involving the Vulgate: Isaiah 7:14 (almah → virgo, messianic heightening), Genesis 3:15 (ipsa/ipse controversy, protoevangelium), Psalm 22:16 (foderunt vs leones, Christological reading). If {{VUL_TEXT}} is non-empty, incorporate it into revisions where the Vulgate shows theologically motivated divergence.
```

- [ ] **Step 2: Update analyze_theological() in pipeline**

Change the signature:

```python
def analyze_theological(self, reference: str, vul_text: str = '') -> dict:
```

Change the prompt version:

```python
prompt_version = 'v2'   # was 'v1'
```

Add to the template replace chain:

```python
user_content = (
    template
    .replace('{{REFERENCE}}', reference)
    .replace('{{VUL_TEXT}}',  vul_text)
) if template else (
    f'Reference: {reference}\nVulgate: {vul_text or "(not loaded)"}\n'
    'Identify theologically motivated textual changes. Return JSON with revisions array.'
)
```

- [ ] **Step 3: Update critical.py Theological blueprint**

Change the prompt constant:

```python
_THEOLOGICAL_PROMPT = 'v2'   # was 'v1'
```

In `api_theological_stream()`, after fetching reference-level data (right after the corpus/pipeline check), add:

```python
vul_words = corpus.get_verse_words(reference, 'VUL')
vul_text  = ' '.join(w.word_text for w in vul_words) if vul_words else ''
```

Pass `vul_text` to `pipeline.analyze_theological()`:

```python
_result_box[0] = pipeline.analyze_theological(reference, vul_text)
```

- [ ] **Step 4: Verify all three Vulgate-updated methods compile**

```bash
python3 -c "
from biblical_core.claude_pipeline import ClaudePipeline
import inspect
for method in ['analyze_dss', 'analyze_genealogy', 'analyze_theological']:
    sig = inspect.signature(getattr(ClaudePipeline, method))
    params = list(sig.parameters.keys())
    has_vul = 'vul_text' in params
    print(f'{method}: vul_text={has_vul}')
"
```

Expected: three lines all ending `vul_text=True`.

```bash
python3 -c "from app import create_app; app = create_app(); print('app ok')"
```

Expected: `app ok`

- [ ] **Step 5: Commit**

```bash
git add data/prompts/theological_v2.txt biblical_core/claude_pipeline.py blueprints/critical.py
git commit -m "feat: add Vulgate corpus grounding to Theological Revision Detector (theological_v2)"
```

---

## Task 15: Update README.md and paper.md

**Files:**
- Modify: `README.md`
- Modify: `paper.md`

- [ ] **Step 1: Update README.md**

Find the tools table and add two rows:

```markdown
| Targum Comparator | `/targum` | Compare Targum Onkelos (Torah) and Jonathan (Prophets) against MT and LXX; analyze Memra, anthropomorphism avoidance, targumic expansions, and messianic reinterpretation | Sefaria (Onkelos + Jonathan) |
| NT Textual Tradition Analyzer | `/nt-text` | Manuscript family support (Alexandrian, Western, Byzantine, Caesarean), Metzger A/B/C/D ratings, variant register, and extended analysis for disputed passages | SBLGNT |
```

Update the tool count (was 11 or 13 depending on current state — add 2).

Update the corpus traditions table: add rows for Targum and Vulgate:

```markdown
| TARG | Targum Onkelos (Torah) + Targum Jonathan (Prophets) | Aramaic | ~285,000 tokens | 26 books | Sefaria |
| VUL | Clementine Vulgate | Latin | ~600,000 tokens | 66 books | scrollmapper/bible_databases |
```

Update total corpus word count (add ~885,000 to existing total).

- [ ] **Step 2: Update paper.md**

Find the sentence about corpus traditions count and update to 8 (MT, LXX, GNT, DSS, SP, PESH, TARG, VUL).

Find the sentence about total tools and update to the new count.

Find the corpus word count footnote and update with new totals.

Update any sentence that says "Peshitta uses AI-generated text" — it now uses the ETCBC corpus (from Phase 1 if complete, or note that it is corpus-backed).

Add a sentence about Vulgate integration as a 4th-century Latin witness in the three tools.

- [ ] **Step 3: Commit**

```bash
git add README.md paper.md
git commit -m "docs: update README and paper.md for Phase 2 (Targum, NT Text, Vulgate)"
```

---

## Task 16: Run preseed for new tools and final verification

**Files:**
- No code changes — operational task only

- [ ] **Step 1: Ensure server is running**

```bash
# In a separate terminal:
python3 app.py
# or: flask run --port 5001
```

Confirm: `curl -s http://localhost:5001/targum | grep -c 'Targum'` returns > 0.

- [ ] **Step 2: Run preseed for Targum**

```bash
python3 scripts/preseed_featured.py --tool targum
```

Expected: 4 lines of `✓` (Genesis 22:8, Isaiah 53:5, Exodus 3:14, Genesis 3:22). Each takes 60–90s.

- [ ] **Step 3: Run preseed for NT Text**

```bash
python3 scripts/preseed_featured.py --tool nt_text
```

Expected: 4 lines of `✓` (Mark 16:9, John 7:53, 1 John 5:7, Matthew 1:16).

- [ ] **Step 4: Verify full verification checklist from spec**

```bash
# 1. Targum corpus
ls data/corpora/targ_sefaria/*.csv | wc -l   # → 26

# 2. Vulgate corpus
ls data/corpora/vul_clementine/*.csv | wc -l  # → 66

# 3. Targum corpus query
python3 -c "
from biblical_core.corpus import BiblicalCorpus
c = BiblicalCorpus(); c.set_data_dir('data')
words = c.get_verse_words('Genesis 22:8', 'TARG')
print([w.word_text for w in words[:5]])
"

# 4. Vulgate corpus query
python3 -c "
from biblical_core.corpus import BiblicalCorpus
c = BiblicalCorpus(); c.set_data_dir('data')
words = c.get_verse_words('Isaiah 7:14', 'VUL')
print([w.word_text for w in words])   # should contain 'virgo'
"

# 5. Check cache entries
ls data/cache/ | wc -l   # should be +8 vs before preseed
```

- [ ] **Step 5: Smoke-test key pages**

```bash
python3 -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    routes = ['/targum', '/nt-text', '/dss', '/genealogy', '/theological']
    for r in routes:
        resp = c.get(r)
        print(r, resp.status_code)   # all 200
"
```

- [ ] **Step 6: Final commit**

```bash
git add .
git status   # verify no untracked sensitive files
git commit -m "feat: Phase 2 complete — Targum Comparator, NT Text Analyzer, Vulgate integration"
```

---

## Verification Checklist (from spec)

| # | Check | Command | Expected |
|---|-------|---------|----------|
| 1 | Targum CSV files | `ls data/corpora/targ_sefaria/*.csv \| wc -l` | 26 |
| 2 | Vulgate CSV files | `ls data/corpora/vul_clementine/*.csv \| wc -l` | 66 |
| 3 | Targum corpus query | `c.get_verse_words('Genesis 22:8', 'TARG')` | Aramaic word list |
| 4 | Vulgate corpus query | `c.get_verse_words('Isaiah 7:14', 'VUL')` | Latin with *virgo* |
| 5 | Targum page | `GET /targum?ref=Genesis+22:8` | Three-column view with Aramaic |
| 6 | NT Text page | `GET /nt-text?ref=Mark+16:9` | Disputed passage section visible |
| 7 | DSS Vulgate | `GET /dss?ref=Isaiah+7:14` | vul_witness with *virgo* |
| 8 | Targum preseed | `preseed_featured.py --tool targum` | 4 passages cached |
| 9 | NT Text preseed | `preseed_featured.py --tool nt_text` | 4 passages cached |
