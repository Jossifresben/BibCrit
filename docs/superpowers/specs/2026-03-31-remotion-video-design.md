# BibCrit Remotion Video — Design Spec

**Date:** 2026-03-31
**Author:** Jossi Fresco Benaim
**Status:** Approved

---

## Overview

A 90-second showcase video built with [Remotion](https://www.remotion.dev/) (React-based programmatic video). Targets researchers and academics. Shows all 8 BibCrit tools via animated React mockups using the BibCrit native palette. No voiceover — music only (BibCrit.mp3, trimmed to 90s).

---

## Technical Setup

| Item | Value |
|---|---|
| Framework | Remotion 4.x |
| Language | TypeScript + React |
| Resolution | 1920×1080 (16:9) |
| Frame rate | 30 fps |
| Total frames | 2700 (90s × 30fps) |
| Output | MP4 via `npx remotion render` |
| Location | `video/` directory at repo root |
| Audio | `~/Downloads/BibCrit.mp3` — copied to `video/public/BibCrit.mp3`, fades out at 88s |

---

## Visual Style

- **Background:** BibCrit parchment `#f8f6f0`
- **Card background:** `#ffffff` with `1px solid #d4d0c8` border
- **Primary font:** Space Grotesk (same as app)
- **Transitions:** 0.4s cross-dissolve (12-frame interpolation) between every scene
- **Tool name label:** slides up from `translateY(20px)` → `translateY(0)`, `opacity 0→1`, at 60% through each scene
- **All animations:** driven by Remotion's `interpolate()` — no CSS keyframes

---

## Scene Structure

### Scene 0 — Intro · frames 0–180 (0–6s)

- BibCrit `✦` logo fades in center, scale `0.8 → 1.0`
- Tagline types in character by character: **"Biblical Textual Criticism"**
- Background: parchment `#f8f6f0`

---

### Scene 1 — MT/LXX Divergence Analyzer · frames 180–450 (6–15s)

**Mockup:** Two-column parallel text panel
- Left column header: `MT` (amber badge)
- Right column header: `LXX` (blue badge)
- 4–5 text rows appear sequentially, each row reveals a divergence badge (`ADDITION`, `LEXICAL`, `THEOLOGICAL`) that pops in with a spring animation
- Tool name slides up at frame 390

---

### Scene 2 — DSS Bridge Tool · frames 450–720 (15–24s)

**Mockup:** Stacked manuscript cards
- 3 cards expand open in sequence: `1QIsaᵃ`, `4QIsaᵃ`, `4QIsaᵇ`
- Each card reveals alignment badge: `MT` (amber), `LXX` (blue), `IND` (orange)
- Tool name slides up at frame 660

---

### Scene 3 — Back-Translation Workbench · frames 720–990 (24–33s)

**Mockup:** Three-column word grid
- Columns: `LXX Greek` → `Vorlage (Hebrew)` → `MT Hebrew`
- Words appear left to right; Vorlage words colour-coded green (`AGREES MT`), red (`UNATTESTED`), grey (`GREEK IDIOM`)
- Tool name slides up at frame 930

---

### Scene 4 — Scribal Tendency Profiler · frames 990–1260 (33–42s)

**Mockup:** Radar chart
- 5-axis radar draws from centre outward (stroke animation)
- Axis labels appear one by one: Literalness, Anthropomorphism, Messianic, Harmonization, Paraphrase
- Filled polygon fades in after axes complete
- Tool name slides up at frame 1200

---

### Scene 5 — Numerical Discrepancy Modeler · frames 1260–1530 (42–51s)

**Mockup:** Number comparison panel
- Three large number chips appear: `MT 130`, `LXX 230`, `SP 130` (Genesis 5 Mahalalel)
- A horizontal timeline bar fills left to right beneath them
- Tool name slides up at frame 1470

---

### Scene 6 — Theological Revision Detector · frames 1530–1800 (51–60s)

**Mockup:** Revision cards
- 3 cards flip/slide in: `Anthropomorphism Avoidance`, `Messianic Heightening`, `Harmonization`
- Each card shows tradition badge (LXX blue, Targum green, Vulgate red)
- Tool name slides up at frame 1740

---

### Scene 7 — Patristic Citation Tracker · frames 1800–2070 (60–69s)

**Mockup:** Citation cards + distribution bar
- Distribution bar fills left to right, segmented by tradition colour
- 3 citation cards appear beneath: `Origen`, `Justin Martyr`, `Irenaeus` with text-form badges
- Tool name slides up at frame 2010

---

### Scene 8 — Manuscript Genealogy · frames 2070–2430 (69–81s)

**Mockup:** Stemma tree (12 seconds — visual payoff, longest scene)
- Nodes appear top-down: Proto-Hebrew → MT / LXX / DSS → terminal manuscripts
- Edges draw themselves as SVG path animations after each node appears
- Colour-coded nodes: amber (MT), blue (LXX), purple (DSS), grey (translations)
- Tool name slides up at frame 2370

---

### Scene 9 — Outro · frames 2430–2700 (81–90s)

- Background fades to dark `#1a1a1a`
- **`bibcrit.app`** fades in large, centered (font-size 72px, white)
- Below: `"Open access · 8 tools · Powered by Claude"` fades in (font-size 18px, `#94a3b8`)
- Music fade-out: frames 2640–2700 (88–90s), volume `1.0 → 0`
- Hold on black last 10 frames

---

## File Structure

```
video/
├── package.json
├── remotion.config.ts
├── public/
│   └── BibCrit.mp3
└── src/
    ├── Root.tsx              # Remotion composition registration
    ├── BibCritVideo.tsx      # Main sequence, scene routing
    ├── scenes/
    │   ├── Intro.tsx
    │   ├── SceneDivergence.tsx
    │   ├── SceneDSS.tsx
    │   ├── SceneBackTranslation.tsx
    │   ├── SceneScribal.tsx
    │   ├── SceneNumerical.tsx
    │   ├── SceneTheological.tsx
    │   ├── ScenePatristic.tsx
    │   ├── SceneGenealogy.tsx
    │   └── Outro.tsx
    ├── components/
    │   ├── ToolLabel.tsx     # Sliding tool name label (shared)
    │   ├── TraditionBadge.tsx # MT/LXX/DSS/SP colour badges (shared)
    │   ├── CrossDissolve.tsx  # Transition wrapper (shared)
    │   └── RadarChart.tsx     # SVG radar for scribal scene
    └── theme.ts              # Palette, fonts, timing constants
```

---

## Shared `theme.ts` Constants

```ts
export const PALETTE = {
  parchment: '#f8f6f0',
  border: '#d4d0c8',
  mt: '#c0892a',
  lxx: '#1e40af',
  dss: '#7c3aed',
  sp: '#2c7c5f',
  targum: '#27ae60',
  vulgate: '#c0392b',
  dark: '#1a1a1a',
};

export const TIMING = {
  fps: 30,
  transition: 12,      // frames for cross-dissolve
  labelReveal: 0.6,    // fraction through scene when tool label slides up
};
```

---

## Rendering

```bash
cd video
npm install
npx remotion render src/Root.tsx BibCritShowcase out/bibcrit-showcase.mp4
```

Output: `video/out/bibcrit-showcase.mp4` (~15–30MB H.264)

---

## Out of Scope

- No voiceover recording
- No captions/subtitles (can be added later)
- No localization
- No CI/CD render pipeline
- Spanish version deferred
