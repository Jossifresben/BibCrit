# BibCrit 6-Month Development Roadmap
**Date:** 2026-04-14
**Author:** Jossi Fresco
**Strategic direction:** Research Depth — become the scholarly gold standard for open AI-assisted biblical textual criticism

---

## Context

BibCrit v2.2 ships with 9 analysis tools, 5 live corpora (MT, LXX, DSS 1QIsaᵃ, SP, GNT), bilingual UI (EN + ES), and a fully cached open data API. The next 6 months expand BibCrit from a strong tool suite into a comprehensive platform that covers manuscript traditions and analytical methods found nowhere else in open digital humanities tooling.

### Gap analysis summary

A systematic review of existing tools — Accordance, Logos, SHEBANQ/Text-Fabric, BiblIndex, and the DSS Digital Library — reveals the following:

| Category | Finding |
|---|---|
| AI analysis with scholarly methodology | BibCrit is the only tool of any kind (open or paywalled) |
| Hebrew Vorlage reconstruction | BibCrit is the only tool |
| Scribal tendency profiling | BibCrit is the only tool |
| NT Use of OT citation-form determination | BibCrit is the only tool |
| Chiasm / literary structure detection | **No tool exists anywhere** |
| Source criticism (J/E/D/P) with AI reasoning | **No tool exists anywhere** |
| Targum theological analysis | AI analysis absent everywhere; data paywalled in Accordance/Logos |
| Second Temple literature bridge | **No tool exists anywhere** |
| Intertextuality mapper (unified allusion graph) | **No tool exists anywhere** |
| Free, open access | BibCrit and SHEBANQ/TF only |

Accordance and Logos cost $300–$1,000+ and provide corpus access without analytical reasoning. BibCrit's structural advantage — combining structured corpus data with LLM analysis grounded in explicit scholarly methodology — cannot be replicated by corpus-only tools.

---

## Phase 1 — Months 1–2: Foundation

**Goal:** Strengthen existing tools with more corpus data; launch the first two first-in-world open analysis tools.

### Corpus additions

#### Peshitta real corpus data
- **What:** Replace AI-only Peshitta in Ancient Witness Bridge with actual corpus files from the Leiden Peshitta / CAL
- **Source:** Comprehensive Aramaic Lexicon (cal.huc.edu) or ETCBC Peshitta module
- **Path:** `data/corpora/pesh_etcbc/` (already registered in `corpus.py`)
- **Code impact:** Zero — corpus.py auto-loads any CSV in the directory
- **Scholarly value:** Transforms DSS Bridge from "AI knowledge" to data-backed Syriac comparison

#### MT/LXX expansion — Jeremiah, Samuel, full Psalms
- **What:** Add CSV exports for books with the most text-critical interest
- **Jeremiah:** LXX is 1/8 shorter than MT with chapters 46–51 in different order — the single most dramatic MT/LXX divergence
- **1–2 Samuel:** 4QSamᵃ aligns with LXX against MT in key passages; critical for three-tradition comparison
- **Psalms (full):** Psalms 22, 51, 110 are essential for patristic and messianic analysis
- **Code impact:** None — all 9 tools immediately work on new books

#### Extended DSS witnesses
- **What:** Add 4QSamᵃ, 11QPaleoLev, 1QpHab, 4QDeutᵏ as additional CSVs in `data/corpora/dss/`
- **Source:** ETCBC DSS module (DJD-series aligned)
- **Code impact:** None — DSS Bridge loads all files in the directory

### New tools

#### Chiasm and Literary Structure Detector
- **Route:** `/chiasm`
- **Method:** Lund (1942), Welch (1981), Dorsey (1999), Walsh (2001) concentric structure methodology
- **Input:** Any biblical passage or book
- **Output:** Detected structural units with labels (A, B, C, pivot, B′, A′), supporting textual evidence, confidence score per unit, synthesis of theological significance
- **Corpus dependency:** None — pure AI analysis
- **Prompt:** `chiasm_v1`
- **Why unique:** Zero open tools detect this computationally; currently requires manual consultation of multiple commentaries
- **Primary targets:** Genesis (1–11, 37–50), Isaiah (1–12, 40–55), Psalms (1–89), Amos, Ruth

#### Source Criticism Tool (J/E/D/P)
- **Route:** `/source`
- **Method:** Wellhausen (1878), Friedman (1987, 2003), Baden (2012); supports Classic Documentary, Supplementary, and Neo-Documentary frameworks
- **Input:** Any Pentateuchal passage; optionally select analytical framework
- **Output:** Source attribution with evidence (divine names, vocabulary, theological concerns, doublets), confidence per unit, competing scholarly positions, synthesis
- **Corpus dependency:** None — MT text from existing corpus; pure AI reasoning
- **Prompt:** `source_v1`
- **Why unique:** No digital tool of any kind offers this for non-specialists; even paywalled tools (Accordance, Logos) do not perform source-critical analysis
- **Scope note:** Presented as analytical evidence, not definitive assignment; scholarly debate is surfaced

### Infrastructure

- **Deploy v2.3:** Push staggered reveal, code review fixes, guide stats, paper.md accuracy update
- **Pre-seed NT Use of OT cache:** Run `precache_all.py --type nt_ot` for 9 featured passages

---

## Phase 2 — Months 3–4: New Traditions

**Goal:** Add Targum and Vulgate as live corpus traditions; launch two more new tools; begin Hebrew RTL and true token streaming.

### Corpus additions

#### Targum corpus (Onkelos + Jonathan)
- **What:** Aramaic Targumim for Torah (Onkelos) and Prophets (Targum Jonathan)
- **Source:** CAL (cal.huc.edu) Targum module or ETCBC Aramaic datasets
- **Path:** `data/corpora/targum_cal/`
- **Schema:** Same CSV format; `tradition = "TARG"`, `manuscript = "Onkelos"` / `"Jonathan"`
- **Code impact:** Add `'TARG': 'targum_cal'` to `_TRADITION_DIRS` in `corpus.py`

#### Vulgate corpus (Jerome)
- **What:** Latin Vulgate OT + NT
- **Source:** CLTK (Classical Language Toolkit) or Open Scriptures Vulgate
- **Path:** `data/corpora/vulgate_cltk/`
- **Schema:** Same CSV format; `tradition = "VUL"`, `manuscript = "Vulgate"`
- **Code impact:** Add `'VUL': 'vulgate_cltk'` to `_TRADITION_DIRS`

#### LXX manuscript variants (Sinaiticus, Alexandrinus)
- **What:** Add Sinaiticus and Alexandrinus alongside Vaticanus in the LXX tradition
- **Source:** STEP Bible (same source as current LXX data)
- **Implementation:** Additional rows in `lxx_stepbible/` with `manuscript = "Sinaiticus"` / `"Alexandrinus"` column
- **Unlocks:** Three-way LXX manuscript comparison in Divergence Analyzer and DSS Bridge

### New tools

#### Targum Comparator
- **Route:** `/targum`
- **Method:** Sperber critical edition; Samely (1992), McNamara (1994), Chilton (1987)
- **Input:** Any Torah (Onkelos) or Prophets (Jonathan) passage
- **Output:** MT vs. Targum word-level comparison; expansion types classified (theological, halakhic, messianic, divine-name substitution [Memra/Shekhina], haggadic); overall paraphrase profile
- **Corpus dependency:** Targum corpus (Phase 2)
- **Prompt:** `targum_v1`
- **Why unique:** Paywalled in Accordance/Logos; no AI analysis exists anywhere

#### NT Textual Tradition Analyzer
- **Route:** `/nt-text`
- **Method:** Metzger (1994) UBS apparatus; Aland text-type classification; Byzantine, Alexandrian, Western family profiles
- **Input:** Any NT passage
- **Output:** Key manuscript variants with text-type attribution, external evidence summary, transcriptional probability, intrinsic probability, UBS confidence grade, synthesis
- **Corpus dependency:** GNT (already live); UBS variant data via AI training knowledge
- **Prompt:** `nt_text_v1`
- **Why unique:** UBS/NA28 apparatus data is paywalled; no AI analysis exists anywhere

### Infrastructure

#### Hebrew RTL UI
- Add `he` locale to `data/i18n.json`
- Wire `dir="rtl"` and RTL CSS in `base.html` when `lang=he`
- Translate all UI strings (analysis output remains AI-generated Hebrew via translation pipeline)
- Makes BibCrit usable by Hebrew-speaking Israeli biblical scholars

#### True Anthropic token streaming
- Replace `messages.create()` with `messages.stream()` across all pipeline methods
- Emit `section` SSE events as each JSON key completes
- Frontend renders sections as they arrive — 10–20s earlier on first-time queries
- See `docs/superpowers/plans/prancy-rolling-quiche.md` § "Nice-to-Have: True Streaming" for full spec

---

## Phase 3 — Months 5–6: Synthesis

**Goal:** Capstone tools that require all prior corpora; platform maturity; multilingual expansion; JOSS v3 submission.

### Corpus additions

#### Second Temple literature
- **What:** 1 Enoch, Jubilees, Sirach (Ben Sira), 4 Ezra, Tobit
- **Source:** CLTK / Open Scriptures / NETS (New English Translation of the Septuagint)
- **Path:** `data/corpora/stl_cltk/`
- **Code impact:** Add `'STL': 'stl_cltk'` to `_TRADITION_DIRS`
- **Why:** Critical for DSS context; many DSS theological concerns mirror 1 Enoch and Jubilees; essential for intertextuality mapper

#### Peshitta NT
- **What:** Syriac NT (Peshitta — Aramaic Primacy tradition)
- **Source:** ETCBC Peshitta NT / CAL
- **Path:** Additional CSVs in `pesh_etcbc/` with NT books
- **Unlocks:** Third NT tradition alongside SBLGNT for NT Use of OT and NT Textual Tradition tools

### New tools

#### Second Temple Literature Bridge
- **Route:** `/stl`
- **Method:** Nickelsburg (2001), VanderKam (2010), Collins (1998); allusion classification methodology from Beale & Carson adapted for Second Temple texts
- **Input:** Any canonical OT or NT passage
- **Output:** Allusions and citations in 1 Enoch, Jubilees, Sirach, 4 Ezra; directionality assessment (does STL cite canon, or does canon reflect STL?); significance for DSS and NT interpretation
- **Corpus dependency:** STL corpus (Phase 3)
- **Prompt:** `stl_v1`
- **Why unique:** No open tool covers cross-corpus Second Temple relationships

#### Intertextuality Mapper
- **Route:** `/intertextuality`
- **Method:** Hays (1989) echo criteria; Beale (1998) allusion taxonomy; inner-biblical allusion methodology (Fishbane 1985)
- **Input:** Any passage
- **Output:** Full allusion network graph — inner-biblical allusions, NT echoes, patristic citations, DSS parallels, Second Temple literature parallels; each link typed and scored; exportable as JSON-LD / RDF
- **Corpus dependency:** All corpora from Phases 1–3 (this is the capstone tool)
- **Prompt:** `intertextuality_v1`
- **Why unique:** Currently requires consulting 4+ separate tools and databases manually; no unified view exists anywhere

### Infrastructure

#### Full open API v1
- Versioned endpoints (`/api/v1/...`)
- API key management and rate limiting
- Swagger / OpenAPI documentation at `/api/docs`
- Enables seminaries and journals to embed BibCrit tool results directly

#### Dutch and Portuguese UI
- Add `nl` and `pt` locales to `data/i18n.json`
- Significant biblical scholarship communities: Netherlands (VU Amsterdam, Leiden) and Brazil/Portugal

#### JOSS paper v3 + DOI update
- Update `paper.md` to reflect 15 tools and 8 corpus traditions
- Submit updated JOSS paper
- Tag v3.0, create Zenodo DOI update

---

## Dependency graph

```
Phase 1 corpora → Phase 2 Targum Comparator (needs Targum corpus)
Phase 3 STL corpus → Phase 3 STL Bridge tool
All Phase 1–3 corpora → Phase 3 Intertextuality Mapper (capstone)
Phase 2 GNT (already live) → NT Textual Tradition Analyzer (no new corpus needed)
Chiasm Detector, Source Criticism → No corpus dependency (can start any time)
True streaming → Independent of all corpus work (parallel track)
```

---

## End state: BibCrit v3.0 (6 months)

| Metric | Now | +6 months |
|---|---|---|
| Analysis tools | 9 | 15 |
| Corpus traditions | 5 (MT, LXX, DSS, SP, GNT) | 9 (+ Peshitta, Targum, Vulgate, STL) |
| UI languages | 2 (EN, ES) | 5 (+ HE, NL, PT) |
| First-in-world open tools | 5 | 11 |
| Open analysis cache entries | ~141 | ~500+ |

---

## Success criteria

- Every new tool returns rich, structured analysis with confidence scores and competing hypotheses
- Every new corpus tradition loads automatically via `BiblicalCorpus` with no architectural changes
- All 15 tools have featured passages pre-cached (instant load)
- Intertextuality Mapper surfaces allusion networks spanning at least 3 traditions per passage
- JOSS paper accepted citing 15 tools and 9 corpus traditions
- BibCrit is the top Google result for "open biblical textual criticism tool"
