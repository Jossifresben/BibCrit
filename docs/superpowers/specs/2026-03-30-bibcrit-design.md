# BibCrit — Biblical Textual Criticism Platform
## Product Requirements Document

**Date:** 2026-03-30
**Status:** Approved for implementation planning
**Project location:** `/Users/jfresco16/Google Drive/Claude/BibCrit`
**Reference project:** Aramaic Root Atlas (`/Users/jfresco16/Google Drive/Claude/aramaic-root-atlas`)

---

## 1. Vision & Goals

BibCrit is a comprehensive Biblical Textual Criticism research platform that applies Claude AI as its primary analytical engine, enabling scholars to examine divergences between manuscript traditions, reconstruct probable Vorlagen, profile scribal tendencies, and build manuscript transmission genealogies — all with explicit confidence scoring, competing hypotheses, and academic-grade export.

**Primary goal:** Give seminary-trained scholars and academics a research-grade tool that applies rigorous critical methodology to manuscript comparison, replacing hours of manual apparatus consultation with structured, citable AI-assisted analysis.

**Secondary goal:** Democratize scholarship through a public-facing Discovery layer — curated, plain-language findings auto-generated as a flywheel of scholarly use, requiring no Hebrew or Greek knowledge.

**Funding pathway:** Demo the flagship tool (MT/LXX Parallel Divergence Analyzer) to ETCBC and similar institutions. Token costs are low enough ($5–200/month depending on scale) that a small institutional grant covers operations and unlocks the premium "Ask Claude" conversational layer.

---

## 2. Target Users

### Primary: Scholars & Academics
- Seminary-trained researchers, PhD students, professors
- Fluent in Biblical Hebrew and/or Koine Greek
- Familiar with critical terminology: BHS apparatus, Vorlage, stemma, scribal tendencies, Masoretic Text, Septuagint
- Expect citation-grade output with explicit uncertainty flagging
- Need SBL-format footnote export

### Secondary: Curious Laypeople (Discovery layer only)
- No original language knowledge required
- Access via the Discovery section only — curated, plain-language findings
- Entry point for donations and community building
- Audience for "Word of the Week," "Did You Know?" and thematic deep-dives

---

## 3. Architecture

### 3.1 Strategy: Fork the Aramaic Root Atlas

BibCrit is built by forking the Aramaic Root Atlas codebase. The Atlas proves the Flask + Python + Jinja2 + D3.js + Render.com stack at production scale for scholarly linguistic tools. Forking saves weeks of infrastructure rebuilding.

**Key structural upgrade over the Atlas:** Flask Blueprints replace the monolithic `app.py` (2,521 lines in the Atlas). BibCrit's routes are split across four blueprints from day one, preventing the monolith problem as the tool count grows.

### 3.2 Repository Structure

```
bibcrit/
├── biblical_core/                  # NEW — BibCrit-specific engine
│   ├── corpus.py                   # BiblicalCorpus: loads MT/LXX/DSS/Peshitta
│   ├── characters.py               # Hebrew/Greek char maps (extended from Atlas)
│   ├── claude_pipeline.py          # Claude API calls, prompt templates, response parsing
│   ├── divergence.py               # MT/LXX variant classification engine
│   ├── scribal.py                  # Scribal tendency profiler
│   └── stemma.py                   # Manuscript genealogy logic (Tier 2)
├── aramaic_core/                   # KEPT from Atlas (root extraction, cognates)
│   ├── characters.py
│   ├── affixes.py
│   ├── corpus.py
│   ├── extractor.py
│   ├── cognates.py
│   └── glosser.py
├── blueprints/                     # NEW — Flask Blueprints
│   ├── textual.py                  # MT/LXX tools, DSS bridge, back-translation
│   ├── critical.py                 # Scribal profiler, theological revision, stemma
│   ├── research.py                 # Concordance, hapax, collocations (from Atlas)
│   └── discovery.py               # Public-facing democratization layer
├── templates/                      # Jinja2 templates (extended from Atlas)
│   ├── base.html                   # Navbar, settings, dark mode (updated branding)
│   ├── divergence.html             # MT/LXX Parallel Divergence Analyzer
│   ├── backtranslation.html        # LXX Back-Translation Workbench
│   ├── scribal.html                # Scribal Tendency Profiler
│   ├── numerical.html              # Numerical Discrepancy Modeler
│   ├── discovery.html              # Discovery landing page
│   └── [tier2 templates...]
├── static/
│   ├── bibcrit.css                 # New design system (extends Atlas CSS variables)
│   ├── apparatus.js                # Textual apparatus UI interactions
│   ├── stemma.js                   # D3 tree layout for stemma diagrams
│   └── js/                         # Shared D3 visualization utilities
├── data/
│   ├── corpora/
│   │   ├── mt_etcbc/               # ETCBC BHSA (Hebrew OT + Biblical Aramaic)
│   │   ├── lxx_stepbible/          # STEPBible LXXM (morphological LXX)
│   │   ├── gnt_opengnt/            # OpenGNT (morphological GNT)
│   │   └── dss/                    # Dead Sea Scrolls (Tier 2 — slot designed now)
│   ├── translations/               # KEPT from Atlas (EN/ES/HE/AR/EL)
│   ├── prompts/                    # Versioned Claude prompt templates
│   │   ├── divergence_v1.txt
│   │   ├── backtranslation_v1.txt
│   │   ├── scribal_v1.txt
│   │   └── numerical_v1.txt
│   ├── cache/                      # Cached Claude analysis results (JSON)
│   └── i18n.json                   # KEPT + extended for BibCrit UI strings
├── app.py                          # Slim factory — registers blueprints only
├── render.yaml                     # Render.com deployment (same as Atlas)
├── pyproject.toml
└── README.md
```

### 3.3 What Is Reused vs. New

**Reused from Aramaic Root Atlas (direct or near-direct):**
- Multi-corpus CSV loader pattern → `BiblicalCorpus` follows same interface
- i18n system (EN/ES/HE/AR) with RTL support
- Design system: CSS variables (`--bg`, `--fg`, `--accent`, dark mode), corpus-coded colors
- D3.js force graph template → adapted for stemma trees and divergence networks
- Academic export formats: TEI XML, BibTeX, Zotero RDF, CSV, JSON
- Bookmarks + researcher annotations (localStorage)
- Guided tour (driver.js)
- Settings panel: language, script, translation track
- QR code sharing
- Render.com deployment configuration
- `aramaic_core/` modules for Peshitta/Targum analysis features

**New in BibCrit:**
- `biblical_core/` module suite
- Flask Blueprint architecture (replaces monolithic app.py)
- Claude API pipeline + prompt template system
- Confidence scoring UI components (HIGH/MEDIUM/LOW badges)
- Competing hypotheses display pattern
- Textual apparatus renderer
- Stemma diagram (D3 tree layout, not force graph)
- ETCBC BHSA, STEPBible LXXM, OpenGNT data ingestion
- Extended Sefaria API integration (Targum Jonathan, rabbinic literature)
- Discovery layer with flywheel content generation
- API budget cap + donation flow

---

## 4. Data Layer

### 4.1 Text Traditions & Sources

| Tradition | Primary Source | License | Coverage |
|-----------|---------------|---------|----------|
| Masoretic Text (MT) | ETCBC BHSA | Open (DANS/GitHub) | Full OT Hebrew + Biblical Aramaic. Deep morphology: POS, clause trees, syntactic roles. |
| MT supplement | Westminster Leningrad Codex | Open | Full cantillation marks, complete Ketiv-Qere apparatus |
| Septuagint (LXX) | STEPBible LXXM | CC BY 4.0 | Full LXX with morphological tagging. Lemmas, parsing, Strong's. |
| LXX manuscript families | Rahlfs-Hanhart critical notes | Reference only | Vaticanus (B), Sinaiticus (א), Alexandrinus (A), Hexapla readings tracked |
| Greek NT | OpenGNT | Open | Full GNT, morphologically tagged |
| GNT supplement | STEPBible TAGNT | Open | Cross-references, supplemental morphology |
| Targums + Rabbinic | Sefaria API | Open API | Targum Onkelos, Neofiti, Jonathan. Talmud, Midrash, medieval commentaries (Rashi, Ibn Ezra) |
| Dead Sea Scrolls | Leon Levy DSS Digital Library + critical editions | Curated CSV | Tier 2. Best coverage: 1QIsa-a, 4QJer-b, Psalms scrolls, Deuteronomy scrolls |

### 4.2 Data Models

```python
@dataclass
class VerseWord:
    reference: str          # "Isaiah 7:14"
    tradition: str          # "MT" | "LXX" | "GNT" | "Peshitta" | "DSS"
    position: int           # word position in verse
    word_text: str          # "הָעַלְמָה" / "παρθένος"
    lemma: str              # "עַלְמָה" / "παρθένος"
    morph: str              # "def.art + noun, fs, abs"
    strong: str             # "H5959" / "G3933"
    manuscript: str         # "Leningrad" | "Vaticanus" | "1QIsa-a" ...

@dataclass
class DivergenceRecord:
    reference: str
    mt_word: str
    lxx_word: str
    divergence_type: str    # "theological_tendency" | "scribal_error" |
                            # "different_vorlage" | "translation_idiom" |
                            # "grammatical_shift" | "omission" | "addition"
    confidence: float       # 0.0 – 1.0
    hypotheses: list        # ranked list of {type, confidence, explanation}
    dss_witness: str | None # DSS agreement if available
    citations: list         # scholarly references
    analysis_technical: str # full scholarly analysis text
    analysis_plain: str     # plain-language version for Discovery
    discovery_ready: bool   # admin-toggled flag for Discovery publication

@dataclass
class VerseAlignment:
    reference: str
    traditions: dict        # {tradition: [VerseWord, ...]}
    divergences: list       # [DivergenceRecord, ...]
    cached_at: datetime
    model_version: str      # Claude model used
```

### 4.3 Canon Coverage

| Canon Section | MT | LXX | GNT | Targum | DSS |
|--------------|----|----|-----|--------|-----|
| Torah (Gen–Deut) | ✅ | ✅ | — | ✅ Onkelos | Tier 2 |
| Prophets (Nevi'im) | ✅ | ✅ | — | ✅ Jonathan | Tier 2 |
| Writings (Ketuvim) | ✅ | ✅ | — | Partial | Tier 2 |
| New Testament | — | — | ✅ | — | — |

---

## 5. Claude API Pipeline

### 5.1 Pipeline Flow

```
1. PASSAGE REQUEST
   User selects passage via corpus browser (book/chapter/verse dropdowns)
   or types reference directly. Scope: verse | chapter | book.
   BiblicalCorpus fetches all available traditions for that reference.

2. CACHE CHECK
   claude_pipeline.py checks data/cache/ for existing analysis.
   Cache key: sha256(passage + tool + prompt_version + model_version)
   Cache hit → serve immediately (free). Cache miss → proceed.

3. PROMPT ASSEMBLY
   Load versioned prompt template from data/prompts/{tool}_v{n}.txt
   Inject: MT text, LXX text, morphological data, manuscript variants,
   tradition-specific context.
   System prompt: scholarly persona + methodology + output JSON schema.

4. CLAUDE ANALYSIS
   Model: selected per-tool (see §5.2 Model Selection)
   Output: structured JSON with technical analysis + plain-language version
   in a single call. Both saved to cache simultaneously.

5. CACHE WRITE
   Full response saved as JSON to data/cache/{key}.json
   Includes: analysis_technical, analysis_plain, confidence scores,
   hypotheses, citations, model_version, cached_at, discovery_ready=false

6. RENDER & SERVE
   Flask route renders the analysis into the Jinja2 template.
   Discovery layer queries cache for analysis_plain entries where
   discovery_ready=true.
```

### 5.2 Model Selection

Model is selected per-tool in `claude_pipeline.py`. The cache key includes `model_version` so Sonnet and Opus results are stored separately and never mixed.

| Tool | Model | Rationale |
|------|-------|-----------|
| MT/LXX Divergence Analyzer | claude-3-5-sonnet | Structured classification + JSON output — Sonnet quality is sufficient |
| LXX Back-Translation Workbench | claude-3-5-sonnet | Word-level reconstruction with clear methodology — Sonnet handles well |
| Numerical Discrepancy Modeler | claude-3-5-sonnet | Pattern analysis on structured numerical data — Sonnet is reliable |
| Scribal Tendency Profiler | **claude-opus** | Subtle stylometric reasoning across full books requires Opus depth. Cost justified by permanent caching — run once per book. |
| "Ask Claude" conversational layer | **claude-opus** | Open-ended scholarly dialogue demands highest reasoning quality. Funded feature — Opus cost covered by institutional grant or donation token. |
| Tier 2 tools (default) | claude-3-5-sonnet | Revisit per-tool during Tier 2 build if quality is insufficient |

### 5.3 Prompt Architecture

Prompt templates are versioned files stored in `data/prompts/`. This separates prompt engineering from code and allows improvement without redeployment. Each template contains:

- **Scholarly persona block** — establishes Claude as a textual critic trained in the relevant methodology
- **Methodology context** — the specific critical framework (divergence classification taxonomy, confidence criteria, etc.)
- **Output schema** — strict JSON schema Claude must return
- **Passage injection points** — `{{MT_TEXT}}`, `{{LXX_TEXT}}`, `{{MORPH_DATA}}`, etc.

When prompt templates are updated (version bump), all cached entries for that tool are invalidated on next request.

### 5.4 Confidence Scoring UI

Every Claude-generated finding is displayed with explicit uncertainty. Three tiers:

| Badge | Score range | Color | Meaning |
|-------|------------|-------|---------|
| HIGH | 0.75 – 1.0 | Green | Strong scholarly consensus or clear textual evidence |
| MEDIUM | 0.45 – 0.74 | Amber | Plausible but contested; competing explanations have merit |
| LOW | 0.00 – 0.44 | Red | Speculative; little textual support |

Each finding displays:
1. **Primary hypothesis** (highest confidence) with full explanation
2. **Alternative hypotheses** (ranked by confidence) as expandable pills
3. **Source citations** (BHS apparatus, Tov, Wevers, Pietersma, relevant DSS evidence)
4. **Export controls**: footnote (SBL format), BibTeX, save to bookmarks

### 5.5 Discovery Flywheel

Every Claude analysis call generates two outputs in a single API call at no extra cost:

- `analysis_technical` — full scholarly analysis for the research tools
- `analysis_plain` — same finding in plain language, saved alongside it

The Discovery section queries `analysis_plain` from the cache. As scholars use the app, Discovery content grows automatically. An admin `discovery_ready` flag on each cache entry allows curation — some analyses are too narrow to surface publicly; others are ideal showcase material. A simple admin toggle controls publication.

### 5.6 Token Cost Estimates

| Tool / Operation | Model | Approx tokens (in+out) | Estimated cost | Caching impact |
|-----------------|-------|----------------------|----------------|----------------|
| MT/LXX divergence — single verse | Sonnet | ~2,000 | ~$0.01 | High reuse → near-zero after first |
| MT/LXX divergence — full chapter | Sonnet | ~8,000 | ~$0.03 | Cached per chapter |
| Back-translation workbench — passage | Sonnet | ~3,500 | ~$0.02 | Medium reuse |
| Numerical discrepancy modeler | Sonnet | ~5,000 | ~$0.04 | Static data → near-permanent cache |
| Scribal tendency profiler — full book | **Opus** | ~60,000 (chunked) | ~$2.00–8.00 | Run once per book, cached permanently |
| "Ask Claude" conversational (funded) | **Opus** | ~4,000/turn | ~$0.15/turn | Not cacheable |

**Monthly operational estimates:**
- Solo researcher (heavy use): $5–15/month
- 10–50 active scholars: $50–200/month
- ETCBC grant: covers "Ask Claude" conversational layer + institutional access

### 5.7 API Budget Cap + Donation Flow

- A single API key is configured with a monthly spend cap (default: $5, configurable)
- A persistent budget bar in the page footer shows: `Monthly budget: $X.XX / $Y.00 used`
- At 80% of cap: donate button appears alongside the bar
- At 100% of cap: a tasteful modal explains the situation, thanks the user for their use of the tool, and presents a donation link (Ko-fi or Stripe)
- Donors receive a session token extending access for 30 days
- All cap and donation logic lives in `claude_pipeline.py` — transparent and auditable

---

## 6. Tier 1 Tools

### 6.1 MT/LXX Parallel Divergence Analyzer ⭐ Flagship

**Route:** `/divergence`
**Blueprint:** `textual`
**Description:** The app's anchor feature. Side-by-side display of MT Hebrew and LXX Greek for any passage, with Claude classifying every divergence by type, scoring confidence, generating competing hypotheses, and citing relevant scholarship and manuscript witnesses.

**Layout:** Three-column (MT | LXX | Claude Analysis panel)

**Passage selection:**
- Corpus browser: book dropdown → chapter dropdown → verse dropdown
- Direct reference input: typed free-form ("Isaiah 7:14")
- Scope toggle: verse / chapter / book (cost warning shown for book scope)

**MT column:**
- Hebrew text (RTL, Noto Sans Hebrew, with nikud)
- Divergent words highlighted inline (amber background)
- Click any highlighted word → expands analysis in right panel
- Source: ETCBC Leningrad Codex
- English translation track below (WEB default, switchable)

**LXX column:**
- Greek text (Noto Serif)
- Corresponding divergent words highlighted (blue background)
- Manuscript family switcher inline: Vaticanus (B) | Sinaiticus (א) | Alexandrinus (A)
- Manuscript variants noted below verse text
- Source: STEPBible LXXM
- English translation below (NETS default)

**DSS column:**
- Appears automatically when DSS data is available for the passage (Tier 1: 1QIsa-a for Isaiah; Tier 2: expanded coverage)
- Shows DSS reading and tradition alignment (agrees with MT / agrees with LXX / unique reading)

**Claude Analysis panel:**
- Displays divergences sorted by confidence (highest first)
- Each divergence card: divergent words, classification badge, primary hypothesis, alternative hypotheses as expandable pills, citations
- Export controls: footnote (SBL), BibTeX, save to bookmarks, share

**Key divergence types classified:**
- Theological tendency
- Scribal error (haplography, dittography, homoioteleuton)
- Different Vorlage (translator had different Hebrew source)
- Translation idiom (Greek equivalent carries different connotations)
- Grammatical shift (person, number, tense)
- Omission / addition

### 6.2 LXX Back-Translation Workbench

**Route:** `/backtranslation`
**Blueprint:** `textual`
**Description:** Takes any LXX Greek passage and reconstructs the probable Hebrew Vorlage — the Hebrew text the translator likely had in front of them. Compares reconstruction against MT, available DSS witnesses, and flags where the LXX may reflect a lost Hebrew variant or pure Greek idiom.

**Input:** LXX passage via corpus browser or typed reference

**Output:**
- Reconstructed Hebrew text word-by-word, each word color-coded:
  - Green: agrees with MT
  - Blue: agrees with a known DSS variant
  - Red: unattested reading (possible lost Vorlage)
  - Grey: Greek idiom only (no Hebrew equivalent reconstructible)
- Confidence score per word
- Side-by-side comparison: Vorlage reconstruction | MT | DSS (when available)
- Full explanation of reconstruction methodology for each divergent word

**Scholar annotation layer:**
- Each word has inline controls: Confirm / Dispute / Annotate
- Annotations saved to researcher's annotation store
- Exported with findings as part of the critical note

**Export:** Reconstructed Vorlage as critical note (SBL format), BibTeX, TEI XML

### 6.3 Scribal Tendency Profiler

**Route:** `/scribal`
**Blueprint:** `critical`
**Description:** Builds a statistical "fingerprint" of each LXX book's translator — their theological tendencies, translation style, and preferred Greek equivalents for Hebrew terms. Enables clustering by translator school.

**Input:** Select a biblical book

**Processing:** Full book analyzed in chunks (chapter by chapter through Claude). Results cached permanently after first run — one-time cost per book.

**Tendencies measured:**
- Literalness score (% of words rendered word-for-word vs. free paraphrase)
- Anthropomorphism reduction (frequency of softening divine physical descriptions)
- Messianic heightening (frequency of adding messianic coloring to ambiguous passages)
- Harmonization tendency (aligning divergent parallel passages)
- Free paraphrase rate (expansions, condensations, restructuring)
- Preferred Greek equivalents for the 50 most common Hebrew roots in the book

**Visualization:**
- Radar/spider chart showing the five tendency scores
- Comparison mode: overlay two books' fingerprints to detect shared translator
- Frequency bar charts for preferred Greek equivalents

**Most valuable use cases:** Isaiah (Deutero-Isaiah question), Jeremiah (MT vs. LXX editorial tradition), Daniel (LXX vs. Theodotion), Psalms (multiple translator hands)

### 6.4 Numerical Discrepancy Modeler

**Route:** `/numerical`
**Blueprint:** `critical`
**Description:** Focused analysis of systematic numerical discrepancies across text traditions. Primary use case: Genesis 5 and 11 patriarchal ages (MT / LXX / Samaritan Pentateuch). Claude tests whether differences are random or systematic and scores competing theories.

**Primary dataset:** Genesis 5 and 11 — all three traditions with complete age data

**Visual output:**
- Timeline plot: three traditions side-by-side, patriarch by patriarch
- Difference table: MT vs. LXX delta, MT vs. SP delta, LXX vs. SP delta
- Pattern analysis: Are differences random or systematic? (Claude statistical analysis)

**Competing theories scored:**
1. MT deflated numbers post-exilically (to prevent overlap with flood)
2. LXX inflated numbers (theological motivation for longer antediluvian era)
3. SP harmonized independently
4. All three reflect independent scribal traditions from a common (now lost) original

**Expandability:** Designed to accept other numerical datasets (Kings/Chronicles regnal year discrepancies, temple measurement differences)

---

## 7. Discovery Layer

**Route:** `/discovery`
**Blueprint:** `discovery`
**Nav:** Highlighted in gold in the main navigation — distinct from scholarly tools

**Description:** Public-facing section requiring no Hebrew or Greek knowledge. Surfaces the most fascinating scholarly findings in plain language. Serves three purposes: (1) democratizes scholarship, (2) acts as the app's public face for fundraising and visibility, (3) provides a gentle entry point that may convert curious laypeople into donors.

**Content types:**

- **Word of the Week** — a single word with a fascinating translation history. Auto-selected from high-confidence divergence analyses with high plain-language quality.
- **Did You Know?** — a brief striking fact about textual transmission (e.g., "The Greek Jeremiah is one-eighth shorter than the Hebrew version")
- **Deep Dives** — thematic collections (e.g., "The Most Debated Verses," "When Translators Had a Different Bible," "The Numbers Problem")
- **Featured Analysis** — a full scholarly analysis from the Divergence Analyzer rendered in plain language with a "See the scholarly analysis" link

**Content pipeline (the flywheel):**
1. Scholar runs any analysis tool → Claude generates `analysis_technical` + `analysis_plain` in one call
2. Both saved to cache
3. Admin reviews `analysis_plain` entries, sets `discovery_ready=true` on quality entries
4. Discovery page automatically populates from flagged cache entries
5. Zero extra cost — content grows as a byproduct of scholarly use

**Sharing:** Every Discovery card has a share button generating a direct link + social preview card. Designed to be shareable on social media to grow awareness.

---

## 8. Tier 2 Tools (Roadmap)

To be built after Tier 1 is deployed and initial user/funding feedback is received.

### 8.1 Manuscript Transmission Genealogy Tool
**Route:** `/stemma` | **Blueprint:** `textual`

Scholar inputs variant readings from multiple manuscripts. Claude builds a probable transmission tree showing which manuscript families share readings and where splits likely occurred. DSS readings serve as fixed anchor points. Visualized as a D3 tree layout (extending the Atlas's force graph infrastructure). Each tree node links to Claude's reasoning for the split.

### 8.2 Patristic & Rabbinic Citation Tracker
**Route:** `/citations` | **Blueprint:** `critical`

Upload a patristic text (Origen, Justin Martyr, Jerome, Augustine) or Rabbinic source. Claude extracts all scriptural citations, identifies which text tradition they reflect, and plots them on a timeline + geographic map. Tracks when the LXX gave way to the MT in Christian use. Sefaria API feeds Rabbinic literature automatically.

### 8.3 Theological Revision Detector
**Route:** `/revision` | **Blueprint:** `critical`

Targets theologically sensitive passages: divine name usage, messianic prophecies, afterlife references, priestly/Deuteronomic tensions. Claude scores each variant for probability of theological motivation vs. textual accident. Pre-loaded with known hotspots: Isa 7:14, Ps 22:16, Deut 32:8, Dan 7:13-14, the Ten Commandments (Exodus vs. Deuteronomy). Generates structured for/against argument for intentional revision.

### 8.4 Dead Sea Scrolls Bridge Tool
**Route:** `/dss` | **Blueprint:** `textual`

Input a DSS fragment identifier (e.g., 4QJer-b, 1QIsa-a). Claude maps its readings against both MT and LXX, showing exactly where it aligns with each tradition. Calculates a "tradition proximity score" (proto-MT vs. proto-LXX Vorlage). Best coverage: Isaiah (1QIsa-a), Psalms, Deuteronomy, Samuel, Jeremiah. The corpus slot is designed in `BiblicalCorpus` from day one — DSS data plugs in when the Tier 2 ingestion pipeline is built.

---

## 9. Tier 3 — Unified Research Platform (Vision)

All tools assembled into a single integrated workbench. One passage selector controls all panels simultaneously.

**Core features:**
- **Shared passage selector** — change the passage once, every tool updates
- **Research Dossier** — Claude accumulates evidence across sessions per passage or book. Persistent, searchable, exportable
- **SBL Academic Export** — one-click export of all dossier findings as footnote-ready SBL-style text, ready for insertion into a paper
- **"Ask Claude" conversational layer** — a side panel research assistant available for open-ended queries about any passage or finding. Funded feature: unlocked via ETCBC grant or donation token

**Technology note:** Tier 3's multi-panel workbench may warrant a React frontend layer over the Flask backend. This decision is deferred to the Tier 2 → Tier 3 transition, when the Python modules will be mature and a clean REST API layer is a natural evolution.

---

## 10. Navigation Structure

```
✝ BibCrit    [Textual Analysis ▾]  [Critical Analysis ▾]  [Research ▾]  [✦ Discovery]
                                                                          🌐  ⚙  🔖  ?

Textual Analysis ▾              Critical Analysis ▾         Research ▾
  MT/LXX Divergence Analyzer ⭐   Scribal Tendency Profiler   Concordance
  Back-Translation Workbench      Numerical Discrepancy       Hapax Finder
  DSS Bridge Tool (Tier 2)        Theological Revision Det.   Collocations
  Manuscript Genealogy (Tier 2)   Patristic Citations (T2)    Passage Profile
```

- **Discovery** is highlighted in gold — distinct from scholarly tools, public-facing
- **Research** dropdown carries over Atlas research tools (concordance, hapax, collocations, passage profile) adapted for the biblical corpus
- Icons (right side): Language selector, Settings, Bookmarks, Guided Tour
- Mobile: hamburger menu (same as Atlas)

---

## 11. Design System

BibCrit extends the Atlas design system. Same CSS variable architecture, same dark mode pattern, updated color palette to reflect the different corpus traditions.

**Color palette:**

```css
:root {
  --bg: #faf8f4;           /* warmer off-white (parchment feel) */
  --fg: #1a1a1a;
  --accent: #2c3e50;       /* dark slate (vs. Atlas blue) */
  --mt-color: #c0892a;     /* amber — Masoretic Text */
  --lxx-color: #3a6bc4;    /* blue — Septuagint */
  --gnt-color: #2c7c5f;    /* green — Greek NT */
  --dss-color: #5f2c7c;    /* purple — Dead Sea Scrolls */
  --peshitta-color: #7c2c2c; /* deep red — Peshitta */
}

[data-theme="dark"] {
  --bg: #111210;
  --fg: #e8e6de;
  --accent: #5a8ab5;
  /* corpus colors adjusted for dark contrast */
}
```

**Typography:**
- Hebrew: Noto Sans Hebrew (same as Atlas)
- Greek: Noto Serif (for LXX/GNT display)
- Syriac: Noto Sans Syriac (kept for Peshitta tools)
- Body: system font stack (same as Atlas)

---

## 12. Non-Functional Requirements

| Requirement | Specification |
|-------------|--------------|
| **Response time** | Cached analyses: < 200ms. Live Claude calls: < 15s (show loading indicator). Chapter-scope analysis: async with progress bar. |
| **Caching** | All Claude outputs cached to disk as JSON. Cache is permanent until prompt version bump. Popular passages (Isaiah 7, Genesis 1) pre-warmed at deployment. |
| **Deployment** | Render.com, same infrastructure as Atlas. Python 3.11+, Gunicorn, single dyno for Tier 1. |
| **RTL support** | Hebrew text rendered RTL throughout. i18n system supports EN/ES/HE/AR UI languages (extended from Atlas). |
| **Export formats** | SBL footnote (plain text), BibTeX, Zotero RDF, TEI XML, CSV, JSON |
| **Accessibility** | WCAG 2.1 AA target. Hebrew/Greek text has sufficient contrast in both light and dark modes. |
| **Mobile** | Responsive layout. Three-column divergence view collapses to tabbed single-column on mobile. |
| **Budget monitoring** | Monthly API spend tracked per-key. Configurable cap. Budget bar visible on every analysis page. Donation flow at 80% and 100% of cap. |
| **Scholar annotation** | localStorage-based (same as Atlas). Future: server-side sync for institutional deployment. |

---

## 13. Build Sequence

### Phase 0 — Foundation (Fork + Refactor)
1. Fork Aramaic Root Atlas repository into BibCrit
2. Refactor `app.py` into Flask Blueprint architecture
3. Create `biblical_core/` module skeleton
4. Data pipeline: ingest ETCBC BHSA, STEPBible LXXM, OpenGNT
5. `BiblicalCorpus` class with multi-tradition loading
6. `claude_pipeline.py` with prompt template system, caching, budget tracking
7. Update design system (CSS variables, color palette, nav branding)

### Phase 1 — Flagship Tool
8. MT/LXX Parallel Divergence Analyzer (full feature set)
9. Confidence scoring UI components
10. Competing hypotheses display
11. Academic export (SBL footnote, BibTeX)
12. API budget cap + donation flow
13. Discovery flywheel (dual-output Claude calls, admin flag)

### Phase 2 — Complete Tier 1
14. LXX Back-Translation Workbench
15. Scribal Tendency Profiler (with D3 radar chart)
16. Numerical Discrepancy Modeler
17. Discovery landing page (Word of the Week, Did You Know?, Deep Dives)
18. Guided tour (driver.js, updated for BibCrit)

### Phase 3 — Tier 2 (post-funding/feedback)
19. DSS data ingestion pipeline + Bridge Tool
20. Manuscript Transmission Genealogy (D3 stemma tree)
21. Theological Revision Detector
22. Patristic & Rabbinic Citation Tracker

### Phase 4 — Tier 3 Unified Platform
23. Unified workbench shell with shared passage selector
24. Research Dossier (cross-session persistence)
25. SBL batch export
26. "Ask Claude" conversational layer (funded feature)
27. ETCBC / institutional API integration

---

## 14. Open Questions (Deferred)

- **Collaborative annotations:** Should annotations be shareable between scholars in a later phase? Requires server-side storage.
- **Institutional login:** ETCBC partnership may require authenticated access for premium features. Architecture supports adding this without refactor.
- **React migration:** Tier 3 workbench may benefit from a React frontend. Deferred to Tier 2 → Tier 3 transition.
- **API key per user vs. shared key:** Current design uses a single API key with a shared budget cap. Institutional deployment may require per-user keys.
- **Samaritan Pentateuch:** Relevant for the Numerical Discrepancy Modeler (Genesis 5/11). No clean open digital source identified yet. Tier 2 research item.

---

*Generated via BibCrit brainstorming session with Claude · 2026-03-30*
*Reference: Aramaic Root Atlas codebase analysis + product vision from prior session*
