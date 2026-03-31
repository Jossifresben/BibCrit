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

BibCrit is an open-source, browser-based toolkit for biblical textual criticism that integrates large language model (LLM) analysis with structured corpus data. It provides eight analytical tools covering the principal methods of the discipline: divergence analysis between the Masoretic Text (MT) and the Septuagint (LXX), Hebrew Vorlage reconstruction via back-translation, scribal tendency profiling, numerical discrepancy modelling, Dead Sea Scrolls witness comparison, theological revision detection, patristic citation tracking, and manuscript genealogy visualization. Each tool streams AI-generated analysis in real time via Server-Sent Events (SSE), producing structured scholarly output that includes competing hypotheses, confidence scores, and exportable citations in SBL and BibTeX formats.

The application is built on Flask, uses the Anthropic API (Claude) for analysis, and supports full bilingual operation in English and Spanish. Analysis results are cached in Supabase (with a local JSON fallback), making repeated queries instantaneous and enabling an open data API over the accumulated corpus.

# Statement of Need

Biblical textual criticism requires expertise in Hebrew, Greek, and Aramaic, familiarity with manuscript traditions spanning two millennia, and access to specialist databases that are often paywalled or require desktop software installations [@tov2012; @ulrich2010]. This combination creates a high barrier to entry for students, independent scholars, and researchers from adjacent disciplines (linguistics, history, religious studies) who wish to engage with primary source variation.

Existing digital tools — such as Accordance, Logos, or BibleWorks — provide corpus access but do not perform analytical reasoning across traditions. Conversely, general-purpose AI assistants lack grounding in the specific manuscript witnesses and methodological frameworks of the field. BibCrit bridges this gap by combining structured corpus data (ETCBC morphological database for MT [@etcbc2023], STEP Bible LXX [@stepbible2023]) with LLM analysis explicitly prompted to apply the scholarly frameworks of Tov [@tov2012], Ulrich [@ulrich2010], and Kraft [@kraft2003].

All analysis is transparently streamed, exportable, and released under Apache 2.0, enabling reuse in research workflows. The open cache API allows the growing body of BibCrit analyses to be harvested for downstream computational studies.

# Functionality

## Corpus and Data Layer

BibCrit loads CSV exports of the ETCBC (MT) and STEP Bible (LXX) corpora at startup. The `BiblicalCorpus` class resolves verse references across traditions and returns typed word objects with lemma, morphology, and Strong's number. Books currently profiled include Genesis, Exodus, Numbers, Deuteronomy, Isaiah, Jeremiah, Psalms, Amos, Joel, Micah, and Zechariah.

## Analysis Pipeline

The `ClaudePipeline` class wraps all Claude API calls with:

- **Versioned prompt templates** stored in `data/prompts/`, enabling reproducibility and A/B testing.
- **SHA-256 cache keys** computed from `(reference, tool, prompt_version, model_version)`, ensuring identical queries return cached results without re-incurring API cost.
- **Monthly budget enforcement** (configurable via `BIBCRIT_API_CAP_USD`), preventing runaway spend.
- **Supabase persistence** with transparent disk JSON fallback.

## Analytical Tools

| Tool | Scholarly Method |
|---|---|
| MT/LXX Divergence Analyzer | Word-level classification: `different_vorlage`, `theological_tendency`, `scribal_error`, `translation_technique` [@tov2012] |
| Back-Translation Workbench | Retroversion of LXX → probable Hebrew Vorlage with per-word confidence [@tov1981] |
| Scribal Tendency Profiler | Five-axis radar chart: literalness, anthropomorphism reduction, messianic heightening, harmonization, paraphrase rate [@sollamo1979] |
| Numerical Discrepancy Modeler | MT / LXX / SP numerical divergence with competing theories ranked by confidence |
| DSS Bridge Tool | Manuscript witness alignment across scrolls, MT, and LXX [@ulrich2010] |
| Theological Revision Detector | Detection of theologically motivated alterations [@fishbane1985] |
| Patristic Citation Tracker | Church Father quotation analysis through the 5th century [@kraft2003] |
| Manuscript Genealogy | Stemmatic visualization from proto-text to modern critical editions |

## Streaming Interface

Analysis streams via SSE so progress is visible in real time. The front end renders structured JSON responses progressively, with each section (synthesis, assessment, key divergences, transmission history) appearing as it arrives.

## Internationalization

All UI strings are defined in `data/i18n.json` with English and Spanish translations. The `lang` query parameter selects the active language; AI-generated analysis is translated server-side for the Spanish locale.

# Acknowledgements

Corpus data provided by the ETCBC (Eep Talstra Centre for Bible and Computer, Vrije Universiteit Amsterdam) and STEP Bible (Tyndale House, Cambridge). AI analysis powered by Claude (Anthropic).

# References
