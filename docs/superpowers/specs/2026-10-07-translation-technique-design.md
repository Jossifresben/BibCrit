# Translation Technique Workbench — Design

**Date:** 2026-10-07
**Status:** implemented on branch feature/translation-technique; see docs/translation-technique.md
**Scope:** Hebrew–Syriac lexical correspondence for the Peshitta Old Testament, Deuteronomy exposed first, inside BibCrit.

## 1. Purpose

A scholar studying translation technique in the Peshitta asks, for a Hebrew lexeme, which Syriac lexemes render it, how often, and what conditions the choice (stem, clause type, complement pattern, preposition, book). Today this is done by hand: clause-by-clause synoptic encoding in the ETCBC format, one book at a time, five verbs per dissertation. The manual encoding is the bottleneck, and the apparatus is left out because of complexity.

This feature computes those tables from a Syriac lemma layer and a word alignment that do not exist anywhere today, and makes every number traceable to its tokens and its build.

Triggering case: a dissertation on lexical consistency in P-Deuteronomy (בוא, נתן, among five verbs; the scholar also named חרם as a lexeme to research). Its published figures are a check on ours: JRD in Deuteronomy → NXT 9, KBC 2, >TJ 1; בוא → top two Syriac lexemes at about 60 and 28; נתן → about 130 and 19.

## 2. Hard constraints

- **The model never produces a number.** Counts, distributions, cross-tabulations and statistics are computed by code over a joined table. The model may annotate (propose a lemma or an alignment link) only where SEDRA, rules and the statistical aligner fail, and every such token is tagged `source: model`. Every table shows the share of its counts that rests on model-sourced tokens or links.
- **No model at query time.** Model calls happen only in the two offline build scripts.
- **Everything versioned.** `data/tt/VERSION`, a run manifest per build, and the manifest hash printed with every table and export.
- **Bilingual EN/ES** page and i18n keys, as for every BibCrit page.
- **Apparatus data is not shipped from the edition.** The Leiden apparatus is Brill copyright. The witness layer ships with a schema and a hand-keyed sample marked by its origin.
- **Gate.** The page is behind a client-side password check (obfuscation, not security), per the owner's instruction. JSON endpoints are not gated.

## 3. What exists and what is missing (surveyed 2026-10-07)

| Asset | State |
|---|---|
| BHSA Hebrew, Text-Fabric 2021 at `~/text-fabric-data/github/ETCBC/bhsa/tf/2021/` | Full morphology and syntax: `lex, gloss, sp, vs, vt, function, typ, rela, ls, prs, …`. Deuteronomy in. |
| Peshitta OT, `data/corpora/pesh_etcbc/*.csv` (from ETCBC/peshitta TF 0.2) | 39 books, 23,072 verses, 308,863 tokens. Deuteronomy 959 verses, 14,136 tokens, 4,388 unique forms. **Surface forms only**; `lemma`, `morph`, `strong` columns empty. |
| MT–Peshitta verse match | 22,889 shared references; Deuteronomy 959/959. Mismatches are a book-name bug ("Song of songs" vs "Song of Songs") plus Psalms/Chronicles/Daniel numbering. |
| Hebrew–Syriac word alignment | None, anywhere (BibCrit, Root Atlas, Constellations, Polyglot). |
| Syriac lexicon | None local. SEDRA IV API (`https://sedra.bethmardutho.org/api/word/{form}`) returns stem, category, kaylo, glosses; several analyses per form. The Root Atlas cache covers 4 of 4,388 Deuteronomy forms. |
| SEDRA coverage, live sample of 80 Deuteronomy forms | 39/40 most-frequent forms hit; 21/40 hapax forms hit. Misses are mostly forms with seyame or diacritic dots, or with object suffixes. Token-weighted coverage before normalization is in the high eighties. |
| Apparatus / manuscript sigla | None. |
| Aligner tooling | None installed; NumPy 2.2 and Text-Fabric 13 present, Python 3.10. |

## 4. Architecture

New top-level package `translation_technique/`, separate from `biblical_core/` (whose `claude_pipeline.py` is already 3,380 lines and must not grow). Four modules, one responsibility each, no module imports Flask:

| Module | Does | Reads | Writes |
|---|---|---|---|
| `lemmas.py` | Build and read the Syriac lemma layer | `data/corpora/pesh_etcbc/*.csv`, `data/tt/sedra_cache.json` | `data/tt/lemmas/<book>.jsonl`, coverage report |
| `align.py` | IBM Model 1 both directions, symmetrized, monotonic prior; candidate disambiguation; threshold export for adjudication | BHSA via Text-Fabric, lemma rows | `data/tt/align/<book>.jsonl`, run manifest |
| `tables.py` | Deterministic aggregation: distribution, facets, cross-tab, chi-square, Cramér's V, model-share | in-memory joined rows | plain dicts |
| `witnesses.py` | Witness layer: load readings, produce substitutions for a sigla | `data/tt/witnesses/<book>.jsonl` | substitution map |

Offline scripts in `scripts/`:

- `tt_build_lemmas.py` — Stage A, per book or all.
- `tt_align.py` — Stage B, all books.
- `tt_adjudicate.py` — the only model-calling script: batches of unresolved forms (Stage A step 4) and sub-threshold links (Stage B step 4).
- `tt_eval_gold.py` — gold-sample agreement and aligner precision/recall.

Web layer:

- `blueprints/translation_technique.py` — page route and two JSON endpoints.
- `templates/translation_technique.html`, `templates/tt_gate.html`.
- i18n keys in `data/i18n.json`; sitemap entry in `app.py`; Guide link under "Other Tools"; entry on `/tools`.

Data directory `data/tt/`, committed:

```
data/tt/VERSION
data/tt/sedra_cache.json
data/tt/lemmas/<book>.jsonl
data/tt/lemmas/coverage.json
data/tt/align/<book>.jsonl
data/tt/align/manifest.json
data/tt/witnesses/deuteronomy.jsonl
data/tt/gold/deuteronomy_sample.jsonl
data/tt/gold/eval.json
```

## 5. Data model

All files are JSONL, one object per line, UTF-8, keys in this order.

### 5.1 Lemma row (one per Syriac token)

```
ref         "Deuteronomy 22:4"
position    int, 1-based token index in the verse (matches pesh_etcbc CSV)
form        surface form as in the CSV
norm        form with seyame (U+0308) and diacritic dots (U+0307, U+0323, U+0330, U+0331) removed
lemma       chosen lemma (SEDRA stem string), or null
pos         SEDRA category of the chosen analysis, or null
source      "sedra" | "rule" | "model" | "unresolved"
rule        affix rule id when source == "rule", else null
candidates  list of {lemma, pos, kaylo} from SEDRA for norm (or for the rule-stripped form), may be empty
confidence  1.0 for a single SEDRA candidate; aligner posterior when chosen among candidates; the model's stated figure for source == "model"; 0.0 for unresolved
```

`confidence` for model rows is reported, never used as accuracy.

### 5.2 Alignment row (one per link)

```
ref           "Deuteronomy 22:4"
heb_node      BHSA word node id, or null
heb_lex       BHSA lex (e.g. "JRD["), or null
heb_word      BHSA g_word_utf8, or null
heb_gloss     BHSA lex gloss, or null
heb_feats     {sp, vs, vt, clause_typ, obj_function, next_prep} or null
syr_position  int, or null
syr_lemma     lemma from the lemma row, or null
syr_source    lemma source ("sedra" | "rule" | "model" | "unresolved"), or null
prob          symmetrized link probability, 0–1
kind          "one-one" | "one-many" | "many-one" | "null"
source        "ibm1" | "model"
```

*Hebrew data is denormalized at build time because the web process does not load Text-Fabric.*

A Syriac token with no Hebrew counterpart is written with `heb_node: null`, `heb_lex: null`, `kind: "null"`.

### 5.3 Witness row (one per alternative reading)

```
ref         "Deuteronomy 22:4"
position    int
sigla       "9a1"
form        alternative surface form
lemma       lemma of the alternative (looked up by Stage A rules on demand; may be null)
note        free text
keyed_from  required free text, e.g. "dissertation slide, 2026-10-07"
```

### 5.4 Gold row (one per link in the 200-verse sample)

Same keys as 5.2 minus `prob` and `source`, plus:

```
reader   "jossi" | "model"
agreed   bool, true when both readers produced this link
```

### 5.5 Manifest (`data/tt/align/manifest.json`)

```
version, built_at, corpus_versions {bhsa, pesh_etcbc, lemmas}, iterations, threshold,
books, model_id (for adjudicated links), model_links, total_links, hash
```

`hash` is the SHA-256 of the concatenated align JSONL files and is what the page and exports print.

## 6. Stage A — lemma layer (`scripts/tt_build_lemmas.py`)

Per book, whole OT, idempotent:

1. Normalize each form → `norm`.
2. Look up `norm` in `data/tt/sedra_cache.json`. On a cache miss, call the SEDRA API once (0.3 s between calls), store the full candidate list or `null`. The cache is committed, so rebuilds are offline and reproducible.
3. On `null`, apply affix rules in order and retry the lookup after each: strip proclitic ܘ, then ܕ, then ܠ, then ܒ (also stacked, e.g. ܘܕ); then strip pronominal suffixes (ܗ ܗ̇ ܟ ܟܝ ܢ ܟܘܢ ܟܝܢ ܗܘܢ ܗܝܢ ܝ ܢܝ). A hit is `source: "rule"` with the rule id.
4. Still `null` → listed in `data/tt/lemmas/unresolved.<book>.json` for `tt_adjudicate.py`, which sends batches of 50 forms with their verse to the model and asks for lemma, pos and a confidence. The response is validated (lemma must be Syriac script, pos from the SEDRA category set); invalid items stay unresolved. Accepted rows are `source: "model"`.
5. Write `data/tt/lemmas/<book>.jsonl` and update `coverage.json`: per book, token share and type share by source.

Forms with more than one SEDRA candidate keep `lemma: null` until Stage B chooses.

## 7. Stage B — alignment (`scripts/tt_align.py`)

1. Build the parallel corpus: for each of the 22,889 shared references, Hebrew tokens from BHSA (`lex`, `sp`) and Syriac tokens from the lemma rows. For ambiguous Syriac tokens, the alignment unit is the candidate set. Function words are kept on both sides. The book-name mismatch ("Song of songs") is fixed in the reference normalizer, not in the CSVs.
2. Train IBM Model 1 Hebrew→Syriac and Syriac→Hebrew, 5 EM iterations, pure NumPy, over lemma pairs. For ambiguous Syriac tokens, each candidate lemma contributes with equal prior.
3. Symmetrize: intersection, then grow-diag toward a monotonic position prior (P follows Hebrew word order closely, which the dissertation itself concludes).
4. Candidate disambiguation: for each ambiguous Syriac token, choose the candidate with the highest linked probability; write `lemma`, `pos`, `confidence = posterior` back into the lemma row.
5. Links with `prob < threshold` (initial 0.3; tuned on the gold sample) are exported to `data/tt/align/pending.json` for `tt_adjudicate.py`, which asks the model only "which Syriac token (by position) renders this Hebrew word, or none." Quarantine: a response naming a position outside the verse, or a Hebrew node not in the verse, is rejected, not repaired. Accepted links are `source: "model"`.
6. Write `data/tt/align/<book>.jsonl` and `manifest.json`.

Runtime: Stage A first run is bounded by SEDRA calls (around 60k unique OT forms, a few hours at 0.3 s); afterwards seconds. Stage B is minutes.

## 8. Tables (`translation_technique/tables.py`)

Pure functions over a list of joined rows (`alignment row` + the Hebrew features fetched for `heb_node`). No I/O.

- `distribution(rows, heb_lex, books)` → `[{syr_lemma, count, model_share}]` sorted by count, plus `total`, `null_count` (Hebrew occurrences with no Syriac counterpart), `model_share_total`.
- `facets()` → the available facets and their BHSA source: `vs` (stem), `vt` (tense), `clause_typ` (clause `typ`), `obj_function` (phrase `function` of the first object phrase in the clause, else "none"), `next_prep` (lex of the following preposition in the clause, else "none"), `book`. "Animacy of object" is listed as **not available** with the reason (not in BHSA; a future annotation layer).
- `crosstab(rows, heb_lex, facet, books)` → matrix syr_lemma × facet value, chi-square, degrees of freedom, p, Cramér's V, and `unreliable: true` when any expected cell count < 5.
- `apply_witness(rows, substitutions)` → rows with the token substitutions applied before counting.
- `model_share(rows)` → fraction of rows where lemma `source == "model"` or link `source == "model"`.

## 9. Page and endpoints

Route `GET /translation-technique` (`?lang=es` for Spanish). Blueprint `translation_technique_bp`.

Gate: `tt_gate.html` renders a password field. JS computes SHA-256 of the input with `crypto.subtle.digest` and compares it to a constant hash in the template; on match it sets `sessionStorage.tt_ok = "1"` and reveals the page content (rendered in the same response, hidden). The hash constant is the only thing in the repo. This is obfuscation; the owner has chosen it knowingly.

Page content:

- Hebrew lexeme input, autocomplete over BHSA `lex` attested in the selected books (`GET /api/tt/lexemes?q=&books=`).
- Book multi-select, default Deuteronomy.
- Distribution bar chart with counts and, beneath it, the model share and the null count in words.
- Facet selector → cross-tab table with the statistics; "unreliable" shown as a sentence, never hidden.
- Witness switch listing sigla from the witness file; on selection the tables are recomputed with substitutions and the `keyed_from` note is shown.
- Occurrence list: ref, Hebrew word in context, Syriac word in context, link prob, sources; each row links to a verse view (`GET /translation-technique/verse/<ref>`) that shows both verses with the alignment drawn.
- Export: `GET /api/tt/occurrences.csv?lex=&books=&witness=` with the manifest hash and version in the first comment line.
- Methodology footer: lemma coverage by source for the selected books, alignment manifest hash, gold-sample precision/recall/agreement, or "unevaluated" until `eval.json` exists.

Endpoints:

- `GET /api/tt/table?lex=&books=&facet=&witness=` → JSON of `distribution` and optional `crosstab`.
- `GET /api/tt/lexemes?q=&books=`.

Both are rate-limited like the other read endpoints in `blueprints/api_v1.py` and are not gated.

## 10. Gold sample and evaluation (`scripts/tt_eval_gold.py`)

- 200 Deuteronomy verses, stratified: 6 per chapter for chapters 1–34 (adjusted to reach 200), fixed seed, list committed.
- Two readers: the owner, through a minimal local form (`/translation-technique/gold/<ref>`, local only, writes `gold/deuteronomy_sample.jsonl` with `reader: "jossi"`), and the model, through `tt_adjudicate.py --gold` writing `reader: "model"`.
- `tt_eval_gold.py` computes reader agreement (links present in both), then aligner precision and recall against the agreed subset, and writes `gold/eval.json` with the three figures and the disagreement count. These appear on the page footer.
- The dissertation's published counts (§1) are a second check, run as a test that prints a diff and does not fail the suite; a disagreement is a finding to report.

## 11. Testing

- `tests/test_tt_lemmas.py`: normalization on forms with seyame/dots; affix rules on a fixed list; cache behaviour with a fixture `tests/fixtures/sedra_sample.json` (no network, the API client is injected).
- `tests/test_tt_align.py`: ten-verse toy corpus with hand gold; asserts symmetrized links and candidate disambiguation.
- `tests/test_tt_tables.py`: synthetic joined rows where distribution, cross-tab and chi-square are known by hand; `unreliable` flag; witness substitution; model share.
- `tests/test_integration.py`: route renders, gate template present, both endpoints, i18n keys EN/ES, sitemap entry.
- `tests/test_tt_dissertation_check.py`: compares our Deuteronomy counts for JRD, בוא, נתן with §1, prints the diff, skips if `data/tt/align/deuteronomy.jsonl` is absent.

## 12. Out of scope for version one

- Natural-language query front end (picker first; add later once the query shape is stable).
- Animacy, telicity and other semantic facets (future annotation layer, model-proposed and scholar-validated).
- Apparatus readings beyond the hand-keyed sample.
- Targum Onkelos as a third column (the Root Atlas has the text; alignment would reuse Stage B unchanged).
- Simtho corpus tethering for collocations.
- Ingest of ETCBC synoptic `couple` encodings (if a scholar supplies one, it becomes a second gold source; the ingest is a separate bounded task).

## 13. Open risks

- SEDRA coverage of hapax forms is about half before normalization; if normalization and rules leave more than 10% of Deuteronomy tokens for the model, the page's model share will be visible on every table. That is the design working, not failing, but it will shape how the tool is received.
- SEDRA sometimes tags particles as verbs (ܕܠܐ returned as a verb). Disambiguation by alignment mitigates this; a small override file for known SEDRA quirks may be needed and must be versioned.
- IBM Model 1 on 23k verse pairs is adequate for a translation that follows source word order; it will be weaker on free renderings and idioms (Deut 20:19 type). Those are exactly the cases a scholar wants to see, so low-probability links must stay visible in the occurrence list, not be dropped.
