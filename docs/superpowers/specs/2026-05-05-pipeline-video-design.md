# BibCrit Pipeline Explainer Video — Design Spec

## Goal

A 90-second Remotion video explaining how a single BibCrit verse analysis is generated — from user input through corpus lookup, cache check, Claude API call, SSE streaming, to structured output in the browser. Lives on the Guide page at bibcrit.app/guide.

## Style

**Hybrid: technical diagram dominant, brief UI demo at the end.**

- ~75% of runtime is an animated horizontal pipeline diagram with data snippets
- ~20% is a UI demo showing the real BibCrit interface with the result loading
- ~5% is title/outro cards
- No voiceover. Title cards and data snippets carry the narration.
- Ambient background music (no lyrics, low energy)
- Running example throughout: **Isaiah 7:14** (flagship BibCrit passage — MT/LXX divergence, real corpus data, cached result available)

## Composition

| Property | Value |
|---|---|
| ID | `PipelineExplainer` |
| Width | 1920px |
| Height | 1080px |
| FPS | 30 |
| Duration | 2700 frames (90s) |

Registered alongside `BibCritShowcase` in `video/src/Root.tsx`.

## Visual Design

- **Background**: `#0f1117` (matches BibCrit dark UI)
- **Primary accent**: `#6366f1` (indigo — active stage glow, arrows, highlights)
- **Secondary text**: `#94a3b8`
- **Code/data snippets**: monospace, `#a5b4fc` for values, `#475569` for labels
- **Active stage border glow**: `box-shadow: 0 0 20px #6366f133` + `border-color: #6366f1`
- **Cache hit green**: `#4ade80`
- **Cache miss amber**: `#f59e0b`

## Scene Breakdown

### S1 — Title card (90 frames / 3s)
BibCrit wordmark fades in on `#0f1117`. Subtitle fades in below: *"How a verse analysis is generated"*. Indigo accent line draws under the subtitle using `interpolate` on width.

### S2 — Pipeline overview (150 frames / 5s)
All 6 stage boxes appear one by one from left to right, each connected by an arrow that draws in after the box. No data snippets yet — establishes the full pipeline map the viewer will follow for the next 56 seconds.

Stages in order: **Input → Corpus → Cache → Claude → SSE → Output**

### S3 — ① User Input (240 frames / 8s)
- Input box border glows indigo
- Characters type into the passage field one by one: `"Isaiah 7:14"` (typewriter effect using `interpolate` on string slice)
- Tool selector label highlights: *MT/LXX Divergence Analyzer*
- Data snippet appears below the box: `{ ref: "Isaiah 7:14", tool: "divergence", lang: "en" }`

### S4 — ② Corpus Lookup (300 frames / 10s)
- Corpus box glows
- Two text rows fade in sequentially:
  - MT Hebrew (right-to-left, larger font): `הִנֵּה הָעַלְמָה הָרָה וְיֹלֶדֶת בֵּן` — source label: *ETCBC Leningrad Codex*
  - LXX Greek below: `ἰδοὺ ἡ παρθένος ἐν γαστρὶ ἕξει` — source label: *STEP Bible Vaticanus*
- Morphology highlight: `עַלְמָה` and `παρθένος` pulse with a small badge (*"young woman" vs "virgin"*)

### S5 — ③ Cache Check — fork (240 frames / 8s)
- Cache box glows
- SHA256 key computes character-by-character: `SHA256("Isaiah 7:14|divergence|v2|claude-sonnet…")`
- Arrow forks into two paths:
  - **Top (green)**: `⚡ Cache Hit → instant result` — flashes briefly (2s / 60 frames), fades
  - **Bottom (amber)**: `Cache Miss → Claude API` — stays lit, focus follows this path
- Label: *"Isaiah 7:14 is cached — but here's what happened on first request"*

### S6 — ④ Claude API (300 frames / 10s)
- Claude box glows
- Compressed prompt fragment scrolls upward — system role snippet, then user message with MT/LXX text injected
- Model badge appears: `claude-sonnet-4-5-20250929`
- Token counter ticks up: `~4,021 tokens`
- Cost label: `~$0.02`

### S7 — ⑤ SSE Stream (360 frames / 12s)
- SSE box glows
- Raw event lines scroll in the data snippet area:
  ```
  data: {"step": "checking_cache"}
  data: {"step": "generating"}
  data: {"done": true, "synthesis": "…", "key_divergences": […]}
  ```
- As each top-level JSON key arrives, its name appears and ticks a checklist:
  - `synthesis` ✓
  - `key_divergences` ✓
  - `transmission_history` ✓
  - `bibcrit_assessment` ✓
- Shows the streaming-first architecture clearly

### S8 — ⑥ Structured Output + cache write (240 frames / 8s)
- Output box glows
- JSON keys expand into readable section titles in the snippet
- Small badge pulses: *"Written to Supabase analysis_cache"*
- All 6 pipeline boxes glow simultaneously for ~1.5s — full pipeline lit, task complete

### S9 — Transition (120 frames / 4s)
- Diagram fades to 0 opacity
- Title card fades in: *"The result in your browser"*
- Dissolve into S10

### S10 — UI Demo (450 frames / 15s)
- BibCrit divergence page shown as a rendered mockup (built in Remotion, not a screenshot, so it animates cleanly)
- Passage bar shows `Isaiah 7:14`
- Analysis sections fade in one by one with the staggered reveal from the real app
- Subtle overlay labels connect back to the pipeline:
  - Arrow pointing to Synthesis section: *"← synthesis key from JSON"*
  - Arrow pointing to Key Divergences: *"← key_divergences array"*
- No heavy annotation — 2 labels max, small, tasteful

### S11 — Outro (210 frames / 7s)
- Clean dark background
- `bibcrit.app` URL fades in (large, indigo)
- Three badges appear below: `Open source` · `Free` · `No signup`
- BibCrit wordmark
- Fade to black

## Component Structure

```
video/src/
  compositions/
    PipelineExplainer/
      index.tsx              — root composition, scene sequencer
      scenes/
        S01_Title.tsx
        S02_PipelineOverview.tsx
        S03_UserInput.tsx
        S04_CorpusLookup.tsx
        S05_CacheCheck.tsx
        S06_ClaudeAPI.tsx
        S07_SSEStream.tsx
        S08_Output.tsx
        S09_Transition.tsx
        S10_UIDemo.tsx
        S11_Outro.tsx
      components/
        PipelineBox.tsx      — reusable stage box (label, glow, data snippet slot)
        Arrow.tsx            — animated connecting arrow
        DataSnippet.tsx      — monospace code block with fade-in lines
        Typewriter.tsx       — character-by-character text reveal
        ForkArrow.tsx        — branching arrow for cache hit/miss split
        UIFrame.tsx          — BibCrit UI mockup for S10
```

## Timing Constants

Defined in `PipelineExplainer/index.tsx` for easy adjustment:

```typescript
export const SCENES = {
  S1_START: 0,      S1_END: 90,
  S2_START: 90,     S2_END: 240,
  S3_START: 240,    S3_END: 480,
  S4_START: 480,    S4_END: 780,
  S5_START: 780,    S5_END: 1020,
  S6_START: 1020,   S6_END: 1320,
  S7_START: 1320,   S7_END: 1680,
  S8_START: 1680,   S8_END: 1920,
  S9_START: 1920,   S9_END: 2040,
  S10_START: 2040,  S10_END: 2490,
  S11_START: 2490,  S11_END: 2700,
} as const;
```

## Animation Principles

- All animations use `interpolate()` with `extrapolateRight: 'clamp'`
- Easing: `Easing.bezier(0.16, 1, 0.3, 1)` (ease-out spring) for reveals
- Easing: `Easing.linear` for typewriter and scrolling text
- No CSS animations, no CSS transitions (Remotion rule)
- Active stage: opacity `0 → 1` over 15 frames, border color transition via interpolated hex is NOT used — instead toggle between two static styles based on frame threshold
- Glow effect: box-shadow intensity interpolated `0 → 1 → 0` over active stage window

## Data Snippets — Exact Content

| Scene | Snippet |
|---|---|
| S3 | `{ ref: "Isaiah 7:14", tool: "divergence", lang: "en" }` |
| S4 MT | `הִנֵּה הָעַלְמָה הָרָה וְיֹלֶדֶת בֵּן` |
| S4 LXX | `ἰδοὺ ἡ παρθένος ἐν γαστρὶ ἕξει` |
| S5 | `SHA256("Isaiah 7:14\|divergence\|v2\|claude-sonnet…") → a3f9c2…` |
| S6 | `model: claude-sonnet-4-5-20250929 · tokens: 4,021 · ~$0.02` |
| S7 | `data: {"step":"generating"} … data: {"done":true,"synthesis":"…"}` |
| S8 | `✓ Written to Supabase analysis_cache` |

## Registration in Root.tsx

Add alongside existing `BibCritShowcase` composition:

```tsx
<Composition
  id="PipelineExplainer"
  component={PipelineExplainer}
  durationInFrames={2700}
  fps={30}
  width={1920}
  height={1080}
/>
```

## Out of Scope

- Voiceover or text-to-speech
- Captions/subtitles
- Mobile/portrait format (guide page is desktop-first)
- Animation of the actual BibCrit server code (S10 is a rendered mockup, not a screencast)
- Music selection (placeholder track, swap before publishing)
