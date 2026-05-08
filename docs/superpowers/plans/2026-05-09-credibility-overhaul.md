# Credibility & Honesty Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface every place BibCrit implies more certainty than is warranted — missing AI disclaimers, hidden corpus gaps, unchallenged methodological frameworks, and invisible cache metadata — and fix each one with minimal, targeted changes.

**Architecture:** Seven independent edits to existing templates, JS files, and i18n.json. No new endpoints. No new CSS classes beyond what `bibcrit.css` already provides. Each task touches 1–3 files and can be committed and verified independently.

**Tech Stack:** Flask/Jinja2 templates, vanilla JS, `data/i18n.json` for translated strings, existing `.bt-info-banner` CSS class, existing `.analysis-model-attr` CSS class.

---

## File Map

| File | Tasks |
|------|-------|
| `templates/base.html` | Task 1 (cite modal disclaimer) |
| `templates/patristic.html` | Task 2 (training-data banner) |
| `templates/stl.html` | Task 3 (training-data banner) |
| `templates/source.html` | Task 4 (contested framework notice) |
| `static/apparatus.js` | Task 5 (cached_at in attribution) |
| `static/backtranslation.js` | Task 5 (cached_at in attribution) |
| `static/dss.js` | Task 5 (cached_at in attribution) |
| `static/scribal.js` | Task 5 (cached_at in attribution) |
| `static/genealogy.js` | Task 5 (cached_at in attribution) |
| `static/patristic.js` | Task 5 (cached_at in attribution) |
| `static/theological.js` | Task 5 (cached_at in attribution) |
| `static/nt_ot.js` | Task 5 (cached_at in attribution) |
| `templates/index.html` | Task 6 (student academic honesty note) |
| `data/i18n.json` | Tasks 2, 3, 4, 6 (new i18n keys) |

---

## Task 1 — Cite Modal AI Disclaimer

**Why:** The cite modal (`Cite this`) lets users generate BibTeX/Chicago/SBL/APA/MLA entries and encourages direct academic citation. There is currently no warning that the cited content is AI-generated. A scholar who clicks "Copy" and pastes into a paper has no in-UI nudge to verify the analysis.

**Files:**
- Modify: `templates/base.html` (lines 241–245)

- [ ] **Step 1: Locate the insertion point**

Open `templates/base.html`. The cite modal content area looks like this (lines 241–245):

```html
<pre class="cite-pre" id="cite-pre"></pre>
<div class="cite-actions">
    <button class="btn-export cite-copy-btn" id="cite-copy-btn">...</button>
    <a class="cite-doi-link" href="...">DOI: ...</a>
</div>
<p class="cite-orcid">ORCID: <a ...>0009-0000-2026-0836</a></p>
```

- [ ] **Step 2: Insert disclaimer between `</pre>` and `<div class="cite-actions">`**

Replace the current block:

```html
            <pre class="cite-pre" id="cite-pre"></pre>
            <div class="cite-actions">
```

With:

```html
            <pre class="cite-pre" id="cite-pre"></pre>
            <p class="cite-ai-disclaimer">
              <span class="material-symbols-outlined" style="font-size:13px;vertical-align:-2px;margin-right:3px;opacity:0.7;">warning</span>AI-generated analysis — verify all findings against primary sources and critical editions before citing in peer-reviewed work.
            </p>
            <div class="cite-actions">
```

- [ ] **Step 3: Add CSS for `.cite-ai-disclaimer` in `templates/base.html` inline style block OR in `bibcrit.css`**

Add to `static/bibcrit.css` after the existing `.cite-orcid` rule. Search for `.cite-orcid` (currently around line 1455) and add after it:

```css
.cite-ai-disclaimer {
  margin: 8px 0 12px;
  font-size: 11px;
  color: var(--muted, #6b7280);
  line-height: 1.5;
  padding: 6px 10px;
  background: var(--bg-muted, #f9fafb);
  border-left: 3px solid var(--border, #e5e7eb);
  border-radius: 0 4px 4px 0;
}
[data-theme="dark"] .cite-ai-disclaimer {
  background: rgba(255,255,255,0.04);
  border-left-color: rgba(255,255,255,0.12);
}
```

- [ ] **Step 4: Verify**

Run the server (`python app.py`). Navigate to any tool page, run an analysis, click the Cite button. Confirm the disclaimer text appears between the citation text block and the Copy button. No JS changes needed — the disclaimer is static HTML.

- [ ] **Step 5: Commit**

```bash
git add "templates/base.html" "static/bibcrit.css"
git commit -m "feat: add AI disclaimer to cite modal

Adds a brief notice that analyses are AI-generated and should be verified
against primary sources before academic citation. Positioned between the
citation text and the Copy button so it cannot be missed.
"
```

---

## Task 2 — Patristic Training-Data Banner

**Why:** The Patristic Citations tool runs entirely on Claude's training knowledge — there is no patristic corpus loaded. The subtitle says "Trace how Church Fathers cited biblical passages" with no hint that the citations are AI-recalled, not drawn from a verified database. A user comparing a Church Father attribution against a critical edition might trust the wrong output.

**Files:**
- Modify: `templates/patristic.html` (after line 15)
- Modify: `data/i18n.json` (2 new keys)

- [ ] **Step 1: Add i18n keys to `data/i18n.json`**

In `data/i18n.json`, inside the `"en"` object, add after any existing patristic key:

```json
"patristic_corpus_notice": "No patristic corpus loaded — citations are drawn from Claude’s training knowledge (patristic literature through the 5th century). Verify all attributions and text forms against TLG, NPNF, and critical editions before relying on specific citations.",
```

Inside the `"es"` object, add the same key:

```json
"patristic_corpus_notice": "Sin corpus patrístico cargado — las citas provienen del conocimiento de entrenamiento de Claude (literatura patrística hasta el siglo V). Verifique todas las atribuciones y formas textuales en TLG, NPNF y ediciones críticas antes de confiar en citas específicas.",
```

- [ ] **Step 2: Insert banner in `templates/patristic.html`**

Find the tool-header block (lines 11–24):

```html
<!-- Tool header -->
<div class="tool-header">
  <h1 class="tool-title">{{ _t('patristic_tool_title') }}</h1>
  <p class="tool-subtitle" id="tool-subtitle">{{ _t('patristic_tool_subtitle') }}</p>
</div>
<script>
  document.addEventListener('DOMContentLoaded', function() {
    if (window.BibCritPersona) BibCritPersona.setToolSubtitle('patristic', {
```

Add the banner immediately after the closing `</div>` of `tool-header` and before `<script>`:

```html
<!-- Tool header -->
<div class="tool-header">
  <h1 class="tool-title">{{ _t('patristic_tool_title') }}</h1>
  <p class="tool-subtitle" id="tool-subtitle">{{ _t('patristic_tool_subtitle') }}</p>
</div>
<div class="bt-info-banner" style="margin-bottom:1rem;">
  <div class="bt-info-inner">
    <span class="material-symbols-outlined" style="font-size:16px;flex-shrink:0;margin-top:1px;">info</span>
    <span class="bt-info-text">{{ _t('patristic_corpus_notice') }}</span>
  </div>
</div>
<script>
```

- [ ] **Step 3: Verify**

Navigate to `/patristic`. Confirm the blue info banner appears below the subtitle, before the passage selector bar. Check `/patristic?lang=es` — confirms Spanish text renders.

- [ ] **Step 4: Commit**

```bash
git add "templates/patristic.html" "data/i18n.json"
git commit -m "feat: add training-data notice to Patristic Citations tool

Patristic corpus is not loaded; analysis draws on Claude training knowledge.
Adds a visible info banner warning users to verify attributions against TLG,
NPNF, and critical editions.
"
```

---

## Task 3 — STL Bridge Training-Data Banner

**Why:** Same issue as patristic. The Second Temple Literature Bridge (1 Enoch, Jubilees, Sirach, 4 Ezra, Tobit) has no corpus loaded. The subtitle mentions these texts as if BibCrit has indexed them. A scholar checking allusion directionality is working entirely from Claude's training recall, not a verified database of parallels.

**Files:**
- Modify: `templates/stl.html` (after line 11)
- Modify: `data/i18n.json` (2 new keys)

- [ ] **Step 1: Add i18n keys to `data/i18n.json`**

In `data/i18n.json`, inside the `"en"` object:

```json
"stl_corpus_notice": "No Second Temple Literature corpus loaded — allusions are drawn from Claude’s training knowledge. Verify all parallels against Charlesworth’s OTP, Nickelsburg, and VanderKam before treating results as definitive.",
```

Inside the `"es"` object:

```json
"stl_corpus_notice": "Sin corpus de Literatura del Segundo Templo cargado — las alusiones provienen del conocimiento de entrenamiento de Claude. Verifique todos los paralelos en la OTP de Charlesworth, Nickelsburg y VanderKam antes de tratar los resultados como definitivos.",
```

- [ ] **Step 2: Insert banner in `templates/stl.html`**

Find the tool-header block (lines 9–12):

```html
<div class="tool-header">
  <h1 class="tool-title">{{ _t('stl_tool_title') }}</h1>
  <p class="tool-subtitle">{{ _t('stl_tool_subtitle') }}</p>
</div>
```

Replace with:

```html
<div class="tool-header">
  <h1 class="tool-title">{{ _t('stl_tool_title') }}</h1>
  <p class="tool-subtitle">{{ _t('stl_tool_subtitle') }}</p>
</div>
<div class="bt-info-banner" style="margin-bottom:1rem;">
  <div class="bt-info-inner">
    <span class="material-symbols-outlined" style="font-size:16px;flex-shrink:0;margin-top:1px;">info</span>
    <span class="bt-info-text">{{ _t('stl_corpus_notice') }}</span>
  </div>
</div>
```

- [ ] **Step 3: Verify**

Navigate to `/stl`. Confirm banner appears. Check `/stl?lang=es` for Spanish. Confirm banner matches patristic visual style (same `.bt-info-banner` class).

- [ ] **Step 4: Commit**

```bash
git add "templates/stl.html" "data/i18n.json"
git commit -m "feat: add training-data notice to STL Bridge tool

No Second Temple Literature corpus is loaded. Adds info banner directing
users to verify allusions against Charlesworth's OTP and secondary literature.
"
```

---

## Task 4 — Source Criticism Contested-Framework Notice

**Why:** The source tool description says "grounded in Wellhausen, Friedman, and Baden" but presents J/E/D/P as the methodology, not one contested framework among several. The Documentary Hypothesis is influential but actively debated — neo-documentarian, Supplementary Hypothesis, and rhetorical-critical scholars would dispute many of its assignments. A student or PhD candidate may not realize they're reading one interpretive lens.

**Files:**
- Modify: `templates/source.html` (after line 15)
- Modify: `data/i18n.json` (2 new keys)

- [ ] **Step 1: Add i18n keys to `data/i18n.json`**

In the `"en"` object:

```json
"source_framework_notice": "Source criticism here applies the Documentary Hypothesis (J/E/D/P) — an influential but contested framework. Alternative models (Supplementary Hypothesis, neo-documentarian approaches, rhetorical criticism) assign layers differently. Results reflect one methodological lens, not a consensus position.",
```

In the `"es"` object:

```json
"source_framework_notice": "La crítica de fuentes aquí aplica la Hipótesis Documental (J/E/D/P) — un marco influyente pero debatido. Existen modelos alternativos (Hipótesis Suplementaria, enfoques neo-documentarios, crítica retórica) que asignan las capas de manera diferente. Los resultados reflejan una perspectiva metodológica, no una posición de consenso.",
```

- [ ] **Step 2: Insert notice in `templates/source.html`**

Find the tool-header block (lines 11–15):

```html
<!-- Tool header -->
<div class="tool-header">
  <h1 class="tool-title">{{ _t('source_tool_title') }}</h1>
  <p class="tool-subtitle">{{ _t('source_tool_subtitle') }}</p>
</div>
```

Replace with:

```html
<!-- Tool header -->
<div class="tool-header">
  <h1 class="tool-title">{{ _t('source_tool_title') }}</h1>
  <p class="tool-subtitle">{{ _t('source_tool_subtitle') }}</p>
</div>
<div class="bt-info-banner" style="margin-bottom:1rem;">
  <div class="bt-info-inner">
    <span class="material-symbols-outlined" style="font-size:16px;flex-shrink:0;margin-top:1px;">info</span>
    <span class="bt-info-text">{{ _t('source_framework_notice') }}</span>
  </div>
</div>
```

- [ ] **Step 3: Verify**

Navigate to `/source`. Confirm banner appears below subtitle. Check `/source?lang=es`. Confirm the banner text accurately conveys the contested nature of J/E/D/P without dismissing it.

- [ ] **Step 4: Commit**

```bash
git add "templates/source.html" "data/i18n.json"
git commit -m "feat: add contested-framework notice to Source Criticism tool

The Documentary Hypothesis is presented alongside alternative models.
Adds info banner clarifying J/E/D/P is one framework, not a consensus position.
"
```

---

## Task 5 — Surface `cached_at` Timestamp in Model Attribution

**Why:** The `cached_at` timestamp is already present in every SSE `done` payload (set by `claude_pipeline.py`). Currently only the model name is shown ("Performed by Claude Sonnet"). Users have no way to know if they're reading a fresh analysis or a 6-month-old cached result. Stale cached analyses may use an outdated model or a superseded understanding of a passage.

**Files to modify (8 JS files):**
- `static/apparatus.js`
- `static/backtranslation.js`
- `static/dss.js`
- `static/scribal.js`
- `static/genealogy.js`
- `static/patristic.js`
- `static/theological.js`
- `static/nt_ot.js`

**Pattern:** Each file already has `_friendlyModel(modelId)`. Add `_formatCached(isoStr)` near it, then append the date to every model attribution string.

- [ ] **Step 1: Add `_formatCached` helper — `static/apparatus.js`**

Find `_friendlyModel` in `apparatus.js` (line 868):

```javascript
  function _friendlyModel(modelId) {
    if (!modelId) return 'Claude';
    if (modelId.indexOf('opus')   !== -1) return 'Claude Opus';
    if (modelId.indexOf('sonnet') !== -1) return 'Claude Sonnet';
    if (modelId.indexOf('haiku')  !== -1) return 'Claude Haiku';
    return 'Claude';
  }
```

Add `_formatCached` immediately after it:

```javascript
  function _formatCached(isoStr) {
    if (!isoStr) return '';
    try {
      var d = new Date(isoStr);
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
    } catch (e) { return ''; }
  }
```

Then update the two `modelAttr` blocks. First occurrence (lines 249–253):

```javascript
          var modelAttr = document.getElementById('divergence-model-attr');
          if (modelAttr) {
            var _cachedDate = _formatCached(msg.data.cached_at);
            modelAttr.textContent = window.t('analysis_by', 'Analysis by') + ' ' + _friendlyModel(msg.data.model_version) + (_cachedDate ? ' · ' + _cachedDate : '');
            modelAttr.style.display = 'inline';
          }
```

Second occurrence (lines 349–353):

```javascript
    var modelAttr = document.getElementById('divergence-model-attr');
    if (modelAttr && currentData) {
      var _cachedDate = _formatCached(currentData.cached_at);
      modelAttr.textContent = window.t('analysis_by', 'Analysis by') + ' ' + _friendlyModel(currentData.model_version) + (_cachedDate ? ' · ' + _cachedDate : '');
      modelAttr.style.display = 'inline';
    }
```

- [ ] **Step 2: Same pattern in `static/backtranslation.js`**

Find `_friendlyModel` in `backtranslation.js` (around line 357) and add `_formatCached` after it (same code as above).

Update the two `modelAttr` blocks (lines 299–302 and 341–344):

```javascript
    var modelAttr = document.getElementById('bt-model-attr');
    if (modelAttr && _lastData.model_version) {
      var _cachedDate = _formatCached(_lastData.cached_at);
      modelAttr.textContent = window.t('analysis_by', 'Analysis by') + ' ' + _friendlyModel(_lastData.model_version) + (_cachedDate ? ' · ' + _cachedDate : '');
      modelAttr.style.display = 'inline';
    }
```

```javascript
    var modelAttr = document.getElementById('bt-model-attr');
    if (modelAttr && currentData) {
      var _cachedDate = _formatCached(currentData.cached_at);
      modelAttr.textContent = window.t('analysis_by', 'Analysis by') + ' ' + _friendlyModel(currentData.model_version) + (_cachedDate ? ' · ' + _cachedDate : '');
      modelAttr.style.display = 'inline';
    }
```

- [ ] **Step 3: `static/dss.js`**

Find `_friendlyModel` in `dss.js` and add `_formatCached` after it (same code).

Find line 952 (the inline HTML string):

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + '</p>' +
```

Replace with:

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + (_formatCached(data.cached_at) ? ' · ' + _esc(_formatCached(data.cached_at)) : '') + '</p>' +
```

- [ ] **Step 4: `static/scribal.js`**

Find `_friendlyModel` in `scribal.js` and add `_formatCached` after it.

There are two occurrences of the inline HTML pattern (lines 508 and 525). Update both:

```javascript
        '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(d.model_version)) + (_formatCached(d.cached_at) ? ' · ' + _esc(_formatCached(d.cached_at)) : '') + '</p>' +
```

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + (_formatCached(data.cached_at) ? ' · ' + _esc(_formatCached(data.cached_at)) : '') + '</p>' +
```

- [ ] **Step 5: `static/genealogy.js`**

Find `_friendlyModel` in `genealogy.js` and add `_formatCached` after it.

Find line 709 (inline HTML):

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + '</p>' +
```

Replace with:

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + (_formatCached(data.cached_at) ? ' · ' + _esc(_formatCached(data.cached_at)) : '') + '</p>' +
```

- [ ] **Step 6: `static/patristic.js`**

Find `_friendlyModel` in `patristic.js` and add `_formatCached` after it.

Find line 666 (inline HTML):

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + '</p>' +
```

Replace with:

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + (_formatCached(data.cached_at) ? ' · ' + _esc(_formatCached(data.cached_at)) : '') + '</p>' +
```

- [ ] **Step 7: `static/theological.js`**

Find `_friendlyModel` in `theological.js` and add `_formatCached` after it.

Find line 676 (inline HTML):

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + '</p>' +
```

Replace with:

```javascript
          '<p class="analysis-model-attr">Performed by ' + _esc(_friendlyModel(data.model_version)) + (_formatCached(data.cached_at) ? ' · ' + _esc(_formatCached(data.cached_at)) : '') + '</p>' +
```

- [ ] **Step 8: `static/nt_ot.js`**

Find `_friendlyModel` in `nt_ot.js` and add `_formatCached` after it.

Find lines 406–409 (`getElementById('nt-ot-model-attr')` block):

```javascript
    var modelAttr = document.getElementById('nt-ot-model-attr');
    if (modelAttr && data.model_version) {
      modelAttr.textContent = 'Analysis by ' + _friendlyModel(data.model_version);
      modelAttr.style.display = 'inline';
    }
```

Replace with:

```javascript
    var modelAttr = document.getElementById('nt-ot-model-attr');
    if (modelAttr && data.model_version) {
      var _cachedDate = _formatCached(data.cached_at);
      modelAttr.textContent = 'Analysis by ' + _friendlyModel(data.model_version) + (_cachedDate ? ' · ' + _cachedDate : '');
      modelAttr.style.display = 'inline';
    }
```

- [ ] **Step 9: Verify**

Run a fresh analysis (not cached) on any tool with model attribution. Confirm the attribution shows e.g. "Performed by Claude Sonnet · May 8, 2026". Then run the same passage again (now cached). The date should still appear — same format, same timestamp from cache. If `cached_at` is missing from a result (older cache entries), the date part is absent and only the model name shows — no crash.

- [ ] **Step 10: Commit**

```bash
git add "static/apparatus.js" "static/backtranslation.js" "static/dss.js" "static/scribal.js" "static/genealogy.js" "static/patristic.js" "static/theological.js" "static/nt_ot.js"
git commit -m "feat: show analysis date in model attribution footer

Surfaces the cached_at timestamp alongside the model name on all tools
that display model attribution. Format: 'Performed by Claude Sonnet · May 8, 2026'.
Date is omitted gracefully when cached_at is absent (older cache entries).
"
```

---

## Task 6 — Student Persona Academic Honesty Note

**Why:** The student persona hero says "No Hebrew or Greek required — AI explains everything in plain language" with no caution about academic integrity. A student who finds this via a Google search could run a passage, copy the output, and submit it as their own textual analysis. One sentence is enough — it doesn't need to be preachy — but it needs to be there.

**Files:**
- Modify: `templates/index.html` (student hero block, lines 365–380)
- Modify: `data/i18n.json` (2 new keys)

- [ ] **Step 1: Add i18n keys to `data/i18n.json`**

In the `"en"` object, add after existing student hero keys:

```json
"ph_student_honesty": "These are AI-generated starting points for learning — not finished academic arguments. Use them to understand a passage, then engage with your textbook and instructor.",
```

In the `"es"` object:

```json
"ph_student_honesty": "Estos son puntos de partida generados por IA — no argumentos académicos terminados. Úsalos para entender un pasaje y luego consulta tu libro de texto y tu instructor.",
```

- [ ] **Step 2: Insert the note in the student hero in `templates/index.html`**

Find the student hero block (lines 365–380):

```html
{# ══ STUDENT HERO ════════════════════════════════════════════════════════════ #}
<div class="persona-hero" data-persona="student">
  <div class="ph-inner">
    <div style="max-width:900px; margin:0 auto;">
      <div class="ph-eyebrow">{{ _t('ph_student_eyebrow') }}</div>
      <div class="ph-title">{{ _t('ph_student_title') | safe }}</div>
      <div class="ph-sub">{{ _t('ph_student_sub') }}</div>
      <div class="ph-badges">
        <span class="ph-badge accent">{{ _t('ph_student_badge_guide') }}</span>
        <span class="ph-badge accent">{{ _t('ph_student_badge_disc') }}</span>
        <span class="ph-badge">{{ _t('ph_student_badge_free') }}</span>
      </div>
    </div>
  </div>
  <div class="ph-tools-label">{{ _t('ph_student_tools_label') }}</div>
</div>
```

Replace with:

```html
{# ══ STUDENT HERO ════════════════════════════════════════════════════════════ #}
<div class="persona-hero" data-persona="student">
  <div class="ph-inner">
    <div style="max-width:900px; margin:0 auto;">
      <div class="ph-eyebrow">{{ _t('ph_student_eyebrow') }}</div>
      <div class="ph-title">{{ _t('ph_student_title') | safe }}</div>
      <div class="ph-sub">{{ _t('ph_student_sub') }}</div>
      <div class="ph-badges">
        <span class="ph-badge accent">{{ _t('ph_student_badge_guide') }}</span>
        <span class="ph-badge accent">{{ _t('ph_student_badge_disc') }}</span>
        <span class="ph-badge">{{ _t('ph_student_badge_free') }}</span>
      </div>
      <p class="ph-student-honesty">
        <span class="material-symbols-outlined" style="font-size:14px;vertical-align:-2px;margin-right:4px;opacity:0.8;">school</span>{{ _t('ph_student_honesty') }}
      </p>
    </div>
  </div>
  <div class="ph-tools-label">{{ _t('ph_student_tools_label') }}</div>
</div>
```

- [ ] **Step 3: Add CSS for `.ph-student-honesty`**

Find `.ph-sub` in `templates/index.html` inline styles or `bibcrit.css`. The student persona block styles are in the index.html `<style>` block. Add after the last student-persona rule in that block:

```css
.ph-student-honesty {
  margin: 12px 0 0;
  font-size: 12px;
  color: #065f46;
  opacity: 0.85;
  line-height: 1.5;
}
[data-theme="dark"] .ph-student-honesty {
  color: #6ee7b7;
}
```

- [ ] **Step 4: Verify**

Navigate to `/`. Select the Student persona. Confirm the academic honesty note appears below the badges in the green hero area. Check `/` with dark mode (`?theme=dark` or toggle). Check `/?lang=es` and select Student — Spanish text should render.

- [ ] **Step 5: Commit**

```bash
git add "templates/index.html" "data/i18n.json"
git commit -m "feat: add academic honesty note to student persona hero

Adds a one-sentence notice below badges in the student hero clarifying
these are AI-generated starting points, not finished academic arguments.
"
```

---

## Verification Checklist (run after all tasks)

- [ ] `/` → Student persona → honesty note visible below badges
- [ ] Any tool → run analysis → model attribution shows date: "Performed by Claude Sonnet · May 8, 2026"
- [ ] Cite modal → click "Cite this" → AI disclaimer visible between citation text and Copy button
- [ ] `/patristic` → blue info banner below subtitle
- [ ] `/stl` → blue info banner below subtitle
- [ ] `/source` → blue info banner below subtitle  
- [ ] `/?lang=es` + Student → Spanish honesty note
- [ ] `/patristic?lang=es` → Spanish banner
- [ ] `/stl?lang=es` → Spanish banner
- [ ] `/source?lang=es` → Spanish banner

---

## Self-Review Notes

**Placeholder scan:** None present. All code blocks are complete and runnable.

**Scope:** All changes are additive (new text, new CSS) except cached_at which modifies existing string building. No routes, models, or data structures changed.

**Type consistency:** `_formatCached` is defined identically in each JS file — same function name, same signature, same return type (string or empty string). No cross-file dependencies.

**What this plan does NOT cover (intentional deferrals):**
- Tools without any model attribution (numerical, chiasm, source, stl, targum, nt_text) — adding model attribution to those is a separate, larger task
- Meta descriptions and OG tags that over-promise (e.g. source.html's "Identify J, E, D, and P source layers" in meta_description) — SEO changes need separate consideration
- The Guide page's methodology section — prose edits, not in scope here
