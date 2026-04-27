"""Research blueprint — concordance, hapax, collocations."""

import os
import re
import markdown as _md

from flask import Blueprint, jsonify, render_template, request
import state

# ── OpenAPI 3.0 spec ──────────────────────────────────────────────────────────

_OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "BibCrit API",
        "version": "1.0.0",
        "description": (
            "BibCrit is an open-source AI-assisted toolkit for biblical textual criticism. "
            "This API provides access to thirteen AI analysis tools (MT/LXX divergence, "
            "back-translation, DSS witness comparison, scribal tendency profiling, and more), "
            "a structured corpus browser over eight manuscript traditions, and an open cache "
            "of all previously generated analyses.\n\n"
            "Analysis endpoints stream results via **Server-Sent Events (SSE)** — connect "
            "with `EventSource` or `curl --no-buffer`. Cached results return in milliseconds; "
            "new analyses take 30–90 s.\n\n"
            "Apache 2.0 · DOI: https://doi.org/10.5281/zenodo.19358424"
        ),
        "contact": {
            "name": "Jossi Fresco Benaim",
            "url": "https://orcid.org/0009-0000-2026-0836",
            "email": "jossif@gmail.com",
        },
        "license": {
            "name": "Apache 2.0",
            "url": "https://www.apache.org/licenses/LICENSE-2.0",
        },
        "x-doi": "10.5281/zenodo.19358424",
    },
    "servers": [
        {"url": "https://bibcrit.app", "description": "Production"},
        {"url": "http://localhost:5001", "description": "Local development"},
    ],
    "tags": [
        {"name": "Analysis", "description": "AI-powered SSE stream analysis tools. Each endpoint streams Server-Sent Events. Connect with EventSource or `curl --no-buffer`. Cached results return instantly; new analyses take 30–90 s."},
        {"name": "Corpus", "description": "Browse the eight manuscript traditions loaded at startup (MT, LXX, DSS, SP, PESH, GNT, Targum, Vulgate)."},
        {"name": "Cache", "description": "Query the accumulated open dataset of all previously generated analyses."},
        {"name": "Export", "description": "Export citations in SBL footnote, BibTeX, RIS, or TEI XML format."},
        {"name": "Votes", "description": "Community quality votes on analysis results and individual hypotheses."},
        {"name": "System", "description": "Health check and API budget monitoring."},
    ],
    "paths": {
        # ── Analysis stream endpoints ────────────────────────────────────────
        "/api/divergence/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "MT/LXX Divergence Analyzer",
                "description": "Word-level divergence classification between the Masoretic Text and Septuagint (different_vorlage, theological_tendency, scribal_error, translation_technique). Based on Tov (2012) methodology.",
                "operationId": "streamDivergence",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Verse reference (e.g. `Isaiah 7:14`, `Genesis 3:15`)"},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}, "description": "Response language"},
                ],
                "responses": {
                    "200": {
                        "description": "Server-Sent Event stream. Events: `step` (progress), `done` (JSON result), `error`.",
                        "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}},
                    }
                },
            }
        },
        "/api/backtranslation/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Back-Translation Workbench",
                "description": "Retroversion of the Septuagint into its probable Hebrew Vorlage, with per-word confidence ratings. Based on Tov (1981).",
                "operationId": "streamBacktranslation",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Verse reference"},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/dss/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Ancient Witness Bridge",
                "description": "Cross-tradition alignment across Dead Sea Scrolls (1QIsaᵃ, 4QSamᵃ, 11QPaleoLev, 4QDeutⁿ), Samaritan Pentateuch, Peshitta, MT, and LXX. Based on Ulrich (2010).",
                "operationId": "streamDSS",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/genealogy/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Manuscript Genealogy",
                "description": "Stemmatic visualization from proto-text through recensions to modern critical editions.",
                "operationId": "streamGenealogy",
                "parameters": [
                    {"name": "book", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Biblical book name (e.g. `Isaiah`, `Genesis`)"},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/nt-ot/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "NT Use of OT Analyzer",
                "description": "Identifies OT allusions and quotations within NT passages, determining whether the citation follows the MT or LXX text-form. Based on Beale & Carson (2007), Stanley (1992), Hays (1989).",
                "operationId": "streamNtOt",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}, "description": "NT verse reference (e.g. `Matthew 4:15-16`)"},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/scribal/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Scribal Tendency Profiler",
                "description": "Five-axis radar chart analysis: literalness, anthropomorphism reduction, messianic heightening, harmonization, paraphrase rate. Based on Sollamo (1979).",
                "operationId": "streamScribal",
                "parameters": [
                    {"name": "book", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Biblical book name"},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/numerical/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Numerical Discrepancy Modeler",
                "description": "Models numerical divergences between MT, LXX, and SP (patriarchal ages, census figures, temple dimensions, military counts). Competing theories ranked by plausibility.",
                "operationId": "streamNumerical",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/theological/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Theological Revision Detector",
                "description": "Detects theologically motivated alterations across manuscript traditions. Based on Fishbane (1985).",
                "operationId": "streamTheological",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/patristic/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Patristic Citation Tracker",
                "description": "Tracks Church Father quotations of a passage through the 5th century, with text-form distribution across MT, LXX, and other traditions. Based on Kraft (2009).",
                "operationId": "streamPatristic",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/chiasm/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Chiasm & Literary Structure Detector",
                "description": "Detects concentric structures (A-B-C-Bʹ-Aʹ), parallel panels, inclusios, and refrains. Based on Lund (1942), Welch (1981), Dorsey (1999).",
                "operationId": "streamChiasm",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/source/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Documentary Source Criticism",
                "description": "Attributes Pentateuchal passages to J, E, D, P, or Redactor via divine name usage, vocabulary patterns, doublets, and narrative tensions. Based on Wellhausen (1883), Friedman (1987), Baden (2012).",
                "operationId": "streamSource",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/targum/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "Targum Comparator",
                "description": "Analyzes Targumic renderings: Memra, anthropomorphism avoidance, messianic reinterpretation, and targumic expansions. Covers Onkelos (Torah) and Jonathan (Prophets). Based on Samely (1992), Smelik (1995).",
                "operationId": "streamTargum",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        "/api/nt-text/stream": {
            "get": {
                "tags": ["Analysis"],
                "summary": "NT Textual Tradition Analyzer",
                "description": "Manuscript family attestation for NT passages (Alexandrian, Western, Byzantine, Caesarean), Metzger A/B/C/D confidence ratings, and variant register. Based on Metzger (1994).",
                "operationId": "streamNtText",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}, "description": "NT verse reference"},
                    {"name": "lang", "in": "query", "schema": {"type": "string", "enum": ["en", "es"], "default": "en"}},
                ],
                "responses": {"200": {"description": "SSE stream", "content": {"text/event-stream": {"schema": {"$ref": "#/components/schemas/SSEStream"}}}}},
            }
        },
        # ── Corpus browser ───────────────────────────────────────────────────
        "/api/books": {
            "get": {
                "tags": ["Corpus"],
                "summary": "List books in a tradition",
                "description": "Returns all biblical books available for a given manuscript tradition.",
                "operationId": "listBooks",
                "parameters": [
                    {"name": "tradition", "in": "query", "required": True, "schema": {"type": "string", "enum": ["MT", "LXX", "DSS", "SP", "PESH", "GNT", "TARGUM", "VULGATE"]}, "description": "Manuscript tradition"},
                ],
                "responses": {
                    "200": {
                        "description": "List of book names",
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"books": {"type": "array", "items": {"type": "string"}}}}}},
                    }
                },
            }
        },
        "/api/chapters": {
            "get": {
                "tags": ["Corpus"],
                "summary": "List chapters for a book",
                "description": "Returns all chapter numbers available for a book in a given tradition.",
                "operationId": "listChapters",
                "parameters": [
                    {"name": "book", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "tradition", "in": "query", "required": True, "schema": {"type": "string", "enum": ["MT", "LXX", "DSS", "SP", "PESH", "GNT", "TARGUM", "VULGATE"]}},
                ],
                "responses": {
                    "200": {
                        "description": "Chapter list",
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"chapters": {"type": "array", "items": {"type": "integer"}}}}}},
                    }
                },
            }
        },
        "/api/verses": {
            "get": {
                "tags": ["Corpus"],
                "summary": "Get verse text",
                "description": "Returns morphological word objects for a verse reference and tradition.",
                "operationId": "getVerses",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}, "description": "Verse reference (e.g. `Isaiah 7:14`)"},
                    {"name": "tradition", "in": "query", "required": True, "schema": {"type": "string", "enum": ["MT", "LXX", "DSS", "SP", "PESH", "GNT", "TARGUM", "VULGATE"]}},
                ],
                "responses": {
                    "200": {
                        "description": "Word-level verse data",
                        "content": {"application/json": {"schema": {"type": "object", "properties": {
                            "reference": {"type": "string"},
                            "tradition": {"type": "string"},
                            "words": {"type": "array", "items": {"$ref": "#/components/schemas/CorpusWord"}},
                        }}}},
                    }
                },
            }
        },
        # ── Cache / discovery ────────────────────────────────────────────────
        "/api/cache": {
            "get": {
                "tags": ["Cache"],
                "summary": "Browse cached analyses",
                "description": "Returns paginated cached analysis records. The accumulated cache is an open dataset — every result ever generated is freely accessible here.",
                "operationId": "getCache",
                "parameters": [
                    {"name": "tool", "in": "query", "schema": {"type": "string"}, "description": "Filter by tool name (e.g. `divergence`, `patristic`)"},
                    {"name": "ref", "in": "query", "schema": {"type": "string"}, "description": "Substring match on reference (e.g. `Isaiah`)"},
                    {"name": "discovery_ready", "in": "query", "schema": {"type": "boolean"}, "description": "Only return discovery-ready passages"},
                    {"name": "limit", "in": "query", "schema": {"type": "integer", "default": 50, "maximum": 200}},
                    {"name": "offset", "in": "query", "schema": {"type": "integer", "default": 0}},
                ],
                "responses": {
                    "200": {
                        "description": "Paginated cache records",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/CacheResponse"}}},
                    }
                },
            }
        },
        "/api/discovery/cards": {
            "get": {
                "tags": ["Cache"],
                "summary": "Discovery feed cards",
                "description": "Returns a curated set of discovery-ready analysis cards for the Discovery feed.",
                "operationId": "getDiscoveryCards",
                "responses": {
                    "200": {
                        "description": "Discovery card array",
                        "content": {"application/json": {"schema": {"type": "object", "properties": {"cards": {"type": "array", "items": {"$ref": "#/components/schemas/DiscoveryCard"}}}}}},
                    }
                },
            }
        },
        # ── Export ───────────────────────────────────────────────────────────
        "/api/export/sbl": {
            "get": {
                "tags": ["Export"],
                "summary": "SBL footnote (generic)",
                "description": "Generates a formatted SBL-style footnote citation for any tool and reference.",
                "operationId": "exportSbl",
                "parameters": [
                    {"name": "ref", "in": "query", "schema": {"type": "string"}, "description": "Verse reference (use `ref` for verse tools)"},
                    {"name": "book", "in": "query", "schema": {"type": "string"}, "description": "Book name (use `book` for book-level tools)"},
                    {"name": "tool", "in": "query", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "SBL footnote string", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SblResponse"}}}}},
            }
        },
        "/api/export/bibtex": {
            "get": {
                "tags": ["Export"],
                "summary": "BibTeX entry (generic)",
                "description": "Generates a BibTeX @misc entry for any tool and reference.",
                "operationId": "exportBibtex",
                "parameters": [
                    {"name": "ref", "in": "query", "schema": {"type": "string"}},
                    {"name": "book", "in": "query", "schema": {"type": "string"}},
                    {"name": "tool", "in": "query", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "BibTeX entry", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BibtexResponse"}}}}},
            }
        },
        "/api/divergence/export/sbl": {
            "get": {
                "tags": ["Export"],
                "summary": "SBL footnote (Divergence)",
                "description": "Structured SBL citation for a divergence analysis result.",
                "operationId": "exportDivergenceSbl",
                "parameters": [{"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "SBL footnote", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SblResponse"}}}}},
            }
        },
        "/api/divergence/export/bibtex": {
            "get": {
                "tags": ["Export"],
                "summary": "BibTeX (Divergence)",
                "operationId": "exportDivergenceBibtex",
                "tags_": ["Export"],
                "parameters": [{"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "BibTeX entry", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/BibtexResponse"}}}}},
            }
        },
        "/api/divergence/export/ris": {
            "get": {
                "tags": ["Export"],
                "summary": "RIS entry (Divergence)",
                "operationId": "exportDivergenceRis",
                "parameters": [{"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "RIS entry", "content": {"application/json": {"schema": {"type": "object", "properties": {"ris": {"type": "string"}}}}}}},
            }
        },
        "/api/divergence/export/tei": {
            "get": {
                "tags": ["Export"],
                "summary": "TEI XML (Divergence)",
                "operationId": "exportDivergenceTei",
                "parameters": [{"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}}],
                "responses": {"200": {"description": "TEI XML snippet", "content": {"application/json": {"schema": {"type": "object", "properties": {"tei": {"type": "string"}}}}}}},
            }
        },
        # ── Votes ────────────────────────────────────────────────────────────
        "/api/vote": {
            "post": {
                "tags": ["Votes"],
                "summary": "Submit quality vote",
                "description": "Record an upvote (+1), downvote (-1), or removal (0) for an analysis result.",
                "operationId": "submitVote",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/VoteRequest"}}},
                },
                "responses": {"200": {"description": "Vote recorded", "content": {"application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}}}}},
            }
        },
        "/api/votes": {
            "get": {
                "tags": ["Votes"],
                "summary": "Get quality vote counts",
                "operationId": "getVotes",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "tool", "in": "query", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "Vote counts", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/VoteResponse"}}}}},
            }
        },
        "/api/hypothesis/vote": {
            "post": {
                "tags": ["Votes"],
                "summary": "Submit hypothesis vote",
                "description": "Vote on a specific scholarly hypothesis within an analysis result.",
                "operationId": "submitHypothesisVote",
                "requestBody": {
                    "required": True,
                    "content": {"application/json": {"schema": {"$ref": "#/components/schemas/HypothesisVoteRequest"}}},
                },
                "responses": {"200": {"description": "Vote recorded", "content": {"application/json": {"schema": {"type": "object", "properties": {"ok": {"type": "boolean"}}}}}}},
            }
        },
        "/api/hypothesis/votes": {
            "get": {
                "tags": ["Votes"],
                "summary": "Get hypothesis vote counts",
                "operationId": "getHypothesisVotes",
                "parameters": [
                    {"name": "ref", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "tool", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "hypothesis_id", "in": "query", "required": True, "schema": {"type": "string"}},
                ],
                "responses": {"200": {"description": "Hypothesis vote counts", "content": {"application/json": {"schema": {"$ref": "#/components/schemas/VoteResponse"}}}}},
            }
        },
        # ── System ───────────────────────────────────────────────────────────
        "/api/budget": {
            "get": {
                "tags": ["System"],
                "summary": "API budget status",
                "description": "Returns current Claude API spend against the monthly cap.",
                "operationId": "getBudget",
                "responses": {
                    "200": {
                        "description": "Budget status",
                        "content": {"application/json": {"schema": {"type": "object", "properties": {
                            "spend_usd": {"type": "number"},
                            "cap_usd": {"type": "number"},
                            "pct": {"type": "number"},
                        }}}},
                    }
                },
            }
        },
        "/health": {
            "get": {
                "tags": ["System"],
                "summary": "Health check",
                "operationId": "healthCheck",
                "responses": {"200": {"description": "Service healthy", "content": {"application/json": {"schema": {"type": "object", "properties": {"status": {"type": "string"}, "app": {"type": "string"}}}}}}},
            }
        },
    },
    "components": {
        "schemas": {
            "SSEStream": {
                "type": "string",
                "description": (
                    "Server-Sent Events stream. Each event is `data: <JSON>\\n\\n`.\n\n"
                    "Event types:\n"
                    "- `step` — `{type: 'step', message: string}` — progress update\n"
                    "- `done` — `{type: 'done', result: AnalysisResult}` — complete analysis\n"
                    "- `error` — `{type: 'error', message: string}` — analysis failed\n\n"
                    "Example (curl): `curl -N 'https://bibcrit.app/api/divergence/stream?ref=Isaiah+7:14'`"
                ),
            },
            "AnalysisResult": {
                "type": "object",
                "description": "Structured scholarly analysis object. Fields vary by tool; common fields below.",
                "properties": {
                    "synthesis": {"type": "string", "description": "Narrative synthesis of the analysis"},
                    "assessment": {"type": "string", "description": "BibCrit confidence assessment"},
                    "key_divergences": {"type": "array", "items": {"type": "object"}},
                    "transmission_history": {"type": "string"},
                    "competing_hypotheses": {"type": "array", "items": {"type": "object", "properties": {
                        "hypothesis": {"type": "string"},
                        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    }}},
                    "mt_text": {"type": "string", "description": "Masoretic Text of the passage (corpus-sourced)"},
                    "lxx_text": {"type": "string", "description": "Septuagint text of the passage (corpus-sourced)"},
                    "cached": {"type": "boolean"},
                    "model_version": {"type": "string"},
                    "prompt_version": {"type": "string"},
                },
            },
            "CorpusWord": {
                "type": "object",
                "properties": {
                    "word_text": {"type": "string"},
                    "lemma": {"type": "string"},
                    "morph": {"type": "string"},
                    "strong": {"type": "string"},
                    "position": {"type": "integer"},
                    "manuscript": {"type": "string"},
                    "tradition": {"type": "string"},
                },
            },
            "CacheResponse": {
                "type": "object",
                "properties": {
                    "results": {"type": "array", "items": {"type": "object", "properties": {
                        "tool": {"type": "string"},
                        "reference": {"type": "string"},
                        "model_version": {"type": "string"},
                        "cached_at": {"type": "string", "format": "date-time"},
                        "result": {"$ref": "#/components/schemas/AnalysisResult"},
                    }}},
                    "total": {"type": "integer"},
                    "limit": {"type": "integer"},
                    "offset": {"type": "integer"},
                },
            },
            "DiscoveryCard": {
                "type": "object",
                "properties": {
                    "reference": {"type": "string"},
                    "tool": {"type": "string"},
                    "snippet": {"type": "string"},
                    "cached_at": {"type": "string", "format": "date-time"},
                },
            },
            "SblResponse": {
                "type": "object",
                "properties": {
                    "reference": {"type": "string"},
                    "tool": {"type": "string"},
                    "footnote": {"type": "string"},
                    "footnotes": {"type": "array", "items": {"type": "string"}},
                },
            },
            "BibtexResponse": {
                "type": "object",
                "properties": {
                    "reference": {"type": "string"},
                    "tool": {"type": "string"},
                    "bibtex": {"type": "string"},
                },
            },
            "VoteRequest": {
                "type": "object",
                "required": ["reference", "tool", "value"],
                "properties": {
                    "reference": {"type": "string"},
                    "tool": {"type": "string"},
                    "value": {"type": "integer", "enum": [-1, 0, 1], "description": "1 = upvote, -1 = downvote, 0 = remove vote"},
                },
            },
            "HypothesisVoteRequest": {
                "type": "object",
                "required": ["reference", "tool", "hypothesis_id", "value"],
                "properties": {
                    "reference": {"type": "string"},
                    "tool": {"type": "string"},
                    "hypothesis_id": {"type": "string"},
                    "value": {"type": "integer", "enum": [-1, 0, 1]},
                },
            },
            "VoteResponse": {
                "type": "object",
                "properties": {
                    "tool": {"type": "string"},
                    "reference": {"type": "string"},
                    "upvotes": {"type": "integer"},
                    "downvotes": {"type": "integer"},
                },
            },
        }
    },
}

research_bp = Blueprint('research', __name__)

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))


def _parse_paper():
    """Parse paper.md and paper.bib, return dict ready for template."""
    paper_path = os.path.join(_BASE_DIR, 'paper.md')
    bib_path   = os.path.join(_BASE_DIR, 'paper.bib')

    with open(paper_path, encoding='utf-8') as f:
        raw = f.read()

    # Strip YAML frontmatter
    body = re.sub(r'^---\s*\n.*?\n---\s*\n', '', raw, flags=re.DOTALL)

    # Extract frontmatter fields
    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', raw, flags=re.DOTALL)
    frontmatter = fm_match.group(1) if fm_match else ''
    title   = re.search(r"^title:\s*['\"]?(.*?)['\"]?\s*$", frontmatter, re.M)
    date    = re.search(r'^date:\s*(.+)$', frontmatter, re.M)
    # Only parse names/orcids under the `authors:` block (stop at `affiliations:`)
    authors_block = re.search(r'^authors:\s*\n(.*?)(?=^\w)', frontmatter, re.DOTALL | re.M)
    ab = authors_block.group(1) if authors_block else ''
    authors = re.findall(r'^\s*-?\s*name:\s*(.+)$', ab, re.M)
    orcids  = re.findall(r'^\s*orcid:\s*(.+)$', ab, re.M)

    # Build cite key → short label mapping for inline superscripts
    cite_keys = re.findall(r'@(\w+)', body)
    unique_keys = list(dict.fromkeys(cite_keys))  # preserve order
    key_num = {k: i+1 for i, k in enumerate(unique_keys)}

    # Replace [@key1; @key2] or [@key] with superscript footnote numbers
    def _replace_cite(m):
        keys = re.findall(r'@(\w+)', m.group(0))
        nums = ', '.join(str(key_num[k]) for k in keys if k in key_num)
        return f'<sup class="paper-cite">[{nums}]</sup>'
    body = re.sub(r'\[@[^\]]+\]', _replace_cite, body)

    # Remove the bare "# References" section — we render from bib
    body = re.sub(r'\n# References\s*$', '', body, flags=re.DOTALL)

    # Convert markdown to HTML
    html = _md.markdown(body, extensions=['tables', 'fenced_code', 'nl2br'])

    # Parse bib file into list of formatted reference strings
    refs = _parse_bib(bib_path, unique_keys, key_num)

    return {
        'title':   title.group(1) if title else 'BibCrit',
        'authors': list(zip(authors, orcids + ['']*len(authors))),
        'date':    date.group(1) if date else '2026',
        'html':    html,
        'refs':    refs,
    }


def _parse_bib(bib_path, ordered_keys, key_num):
    """Return list of (num, formatted_html) tuples in citation order."""
    with open(bib_path, encoding='utf-8') as f:
        raw = f.read()

    entries = {}
    for entry in re.finditer(r'@\w+\{(\w+),(.*?)\n\}', raw, re.DOTALL):
        key   = entry.group(1)
        block = entry.group(2)
        def _field(name):
            m = re.search(rf'{name}\s*=\s*\{{(.+?)\}}', block, re.DOTALL)
            v = m.group(1).strip().replace('\n', ' ') if m else ''
            return v.strip('{}')  # remove BibTeX double-brace wrappers
        entries[key] = {
            'author':  _field('author'),
            'title':   _field('title'),
            'year':    _field('year'),
            'journal': _field('journal'),
            'publisher': _field('publisher'),
            'edition': _field('edition'),
            'url':     _field('url'),
            'doi':     _field('doi'),
            'note':    _field('note'),
            'howpublished': _field('howpublished').replace(r'\url{', '').rstrip('}'),
        }

    result = []
    for k in ordered_keys:
        if k not in entries:
            continue
        e   = entries[k]
        num = key_num[k]
        url = e['doi'] and f'https://doi.org/{e["doi"]}' or e['url'] or e['howpublished'] or ''
        url = re.sub(r'\\url\{([^}]+)\}', r'\1', url)
        parts = []
        if e['author']:  parts.append(e['author'])
        if e['title']:
            t = f'<em>{e["title"]}</em>' if not e['journal'] else f'"{e["title"]}"'
            parts.append(t)
        if e['journal']: parts.append(e['journal'])
        if e['edition']: parts.append(e['edition'] + ' ed.')
        if e['publisher']: parts.append(e['publisher'])
        if e['year']:    parts.append(e['year'])
        ref_text = '. '.join(parts)
        if url:
            ref_text += f'. <a href="{url}" target="_blank" rel="noopener">{url}</a>'
        result.append((num, ref_text))

    return result


@research_bp.route('/health')
def health():
    return jsonify({'status': 'ok', 'app': 'bibcrit'})


@research_bp.route('/guide')
def guide():
    lang = request.args.get('lang', 'en')
    template = 'guide_es.html' if lang == 'es' else 'guide.html'
    return render_template(template, lang=lang, t=state.t)


@research_bp.route('/paper')
def paper():
    lang = request.args.get('lang', 'en')
    data = _parse_paper()
    return render_template('paper.html', lang=lang, t=state.t, **data)


@research_bp.route('/api/v1/openapi.json')
def openapi_spec():
    """Machine-readable OpenAPI 3.0 spec for the BibCrit API."""
    return jsonify(_OPENAPI_SPEC)


@research_bp.route('/api/docs')
def api_docs():
    """Swagger UI for the BibCrit API."""
    return render_template('api_docs.html', lang='en', t=state.t)
