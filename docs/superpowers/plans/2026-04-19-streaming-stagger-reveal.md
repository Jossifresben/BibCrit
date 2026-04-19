# Streaming Interface — Staggered Section Reveal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When analysis results arrive for the Targum Comparator and NT Textual Tradition Analyzer, reveal each result section one by one via the existing staggered CSS animation rather than showing everything at once.

**Architecture:** `staggerReveal(container, step)` is already defined in `result-actions.js` (loaded in `base.html`) and working correctly in 11 of 13 tools. The two new tools (`targum.js`, `nt_text.js`) never call it — their `renderResult()` function populates sections then calls `results.style.display = ''` with no animation. The fix is one line added to each file after `results` becomes visible. No CSS, no backend, no template changes needed.

**Tech Stack:** Vanilla JS, `window.staggerReveal` (already in `static/result-actions.js`), `section-reveal` CSS keyframe (already in `static/bibcrit.css`).

---

## Background

`staggerReveal(container, step)` applies `animation: sectionReveal 0.4s cubic-bezier(0.22, 1, 0.36, 1)` to each direct child of `container` with a staggered `animation-delay` of `i * step` ms (capped at 500 ms). Calling it with `step=90` reveals sections 90 ms apart: text columns → synthesis → fidelity/variants → theological modifications → assessment.

The function guards against `null` containers, so no null-check is needed at the call site.

Reference implementations to follow (both correct):
- `static/theological.js` line 267: `staggerReveal(results, 90);`
- `static/patristic.js` line 267: `staggerReveal(results, 90);`

---

## File Map

| File | Change |
|---|---|
| `static/targum.js` | Add `staggerReveal(results, 90);` after line 257 |
| `static/nt_text.js` | Add `staggerReveal(results, 90);` after line 228 |

No other files touched.

---

## Task 1 — Add staggered reveal to Targum Comparator

**Files:**
- Modify: `static/targum.js` (lines 255–260)

### Context

`renderResult()` in `targum.js` ends with:

```javascript
    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';

    _wireExport(data);
  }
```

`results` is `document.getElementById('targum-results')`. Its direct children in `templates/targum.html` are (in DOM order): `#text-columns`, `#synthesis-section`, `#fidelity-section`, `#theological-section`, `#expansions-section`, `#messianic-section`, `#lxx-align-section`, `#bibcrit-assessment`, `.export-row`. Sections with no data are left `display:none` by `renderResult()`; `staggerReveal` ignores them naturally because they're invisible.

- [ ] **Step 1: Open `static/targum.js` and locate the end of `renderResult()`**

Find this block (around line 255):
```javascript
    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';

    _wireExport(data);
  }
```

- [ ] **Step 2: Add the staggerReveal call**

Replace the block with:
```javascript
    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';
    staggerReveal(results, 90);

    _wireExport(data);
  }
```

- [ ] **Step 3: Verify in browser**

1. Start the dev server: `cd "/Users/jfresco16/Google Drive/Claude/BibCrit" && python app.py`
2. Open `http://localhost:5001/targum?ref=Genesis+22%3A8`
3. Click Analyze (or wait for auto-trigger)
4. When results arrive, each section should fade in from translateY(10px) with ~90 ms between sections — text columns first, then synthesis, then fidelity, then modifications, then assessment. The whole sequence takes under 1 second.
5. Reload and re-run to confirm the animation fires on cache hits too.

Expected: sections slide in sequentially, not all at once.
Not expected: all content appears as a single block.

- [ ] **Step 4: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add static/targum.js
git commit -m "feat(targum): add staggered section reveal on result render

Calls staggerReveal(results, 90) at the end of renderResult() so
sections animate in sequence (90 ms apart) rather than appearing
all at once. Matches the pattern used in theological.js and patristic.js.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2 — Add staggered reveal to NT Textual Tradition Analyzer

**Files:**
- Modify: `static/nt_text.js` (lines 226–230)

### Context

`renderResult()` in `nt_text.js` ends with:

```javascript
    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';
    _wireExport(data);
  }
```

`results` is `document.getElementById('nt-text-results')`. Its direct children in `templates/nt_text.html` are (in DOM order): `#gnt-text-display`, `#metzger-section`, `#ms-families-section`, `#variant-section`, `#disputed-section`, `#synthesis-section`, `#bibcrit-assessment`, `.export-row`.

- [ ] **Step 1: Open `static/nt_text.js` and locate the end of `renderResult()`**

Find this block (around line 226):
```javascript
    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';
    _wireExport(data);
  }
```

- [ ] **Step 2: Add the staggerReveal call**

Replace the block with:
```javascript
    var exportRow = document.getElementById('export-row');
    if (exportRow) exportRow.style.display = '';
    if (results)   results.style.display   = '';
    staggerReveal(results, 90);
    _wireExport(data);
  }
```

- [ ] **Step 3: Verify in browser**

1. Open `http://localhost:5001/nt-text?ref=John+7%3A53-8%3A11`
2. Click Analyze
3. When results arrive: GNT text section appears first, then Metzger rating, then manuscript families, then variant register, then synthesis, then assessment — each ~90 ms apart.
4. Also test a NT passage with a disputed section (John 7:53–8:11, Mark 16:9–20) to confirm the disputed passage section also animates correctly when present.

Expected: sections slide in sequentially.
Not expected: all sections appear simultaneously.

- [ ] **Step 4: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add static/nt_text.js
git commit -m "feat(nt-text): add staggered section reveal on result render

Calls staggerReveal(results, 90) at the end of renderResult() so
GNT text → Metzger rating → manuscript families → variant register
→ synthesis → assessment animate in sequence.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Verification checklist

After both tasks are done, confirm the following in a browser:

- [ ] `/targum` — sections animate sequentially on first load (uncached)
- [ ] `/targum` — sections animate sequentially on cache hit (instant result)
- [ ] `/nt-text` — sections animate sequentially on first load
- [ ] `/nt-text` — sections animate sequentially on cache hit
- [ ] Switching to `?lang=es` on both pages — animation still fires (translation path also calls `renderResult`)
- [ ] No console errors on either page

No push / no release tag needed — these are `feat` commits that will ship in the v3.1 milestone.

---

## Out of scope (v3.1+)

The four tools that currently use `staggerReveal(container, 0)` (whole-container fade rather than per-section stagger) — `apparatus.js` (Divergence), `backtranslation.js`, `scribal.js`, `numerical.js` — are excluded from this plan. Their tab/chart-based layouts make section-level stagger structurally different and are tracked separately.
