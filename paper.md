---
title: 'BibCrit: An AI-Assisted Web Application for Biblical Textual Criticism'
tags:
  - biblical studies
  - textual criticism
  - Septuagint
  - Dead Sea Scrolls
  - digital humanities
  - large language models
  - Python
  - Flask
authors:
  - name: Jossi Fresco Benaim
    orcid: 0009-0000-2026-0836
    affiliation: 1
affiliations:
  - name: Independent Researcher
    index: 1
date: 2026-03-31
bibliography: paper.bib
---

# Summary

BibCrit is an open-source, browser-based toolkit for biblical textual criticism that integrates large language model (LLM) analysis with structured corpus data. It provides thirteen analytical tools covering the principal methods of the discipline: divergence analysis between the Masoretic Text (MT) and the Septuagint (LXX), Hebrew Vorlage reconstruction via back-translation, scribal tendency profiling, numerical discrepancy modelling, Dead Sea Scrolls witness comparison, theological revision detection, patristic citation tracking, manuscript genealogy visualization, NT use of OT citation-form determination, chiastic and literary structure detection, and documentary source criticism (J/E/D/P). Each tool streams AI-generated analysis in real time via Server-Sent Events (SSE), producing structured scholarly output that includes competing hypotheses, confidence scores, and exportable citations in SBL and BibTeX formats.

The application is built on Flask, uses the Anthropic Claude API for analysis, and supports full bilingual operation in English and Spanish. Analysis results are cached in Supabase (with a local JSON fallback), making repeated queries instantaneous and enabling an open data API over the accumulated corpus.

# Statement of Need

Biblical textual criticism requires expertise in Hebrew, Greek, and Aramaic, familiarity with manuscript traditions spanning two millennia, and access to specialist databases that are often paywalled or require desktop software installations [@tov2012; @ulrich2010]. This combination creates a high barrier to entry for students, independent scholars, and researchers from adjacent disciplines (linguistics, history, religious studies) who wish to engage with primary source variation.

Existing digital tools — such as Accordance, Logos, or BibleWorks — provide corpus access but do not perform analytical reasoning across traditions. Conversely, general-purpose AI assistants lack grounding in the specific manuscript witnesses and methodological frameworks of the field. BibCrit bridges this gap by combining structured corpus data (ETCBC morphological database for MT [@etcbc2023] via Text-Fabric [@hagen2017], STEP Bible LXX [@stepbible2023]) with LLM analysis explicitly prompted to apply the scholarly frameworks of Tov [@tov2012], Ulrich [@ulrich2010], and Kraft [@kraft2009].

All analysis is transparently streamed, exportable, and released under Apache 2.0, enabling reuse in research workflows. The open cache API allows the growing body of BibCrit analyses to be harvested for downstream computational studies.

# State of the Field

The intersection of digital humanities and biblical studies has produced several notable tools. SHEBANQ [@roorda2015] provides a query interface over the BHSA (Biblical Hebrew Syntactic Analysis) database, and Text-Fabric [@hagen2017] offers a Python API for computational access to the ETCBC corpus. These tools excel at corpus querying and morphological analysis but do not generate interpretive scholarly hypotheses.

On the commercial side, Accordance and Logos Biblical Software provide rich manuscript comparison features but are closed, expensive, and produce no machine-readable structured output. The Göttingen Septuaginta critical apparatus and the Dead Sea Scrolls Digital Library offer specialist access to specific corpora but are siloed from one another.

No existing open-source tool integrates manuscript comparison across MT, LXX, DSS, and SP in a single interface, generates structured scholarly analysis grounded in the methods of the field, or exposes results as a cacheable open API. BibCrit is designed to fill this gap, targeting both individual researchers who need rapid first-pass analysis and computational projects that can build on its cached output.

# Software Design

BibCrit follows a three-layer architecture:

**Corpus layer.** The `BiblicalCorpus` class loads CSV exports of eight corpus traditions at startup: ETCBC (MT, all 39 books), Rahlfs LXX (38 books), ETCBC DSS (1QIsaᵃ, 4QSamᵃ, 11QPaleoLev, 4QDeutn), Samaritan Pentateuch (Torah, 5 books), ETCBC Peshitta (Syriac OT, all 39 books, 308,863 word tokens), SBLGNT (NT, 27 books), Targum Onkelos and Targum Jonathan (Aramaic; 26 books, 240,297 word tokens via Sefaria API), and Clementine Vulgate (Latin; 66 books, 569,588 word tokens via scrollmapper/bible_databases). It resolves verse references across traditions and returns typed word objects carrying lemma, morphology, and Strong's identifiers. This layer is entirely deterministic and requires no API calls.

**Analysis layer.** The `ClaudePipeline` class wraps all Claude API calls with versioned prompt templates stored in `data/prompts/{tool}_{version}.txt`. Cache keys are computed as `SHA-256("{reference}|{tool}|{prompt_version}|{model_version}")`, ensuring identical queries return cached results without re-incurring API cost. Results are stored in Supabase with a transparent disk JSON fallback. A monthly budget cap (`BIBCRIT_API_CAP_USD`) prevents runaway spend during public access.

**Presentation layer.** Each analytical endpoint is implemented as a Flask Server-Sent Events (SSE) stream. The front end renders structured JSON responses progressively — each section (synthesis, assessment, key divergences, transmission history) appearing as it arrives. All UI strings are defined in `data/i18n.json` with English and Spanish translations; AI-generated analysis for the Spanish locale is translated server-side and cached separately in `analysis_cache_es`.

The thirteen analytical tools, their scholarly methods, and active prompt versions are summarised in Table 1.

| Tool | Scholarly Method | Prompt |
|---|---|---|
| MT/LXX Divergence Analyzer | Word-level classification: `different_vorlage`, `theological_tendency`, `scribal_error`, `translation_technique` [@tov2012] | v2 |
| Back-Translation Workbench | Retroversion of LXX → probable Hebrew Vorlage with per-word confidence [@tov1981] | v1 |
| Scribal Tendency Profiler | Five-axis radar chart: literalness, anthropomorphism reduction, messianic heightening, harmonization, paraphrase rate [@sollamo1979] | v1 |
| Numerical Discrepancy Modeler | MT / LXX / SP numerical divergence with competing theories ranked by confidence | v3 |
| Ancient Witness Bridge | DSS manuscript witness alignment across scrolls, Samaritan Pentateuch, Peshitta, MT, and LXX [@ulrich2010] | v7 |
| Theological Revision Detector | Detection of theologically motivated alterations [@fishbane1985] | v2 |
| Patristic Citation Tracker | Church Father quotation analysis through the 5th century with text-form distribution [@kraft2009] | v3 |
| Manuscript Genealogy | Stemmatic visualization from proto-text to modern critical editions | v1 |
| NT Use of OT Analyzer | Identification of OT allusions in NT passages with MT/LXX citation-form determination [@beale2007; @stanley1992; @hays1989] | v1 |
| Chiasm & Literary Structure Detector | Detection of concentric structures (A-B-C-B′-A′), parallel panels, inclusios, and refrains [@lund1942; @welch1981; @dorsey1999] | v1 |
| Source Criticism Tool | Documentary source attribution (J, E, D, P, Redactor) via divine name usage, vocabulary patterns, doublets, and narrative tensions [@wellhausen1883; @friedman1987; @baden2012] | v1 |
| Targum Comparator | Targumic rendering analysis: Memra, anthropomorphism avoidance, messianic reinterpretation, targumic expansions [@samely1992; @smelik1995] | v1 |
| NT Textual Tradition Analyzer | Manuscript family attestation (Alexandrian, Western, Byzantine, Caesarean), Metzger A/B/C/D confidence ratings, variant register [@metzger1994] | v1 |

Table: BibCrit analytical tools with scholarly grounding and current prompt versions.

# Research Impact Statement

BibCrit lowers the barrier to entry for several research activities that previously required specialist software and deep palaeographic training. A graduate student can now obtain a structured comparison of MT and LXX readings for a contested passage in seconds, with competing scholarly explanations ranked by confidence — work that previously required consulting Tov's apparatus [@tov2012] alongside the Göttingen critical edition. The scribal tendency profiler makes it possible to compare the translation styles of different LXX books quantitatively without writing custom corpus queries. The patristic citation tracker surfaces text-form evidence from the Church Fathers that is otherwise scattered across the Migne Patrologia and specialist monographs.

The accumulated analysis cache — covering featured passages across all thirteen tools in both English and Spanish — constitutes an open dataset that can be harvested for downstream computational studies. The cache API (`/api/{tool}/stream?ref=...&lang=en`) is openly accessible, enabling integration into research pipelines without direct interaction with the web interface.

Bilingual operation (English and Spanish) makes the tool accessible to the significant body of biblical scholarship published in Spanish, particularly in Latin American and Iberian academic contexts.

# AI Usage Disclosure

BibCrit uses the Anthropic Claude API (`claude-sonnet-4-5`) to generate analytical content for each of its thirteen tools. The AI is not used for corpus ingestion, cache management, or any deterministic processing steps. All AI-generated analysis is clearly attributed as such in the user interface, and users are informed that results should be verified against primary sources.

The prompt templates in `data/prompts/` are scholarly-grounded, specifying the methodological frameworks of Tov, Metzger, Hengel, and the Göttingen LXX critical apparatus explicitly. Output schemas are versioned and pinned to specific model versions to ensure reproducibility. A monthly budget cap prevents the tool from making unbounded API calls during public access.

This paper was written by the author. Claude was not used to draft or edit the paper.md text.

# Functionality

## Corpus and Data Layer

BibCrit loads CSV exports of eight corpus traditions at startup. The `BiblicalCorpus` class resolves verse references across traditions and returns typed word objects with lemma, morphology, and Strong's number. Full OT coverage is provided for MT (39 books), LXX (38 books), and Peshitta (39 books, 308,863 Syriac word tokens via ETCBC/peshitta). DSS coverage spans four scrolls: 1QIsaᵃ (Isaiah 1–66), 4QSamᵃ (Samuel fragments), 11QPaleoLev (Leviticus), and 4QDeutn (Deuteronomy fragments). The Samaritan Pentateuch covers the Torah (5 books), and the SBLGNT provides NT Greek (27 books). Targum Onkelos and Targum Jonathan cover the Aramaic tradition (26 books, 240,297 word tokens via Sefaria API), and the Clementine Vulgate provides Latin coverage across the full canon (66 books, 569,588 word tokens via scrollmapper/bible_databases).

## Streaming Interface

Analysis streams via SSE so progress is visible in real time, with step-by-step indicators ("Checking cache…", "Analyzing…") displayed during generation. When results arrive, structured sections are revealed in sequence via staggered CSS animations — synthesis first, then key divergences, transmission history, and the BibCrit assessment — so the page populates incrementally rather than appearing all at once.

## Internationalization

All UI strings are defined in `data/i18n.json` with English and Spanish translations. The `lang` query parameter selects the active language; AI-generated analysis is translated server-side for the Spanish locale and cached separately.

# Acknowledgements

Corpus data provided by the ETCBC (Eep Talstra Centre for Bible and Computer, Vrije Universiteit Amsterdam) under CC-BY-NC 4.0, and STEP Bible (Tyndale House, Cambridge). AI analysis powered by Claude (Anthropic).

# References
