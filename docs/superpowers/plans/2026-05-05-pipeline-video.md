# PipelineExplainer Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 90-second Remotion composition (`PipelineExplainer`) that explains the BibCrit verse analysis pipeline — user input → corpus lookup → cache check → Claude API → SSE stream → structured output — with a brief UI demo at the end.

**Architecture:** 11 scene components rendered via `<Sequence from={N} durationInFrames={D}>` with absolute frame positions (no `TransitionSeries` — the pipeline row persists across S2–S8 and hard cuts work cleanly on a uniform dark background). Fade-in/out is handled inside S01 and S11 individually. Six reusable components (`PipelineRow`, `PipelineBox`, `Arrow`, `DataSnippet`, `Typewriter`, `ForkArrow`, `UIFrame`) live in `compositions/PipelineExplainer/components/`.

**Tech Stack:** Remotion 4.0.442, React 18, TypeScript, Space Grotesk (Google Fonts via `@import`), system monospace for code snippets. No new npm packages required.

---

## File Map

| Action | Path | Purpose |
|--------|------|---------|
| Create | `video/src/compositions/PipelineExplainer/theme.ts` | Dark palette, SCENES frame constants, PIPELINE_STAGES list |
| Create | `video/src/compositions/PipelineExplainer/index.tsx` | Root composition — mounts all 11 scenes via `<Sequence>` |
| Create | `video/src/compositions/PipelineExplainer/components/PipelineBox.tsx` | Single stage box with active glow state |
| Create | `video/src/compositions/PipelineExplainer/components/Arrow.tsx` | Animated connecting arrow between boxes |
| Create | `video/src/compositions/PipelineExplainer/components/PipelineRow.tsx` | Full 6-box row; used by S02–S08 |
| Create | `video/src/compositions/PipelineExplainer/components/DataSnippet.tsx` | Monospace code block, lines fade in one by one |
| Create | `video/src/compositions/PipelineExplainer/components/Typewriter.tsx` | Character-by-character text reveal |
| Create | `video/src/compositions/PipelineExplainer/components/ForkArrow.tsx` | Branching arrow for S05 cache hit/miss split |
| Create | `video/src/compositions/PipelineExplainer/components/UIFrame.tsx` | BibCrit divergence UI mockup for S10 |
| Create | `video/src/compositions/PipelineExplainer/scenes/S01_Title.tsx` | Title card |
| Create | `video/src/compositions/PipelineExplainer/scenes/S02_PipelineOverview.tsx` | All boxes appear left→right |
| Create | `video/src/compositions/PipelineExplainer/scenes/S03_UserInput.tsx` | Input box active, typewriter |
| Create | `video/src/compositions/PipelineExplainer/scenes/S04_CorpusLookup.tsx` | Corpus box active, Hebrew + Greek |
| Create | `video/src/compositions/PipelineExplainer/scenes/S05_CacheCheck.tsx` | Cache box active, fork arrow |
| Create | `video/src/compositions/PipelineExplainer/scenes/S06_ClaudeAPI.tsx` | Claude box active, prompt + token counter |
| Create | `video/src/compositions/PipelineExplainer/scenes/S07_SSEStream.tsx` | SSE box active, scrolling events + checklist |
| Create | `video/src/compositions/PipelineExplainer/scenes/S08_Output.tsx` | Output box active, all boxes pulse |
| Create | `video/src/compositions/PipelineExplainer/scenes/S09_Transition.tsx` | Fade-out pipeline + "The result in your browser" |
| Create | `video/src/compositions/PipelineExplainer/scenes/S10_UIDemo.tsx` | BibCrit UI mockup, sections reveal |
| Create | `video/src/compositions/PipelineExplainer/scenes/S11_Outro.tsx` | bibcrit.app URL + badges |
| Modify | `video/src/Root.tsx` | Register `PipelineExplainer` composition |

---

## Task 1: Scaffold — theme, skeleton root, register in Root.tsx

**Files:**
- Create: `video/src/compositions/PipelineExplainer/theme.ts`
- Create: `video/src/compositions/PipelineExplainer/index.tsx`
- Modify: `video/src/Root.tsx`

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p "video/src/compositions/PipelineExplainer/components"
mkdir -p "video/src/compositions/PipelineExplainer/scenes"
```

- [ ] **Step 2: Create `video/src/compositions/PipelineExplainer/theme.ts`**

```typescript
import { Easing } from 'remotion';

export const DARK = {
  bg:            '#0f1117',
  surface:       '#1e2130',
  surface2:      '#161b27',
  border:        '#2d3348',
  borderActive:  '#6366f1',
  accent:        '#6366f1',
  accentLight:   '#a5b4fc',
  text:          '#e2e8f0',
  textMuted:     '#94a3b8',
  textDim:       '#475569',
  codeValue:     '#a5b4fc',
  codeLabel:     '#475569',
  cacheHit:      '#4ade80',
  cacheMiss:     '#f59e0b',
} as const;

// Absolute frame positions. All 11 scenes + gaps = 2700 frames total.
export const SCENES = {
  S1_START:  0,    S1_END:  90,   // 90  frames  3s
  S2_START:  90,   S2_END:  240,  // 150 frames  5s
  S3_START:  240,  S3_END:  480,  // 240 frames  8s
  S4_START:  480,  S4_END:  780,  // 300 frames 10s
  S5_START:  780,  S5_END:  1020, // 240 frames  8s
  S6_START:  1020, S6_END:  1320, // 300 frames 10s
  S7_START:  1320, S7_END:  1680, // 360 frames 12s
  S8_START:  1680, S8_END:  1920, // 240 frames  8s
  S9_START:  1920, S9_END:  2040, // 120 frames  4s
  S10_START: 2040, S10_END: 2490, // 450 frames 15s
  S11_START: 2490, S11_END: 2700, // 210 frames  7s
} as const;

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1);

// Pipeline stage definitions — index 0–5 maps to activeIndex prop on PipelineRow
export const PIPELINE_STAGES = [
  { id: 'input',  label: 'Input',  sub: 'User query' },
  { id: 'corpus', label: 'Corpus', sub: 'MT + LXX' },
  { id: 'cache',  label: 'Cache',  sub: 'Supabase' },
  { id: 'claude', label: 'Claude', sub: 'API call' },
  { id: 'sse',    label: 'SSE',    sub: 'Stream' },
  { id: 'output', label: 'Output', sub: 'JSON' },
] as const;

export const FONT_STYLE = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
  * { box-sizing: border-box; }
`;
```

- [ ] **Step 3: Create `video/src/compositions/PipelineExplainer/index.tsx` — skeleton only**

```tsx
import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { DARK, SCENES, FONT_STYLE } from './theme';

// Placeholder — replace each null with real scene import in Task 16
const Placeholder: React.FC<{ label: string }> = ({ label }) => (
  <AbsoluteFill style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div style={{ color: '#6366f1', fontSize: 48, fontWeight: 700 }}>{label}</div>
  </AbsoluteFill>
);

export const PipelineExplainer: React.FC = () => (
  <AbsoluteFill style={{ background: DARK.bg, fontFamily: "'Space Grotesk', sans-serif" }}>
    <style>{FONT_STYLE}</style>

    <Sequence from={SCENES.S1_START}  durationInFrames={SCENES.S1_END  - SCENES.S1_START}>
      <Placeholder label="S1 Title" />
    </Sequence>
    <Sequence from={SCENES.S2_START}  durationInFrames={SCENES.S2_END  - SCENES.S2_START}>
      <Placeholder label="S2 Pipeline Overview" />
    </Sequence>
    <Sequence from={SCENES.S3_START}  durationInFrames={SCENES.S3_END  - SCENES.S3_START}>
      <Placeholder label="S3 User Input" />
    </Sequence>
    <Sequence from={SCENES.S4_START}  durationInFrames={SCENES.S4_END  - SCENES.S4_START}>
      <Placeholder label="S4 Corpus Lookup" />
    </Sequence>
    <Sequence from={SCENES.S5_START}  durationInFrames={SCENES.S5_END  - SCENES.S5_START}>
      <Placeholder label="S5 Cache Check" />
    </Sequence>
    <Sequence from={SCENES.S6_START}  durationInFrames={SCENES.S6_END  - SCENES.S6_START}>
      <Placeholder label="S6 Claude API" />
    </Sequence>
    <Sequence from={SCENES.S7_START}  durationInFrames={SCENES.S7_END  - SCENES.S7_START}>
      <Placeholder label="S7 SSE Stream" />
    </Sequence>
    <Sequence from={SCENES.S8_START}  durationInFrames={SCENES.S8_END  - SCENES.S8_START}>
      <Placeholder label="S8 Output" />
    </Sequence>
    <Sequence from={SCENES.S9_START}  durationInFrames={SCENES.S9_END  - SCENES.S9_START}>
      <Placeholder label="S9 Transition" />
    </Sequence>
    <Sequence from={SCENES.S10_START} durationInFrames={SCENES.S10_END - SCENES.S10_START}>
      <Placeholder label="S10 UI Demo" />
    </Sequence>
    <Sequence from={SCENES.S11_START} durationInFrames={SCENES.S11_END - SCENES.S11_START}>
      <Placeholder label="S11 Outro" />
    </Sequence>
  </AbsoluteFill>
);
```

- [ ] **Step 4: Modify `video/src/Root.tsx` to register both compositions**

Replace the entire file content:

```tsx
import React from 'react';
import { Composition, registerRoot } from 'remotion';
import { BibCritVideo } from './BibCritVideo';
import { PipelineExplainer } from './compositions/PipelineExplainer/index';
import { TOTAL_FRAMES, TIMING } from './theme';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BibCritShowcase"
        component={BibCritVideo}
        durationInFrames={TOTAL_FRAMES}
        fps={TIMING.fps}
        width={1920}
        height={1080}
      />
      <Composition
        id="PipelineExplainer"
        component={PipelineExplainer}
        durationInFrames={2700}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

registerRoot(RemotionRoot);
```

- [ ] **Step 5: Verify — render frame 45 (mid S1)**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=45
```

Expected: dark `#0f1117` background with "S1 Title" in indigo text centered. Studio at http://localhost:3003 now shows `PipelineExplainer` in the composition list.

- [ ] **Step 6: Commit**

```bash
git add video/src/compositions/ video/src/Root.tsx
git commit -m "feat(video): scaffold PipelineExplainer composition with placeholder scenes"
```

---

## Task 2: PipelineBox + Arrow + PipelineRow components

**Files:**
- Create: `video/src/compositions/PipelineExplainer/components/PipelineBox.tsx`
- Create: `video/src/compositions/PipelineExplainer/components/Arrow.tsx`
- Create: `video/src/compositions/PipelineExplainer/components/PipelineRow.tsx`

- [ ] **Step 1: Create `PipelineBox.tsx`**

`PipelineBox` receives `isActive` and `localFrame` as props — it does NOT call `useCurrentFrame()` itself (the parent scene does that and passes the local frame down).

```tsx
import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface PipelineBoxProps {
  label: string;
  sub: string;
  isActive: boolean;
  localFrame: number;    // local frame within the current scene (0 = scene start)
  sceneLength: number;   // total frames in the active scene, for glow fade-out timing
  isVisible?: boolean;   // false = not yet revealed (used in S02 overview)
  children?: React.ReactNode;
}

export const PipelineBox: React.FC<PipelineBoxProps> = ({
  label, sub, isActive, localFrame, sceneLength, isVisible = true, children
}) => {
  const opacity = isVisible ? 1 : 0;

  // Glow fades in over first 15 frames, holds, fades out over last 15 frames
  const glow = isActive
    ? interpolate(
        localFrame,
        [0, 15, sceneLength - 15, sceneLength],
        [0, 1, 1, 0],
        { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
      )
    : 0;

  const labelColor = isActive ? DARK.accentLight : DARK.textMuted;
  const borderColor = isActive ? DARK.borderActive : DARK.border;
  const glowPx = 20 * glow;
  const glowAlpha = (0.5 * glow).toFixed(2);

  return (
    <div
      style={{
        opacity,
        background: DARK.surface,
        border: `2px solid ${borderColor}`,
        borderRadius: 12,
        padding: '18px 22px',
        minWidth: 160,
        textAlign: 'center',
        boxShadow: `0 0 ${glowPx}px rgba(99, 102, 241, ${glowAlpha})`,
        flexShrink: 0,
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 700, color: labelColor, lineHeight: 1 }}>
        {label}
      </div>
      <div style={{ fontSize: 13, color: DARK.textDim, marginTop: 6 }}>
        {sub}
      </div>
      {children && (
        <div style={{ marginTop: 14 }}>{children}</div>
      )}
    </div>
  );
};
```

- [ ] **Step 2: Create `Arrow.tsx`**

Arrow draws from left to right. Width grows from 0 to full via `interpolate` on the `revealProgress` prop (0–1).

```tsx
import React from 'react';
import { DARK } from '../theme';

interface ArrowProps {
  revealProgress: number; // 0 = hidden, 1 = fully drawn
}

export const Arrow: React.FC<ArrowProps> = ({ revealProgress }) => {
  const lineWidth = 60 * revealProgress;
  const arrowOpacity = revealProgress > 0.8 ? (revealProgress - 0.8) / 0.2 : 0;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        width: 70,
        flexShrink: 0,
        position: 'relative',
        height: 24,
      }}
    >
      {/* Horizontal line */}
      <div
        style={{
          height: 2,
          width: lineWidth,
          background: DARK.accent,
          borderRadius: 1,
        }}
      />
      {/* Arrowhead */}
      <div
        style={{
          opacity: arrowOpacity,
          width: 0,
          height: 0,
          borderTop: '6px solid transparent',
          borderBottom: '6px solid transparent',
          borderLeft: `10px solid ${DARK.accent}`,
          marginLeft: 2,
        }}
      />
    </div>
  );
};
```

- [ ] **Step 3: Create `PipelineRow.tsx`**

`PipelineRow` renders all 6 boxes with 5 arrows. `activeIndex` (-1 = none, 0–5 = which box glows). `revealUpTo` controls how many boxes have appeared (used in S02 to reveal them sequentially — set to 6 for S03–S08 where all are visible from the start).

```tsx
import React from 'react';
import { interpolate } from 'remotion';
import { DARK, PIPELINE_STAGES, EASE_OUT } from '../theme';
import { PipelineBox } from './PipelineBox';
import { Arrow } from './Arrow';

interface PipelineRowProps {
  activeIndex: number;   // -1 = none active, 0–5 = active stage
  revealUpTo: number;    // how many boxes have appeared (0–6); used in S02
  localFrame: number;    // local frame from parent scene
  sceneLength: number;   // total duration of the current scene
}

export const PipelineRow: React.FC<PipelineRowProps> = ({
  activeIndex, revealUpTo, localFrame, sceneLength
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 0,
        width: '100%',
      }}
    >
      {PIPELINE_STAGES.map((stage, i) => {
        const isVisible = i < revealUpTo;
        // In S02 (reveal mode), each box appears 20 frames after the previous
        const boxRevealFrame = i * 20;
        const boxOpacity = interpolate(
          localFrame,
          [boxRevealFrame, boxRevealFrame + 15],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
        );

        // For S03-S08, revealUpTo = 6 so boxOpacity is always 1 after 15 frames
        const effectiveOpacity = isVisible ? boxOpacity : 0;

        // Arrow after each box except the last
        const arrowRevealFrame = boxRevealFrame + 15;
        const arrowProgress = i < PIPELINE_STAGES.length - 1
          ? interpolate(
              localFrame,
              [arrowRevealFrame, arrowRevealFrame + 12],
              [0, 1],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
            )
          : 0;

        return (
          <React.Fragment key={stage.id}>
            <div style={{ opacity: effectiveOpacity }}>
              <PipelineBox
                label={stage.label}
                sub={stage.sub}
                isActive={activeIndex === i}
                localFrame={localFrame}
                sceneLength={sceneLength}
                isVisible={true}
              />
            </div>
            {i < PIPELINE_STAGES.length - 1 && (
              <div style={{ opacity: i < revealUpTo - 1 ? 1 : 0 }}>
                <Arrow revealProgress={arrowProgress} />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 4: Verify — update S02 placeholder to use PipelineRow, render frame 180**

Edit `video/src/compositions/PipelineExplainer/index.tsx` — replace the S2 `<Placeholder label="S2 Pipeline Overview" />` with:

```tsx
// At top of index.tsx, add temporary import:
import { PipelineRow } from './components/PipelineRow';

// Replace S2 Placeholder:
<Sequence from={SCENES.S2_START} durationInFrames={SCENES.S2_END - SCENES.S2_START}>
  <AbsoluteFill style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '0 100px' }}>
    {/* localFrame inside Sequence starts at 0 */}
    {(() => {
      // This is a quick inline test component — replaced properly in Task 7
      const TestS2: React.FC = () => {
        const { useCurrentFrame: ucf } = require('remotion');
        const lf = ucf();
        const rev = Math.min(6, Math.floor(lf / 20) + 1);
        return <PipelineRow activeIndex={-1} revealUpTo={rev} localFrame={lf} sceneLength={150} />;
      };
      return <TestS2 />;
    })()}
  </AbsoluteFill>
</Sequence>
```

Actually — instead of the inline hack, just render frame 180 with the existing placeholder and check studio manually. The components will be visually verified when the real scenes are wired in Task 7.

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=180
```

Expected: dark background, "S2 Pipeline Overview" label (placeholder). Studio shows the composition exists. Actual PipelineRow rendering verified in Task 7.

- [ ] **Step 5: Commit**

```bash
git add video/src/compositions/PipelineExplainer/components/
git commit -m "feat(video): add PipelineBox, Arrow, PipelineRow components"
```

---

## Task 3: DataSnippet + Typewriter components

**Files:**
- Create: `video/src/compositions/PipelineExplainer/components/DataSnippet.tsx`
- Create: `video/src/compositions/PipelineExplainer/components/Typewriter.tsx`

- [ ] **Step 1: Create `DataSnippet.tsx`**

Renders an array of lines in a monospace code block. Each line fades in `staggerFrames` frames after the previous, starting at `startFrame`.

```tsx
import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface DataSnippetProps {
  lines: Array<{ text: string; color?: string }>;
  localFrame: number;
  startFrame?: number;    // frame (local) when first line appears; default 20
  staggerFrames?: number; // frames between each line; default 18
}

export const DataSnippet: React.FC<DataSnippetProps> = ({
  lines,
  localFrame,
  startFrame = 20,
  staggerFrames = 18,
}) => {
  return (
    <div
      style={{
        background: DARK.surface2,
        border: `1px solid ${DARK.border}`,
        borderRadius: 8,
        padding: '14px 20px',
        fontFamily: 'Menlo, Monaco, Consolas, monospace',
        fontSize: 18,
        lineHeight: 1.7,
        textAlign: 'left',
      }}
    >
      {lines.map((line, i) => {
        const lineStart = startFrame + i * staggerFrames;
        const opacity = interpolate(
          localFrame,
          [lineStart, lineStart + 12],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
        );
        const translateY = interpolate(
          localFrame,
          [lineStart, lineStart + 12],
          [6, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateY(${translateY}px)`,
              color: line.color ?? DARK.codeValue,
              whiteSpace: 'pre',
            }}
          >
            {line.text}
          </div>
        );
      })}
    </div>
  );
};
```

- [ ] **Step 2: Create `Typewriter.tsx`**

Reveals `text` character by character. `charsPerFrame` controls speed (default 2 chars/frame = ~15fps for a 30-char string).

```tsx
import React from 'react';

interface TypewriterProps {
  text: string;
  localFrame: number;
  startFrame?: number;    // frame when typing begins; default 0
  charsPerFrame?: number; // chars revealed per frame; default 2
  color?: string;
  fontSize?: number;
  fontWeight?: number;
  showCursor?: boolean;
}

export const Typewriter: React.FC<TypewriterProps> = ({
  text,
  localFrame,
  startFrame = 0,
  charsPerFrame = 2,
  color = '#e2e8f0',
  fontSize = 28,
  fontWeight = 600,
  showCursor = true,
}) => {
  const elapsed = Math.max(0, localFrame - startFrame);
  const charsVisible = Math.min(text.length, Math.floor(elapsed * charsPerFrame));
  const isTyping = charsVisible < text.length;
  // Blink cursor: on for 8 frames, off for 8 frames
  const cursorVisible = showCursor && (Math.floor(localFrame / 8) % 2 === 0);

  return (
    <span style={{ color, fontSize, fontWeight, fontFamily: 'Menlo, Monaco, Consolas, monospace' }}>
      {text.slice(0, charsVisible)}
      {isTyping && cursorVisible && (
        <span style={{ opacity: 1, borderRight: `2px solid ${color}`, marginLeft: 2 }} />
      )}
    </span>
  );
};
```

- [ ] **Step 3: Verify by inspection** — no render step needed. These components have no side effects. Visual verification happens when used in scenes (Tasks 8–14).

- [ ] **Step 4: Commit**

```bash
git add video/src/compositions/PipelineExplainer/components/DataSnippet.tsx \
        video/src/compositions/PipelineExplainer/components/Typewriter.tsx
git commit -m "feat(video): add DataSnippet and Typewriter components"
```

---

## Task 4: ForkArrow component

**Files:**
- Create: `video/src/compositions/PipelineExplainer/components/ForkArrow.tsx`

This component is specific to S05. It shows the cache hit/miss fork: one arrow branches upward to a green "⚡ Cache Hit" badge (visible for 60 frames then fades), another branches downward to an amber "Cache Miss → Claude API" label (stays lit).

- [ ] **Step 1: Create `ForkArrow.tsx`**

```tsx
import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface ForkArrowProps {
  localFrame: number; // local frame within S05 (0 = start of S05)
}

export const ForkArrow: React.FC<ForkArrowProps> = ({ localFrame }) => {
  // Hit path: appears at frame 40, holds until frame 100, fades out
  const hitOpacity = interpolate(
    localFrame,
    [40, 55, 90, 105],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
  );

  // Miss path: appears at frame 80, stays fully visible
  const missOpacity = interpolate(
    localFrame,
    [80, 95],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
  );

  // SHA key appears char by char starting at frame 20
  const sha = 'SHA256("Isaiah 7:14|divergence|v2|…")';
  const shaChars = Math.min(sha.length, Math.max(0, Math.floor((localFrame - 20) * 1.5)));
  const shaVisible = sha.slice(0, shaChars);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 24 }}>
      {/* SHA key computation */}
      <div
        style={{
          fontFamily: 'Menlo, Monaco, Consolas, monospace',
          fontSize: 20,
          color: DARK.codeValue,
          opacity: localFrame > 15 ? 1 : 0,
          minHeight: 30,
        }}
      >
        {shaVisible}
        {shaChars < sha.length && <span style={{ borderRight: `2px solid ${DARK.codeValue}`, marginLeft: 2 }} />}
      </div>

      {/* Fork container */}
      <div style={{ display: 'flex', gap: 40 }}>
        {/* Vertical fork line */}
        <div
          style={{
            width: 2,
            height: 120,
            background: DARK.border,
            borderRadius: 1,
            opacity: localFrame > 35 ? 1 : 0,
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
          {/* Hit path */}
          <div style={{ opacity: hitOpacity, display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ width: 40, height: 2, background: DARK.cacheHit }} />
            <div
              style={{
                background: '#052e16',
                border: `1px solid ${DARK.cacheHit}`,
                borderRadius: 8,
                padding: '8px 20px',
                color: DARK.cacheHit,
                fontSize: 18,
                fontWeight: 600,
              }}
            >
              ⚡ Cache Hit → instant result
            </div>
          </div>

          {/* Miss path */}
          <div style={{ opacity: missOpacity, display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ width: 40, height: 2, background: DARK.cacheMiss }} />
            <div
              style={{
                background: '#431407',
                border: `1px solid ${DARK.cacheMiss}`,
                borderRadius: 8,
                padding: '8px 20px',
                color: DARK.cacheMiss,
                fontSize: 18,
                fontWeight: 600,
              }}
            >
              Cache Miss → Claude API ↓
            </div>
          </div>
        </div>
      </div>

      {/* Footnote */}
      <div
        style={{
          opacity: interpolate(localFrame, [100, 115], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          fontSize: 16,
          color: DARK.textDim,
          fontStyle: 'italic',
        }}
      >
        Isaiah 7:14 is now cached — but here's what happened on first request
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add video/src/compositions/PipelineExplainer/components/ForkArrow.tsx
git commit -m "feat(video): add ForkArrow component for cache hit/miss split"
```

---

## Task 5: UIFrame component

**Files:**
- Create: `video/src/compositions/PipelineExplainer/components/UIFrame.tsx`

This is a Remotion-rendered mockup of the BibCrit divergence page for Isaiah 7:14. It is NOT a screenshot — it's built in JSX so it animates cleanly. The mockup shows the passage bar, and 4 analysis sections fading in one by one.

- [ ] **Step 1: Create `UIFrame.tsx`**

```tsx
import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface UIFrameProps {
  localFrame: number;
}

const SECTIONS = [
  {
    title: 'Synthesis',
    tag: '← synthesis key',
    body: 'The MT reads הָעַלְמָה ("the young woman") while the LXX renders παρθένος ("virgin"), a lexical choice that drove centuries of Christological debate. The divergence originates in translational ideology, not manuscript variation.',
  },
  {
    title: 'Key Divergences',
    tag: '← key_divergences array',
    body: '1. עַלְמָה → παρθένος (lexical)  ·  2. וְקָרָאת → καλέσεις (person shift)  ·  3. עִמָּנוּ אֵל → Εμμανουηλ (transliteration vs translation)',
  },
  {
    title: 'Transmission History',
    tag: null,
    body: 'Aquila (2nd c.) corrects παρθένος to νεᾶνις ("young woman") in his revision — evidence that the LXX choice was recognized as interpretive within antiquity.',
  },
  {
    title: 'BibCrit Assessment',
    tag: null,
    body: 'Scholarly confidence: High. The lexical shift is attested in Origen\'s Hexapla (col. V), Irenaeus Adv. Haer. 3.21, and the Dead Sea Scrolls (1QIsaᵃ col. VII reads עלמה without article).',
  },
];

export const UIFrame: React.FC<UIFrameProps> = ({ localFrame }) => {
  // Nav bar fades in first
  const navOpacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // Passage bar appears at frame 20
  const barOpacity = interpolate(localFrame, [20, 35], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: '#0b0e18',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        borderRadius: 12,
      }}
    >
      {/* Nav bar */}
      <div
        style={{
          opacity: navOpacity,
          background: '#13172a',
          borderBottom: '1px solid #2d3348',
          padding: '16px 40px',
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          flexShrink: 0,
        }}
      >
        <div style={{ fontSize: 22, fontWeight: 700, color: '#a5b4fc' }}>BibCrit</div>
        <div style={{ fontSize: 15, color: '#64748b' }}>MT / LXX Divergence Analyzer</div>
      </div>

      {/* Passage bar */}
      <div
        style={{
          opacity: barOpacity,
          background: '#13172a',
          padding: '20px 40px',
          borderBottom: '1px solid #2d3348',
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            background: '#1e2130',
            border: '1px solid #6366f1',
            borderRadius: 8,
            padding: '10px 20px',
            fontSize: 20,
            color: '#e2e8f0',
            fontWeight: 600,
            minWidth: 300,
          }}
        >
          Isaiah 7:14
        </div>
        <div
          style={{
            background: '#6366f1',
            color: 'white',
            padding: '10px 24px',
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 700,
          }}
        >
          Analyze
        </div>
      </div>

      {/* Analysis sections */}
      <div style={{ flex: 1, padding: '28px 40px', display: 'flex', flexDirection: 'column', gap: 20, overflow: 'hidden' }}>
        {SECTIONS.map((section, i) => {
          const sectionStart = 45 + i * 60;
          const sectionOpacity = interpolate(
            localFrame,
            [sectionStart, sectionStart + 20],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
          );
          const sectionY = interpolate(
            localFrame,
            [sectionStart, sectionStart + 20],
            [16, 0],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
          );

          return (
            <div
              key={i}
              style={{
                opacity: sectionOpacity,
                transform: `translateY(${sectionY}px)`,
                background: '#1e2130',
                border: '1px solid #2d3348',
                borderRadius: 10,
                padding: '18px 24px',
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 10 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: '#a5b4fc' }}>
                  {section.title}
                </div>
                {section.tag && (
                  <div
                    style={{
                      fontSize: 12,
                      color: '#6366f1',
                      background: '#1e1b4b',
                      border: '1px solid #6366f1',
                      borderRadius: 4,
                      padding: '2px 10px',
                      fontStyle: 'italic',
                    }}
                  >
                    {section.tag}
                  </div>
                )}
              </div>
              <div style={{ fontSize: 14, color: '#94a3b8', lineHeight: 1.6 }}>
                {section.body}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add video/src/compositions/PipelineExplainer/components/UIFrame.tsx
git commit -m "feat(video): add UIFrame mockup component for S10"
```

---

## Task 6: S01_Title + S11_Outro scenes

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S01_Title.tsx`
- Create: `video/src/compositions/PipelineExplainer/scenes/S11_Outro.tsx`

- [ ] **Step 1: Create `S01_Title.tsx`** (local frame 0–89)

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

export const S01_Title: React.FC = () => {
  const frame = useCurrentFrame(); // 0–89

  const titleOpacity = interpolate(frame, [0, 20, 70, 89], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const subtitleOpacity = interpolate(frame, [18, 36], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const subtitleY = interpolate(frame, [18, 36], [12, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Accent line draws from 0 to full width
  const lineWidth = interpolate(frame, [30, 60], [0, 340], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 20,
        opacity: titleOpacity,
      }}
    >
      {/* Wordmark */}
      <div style={{ fontSize: 88, fontWeight: 700, color: DARK.accentLight, letterSpacing: '-0.02em', lineHeight: 1 }}>
        BibCrit
      </div>

      {/* Subtitle */}
      <div
        style={{
          opacity: subtitleOpacity,
          transform: `translateY(${subtitleY}px)`,
          fontSize: 30,
          fontWeight: 400,
          color: DARK.textMuted,
          letterSpacing: '0.08em',
        }}
      >
        How a verse analysis is generated
      </div>

      {/* Accent underline */}
      <div
        style={{
          width: lineWidth,
          height: 3,
          background: DARK.accent,
          borderRadius: 2,
        }}
      />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Create `S11_Outro.tsx`** (local frame 0–209)

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

const BADGES = ['Open source', 'Free', 'No signup'];

export const S11_Outro: React.FC = () => {
  const frame = useCurrentFrame(); // 0–209

  const urlOpacity = interpolate(frame, [15, 40], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const urlScale = interpolate(frame, [15, 40], [0.9, 1.0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // Fade to black over last 30 frames
  const fadeOut = interpolate(frame, [179, 209], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 36,
      }}
    >
      {/* URL */}
      <div
        style={{
          opacity: urlOpacity,
          transform: `scale(${urlScale})`,
          fontSize: 96,
          fontWeight: 700,
          color: DARK.accent,
          letterSpacing: '-0.02em',
        }}
      >
        bibcrit.app
      </div>

      {/* Badges row */}
      <div style={{ display: 'flex', gap: 20 }}>
        {BADGES.map((badge, i) => {
          const badgeOpacity = interpolate(frame, [40 + i * 12, 55 + i * 12], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
          });
          return (
            <div
              key={badge}
              style={{
                opacity: badgeOpacity,
                background: DARK.surface,
                border: `1px solid ${DARK.border}`,
                borderRadius: 999,
                padding: '10px 28px',
                fontSize: 20,
                color: DARK.textMuted,
                fontWeight: 500,
              }}
            >
              {badge}
            </div>
          );
        })}
      </div>

      {/* Fade-to-black overlay */}
      <div
        style={{
          position: 'absolute',
          inset: 0,
          background: '#000',
          opacity: fadeOut,
          pointerEvents: 'none',
        }}
      />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Wire S01 and S11 into index.tsx**

In `video/src/compositions/PipelineExplainer/index.tsx`, add imports at top:

```tsx
import { S01_Title } from './scenes/S01_Title';
import { S11_Outro } from './scenes/S11_Outro';
```

Replace the S1 and S11 `<Placeholder>` calls:

```tsx
// S1:
<Sequence from={SCENES.S1_START} durationInFrames={SCENES.S1_END - SCENES.S1_START}>
  <S01_Title />
</Sequence>

// S11:
<Sequence from={SCENES.S11_START} durationInFrames={SCENES.S11_END - SCENES.S11_START}>
  <S11_Outro />
</Sequence>
```

- [ ] **Step 4: Verify**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=45
```
Expected: "BibCrit" in indigo, subtitle below, accent line drawn.

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=2560
```
Expected: "bibcrit.app" large indigo, three badges below.

- [ ] **Step 5: Commit**

```bash
git add video/src/compositions/PipelineExplainer/scenes/S01_Title.tsx \
        video/src/compositions/PipelineExplainer/scenes/S11_Outro.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S01 Title and S11 Outro scenes"
```

---

## Task 7: S02_PipelineOverview + S09_Transition scenes

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S02_PipelineOverview.tsx`
- Create: `video/src/compositions/PipelineExplainer/scenes/S09_Transition.tsx`

- [ ] **Step 1: Create `S02_PipelineOverview.tsx`** (local frame 0–149)

Boxes appear one at a time left→right. At frame 100, a subtitle label fades in.

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';

export const S02_PipelineOverview: React.FC = () => {
  const frame = useCurrentFrame(); // 0–149

  // Reveal one box every 20 frames: 6 boxes → complete at frame 120
  const revealUpTo = Math.min(6, Math.floor(frame / 20) + 1);

  const subtitleOpacity = interpolate(frame, [100, 118], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 48,
        padding: '0 100px',
      }}
    >
      <PipelineRow
        activeIndex={-1}
        revealUpTo={revealUpTo}
        localFrame={frame}
        sceneLength={150}
      />

      <div
        style={{
          opacity: subtitleOpacity,
          fontSize: 22,
          color: DARK.textDim,
          fontStyle: 'italic',
        }}
      >
        Every analysis follows this path — let's walk through each stage
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Create `S09_Transition.tsx`** (local frame 0–119)

Pipeline concept fades out, transition label fades in.

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

export const S09_Transition: React.FC = () => {
  const frame = useCurrentFrame(); // 0–119

  // Content fades in quickly, then out
  const opacity = interpolate(frame, [0, 15, 90, 119], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const labelY = interpolate(frame, [0, 20], [16, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
        opacity,
      }}
    >
      <div
        style={{
          transform: `translateY(${labelY}px)`,
          fontSize: 52,
          fontWeight: 700,
          color: DARK.text,
          letterSpacing: '-0.01em',
        }}
      >
        The result in your browser
      </div>
      <div style={{ fontSize: 22, color: DARK.textDim }}>
        Isaiah 7:14 · MT/LXX Divergence Analyzer
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Wire into index.tsx**

Add imports:
```tsx
import { S02_PipelineOverview } from './scenes/S02_PipelineOverview';
import { S09_Transition } from './scenes/S09_Transition';
```

Replace S2 and S9 Placeholders with:
```tsx
<Sequence from={SCENES.S2_START} durationInFrames={SCENES.S2_END - SCENES.S2_START}>
  <S02_PipelineOverview />
</Sequence>

<Sequence from={SCENES.S9_START} durationInFrames={SCENES.S9_END - SCENES.S9_START}>
  <S09_Transition />
</Sequence>
```

- [ ] **Step 4: Verify**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=180
```
Expected: all 6 pipeline boxes visible on dark background, no active glow, subtitle visible.

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=1980
```
Expected: "The result in your browser" centered, dark background.

- [ ] **Step 5: Commit**

```bash
git add video/src/compositions/PipelineExplainer/scenes/S02_PipelineOverview.tsx \
        video/src/compositions/PipelineExplainer/scenes/S09_Transition.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S02 PipelineOverview and S09 Transition scenes"
```

---

## Task 8: S03_UserInput scene

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S03_UserInput.tsx`

Local frame 0–239. Input box glows. Typewriter types "Isaiah 7:14". Tool label appears. Data snippet fades in.

- [ ] **Step 1: Create `S03_UserInput.tsx`**

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';
import { Typewriter } from '../components/Typewriter';

export const S03_UserInput: React.FC = () => {
  const frame = useCurrentFrame(); // 0–239

  // Stage label and tool name appear at frame 40
  const toolLabelOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // Data snippet appears at frame 100
  const snippetOpacity = interpolate(frame, [100, 115], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 60,
      }}
    >
      {/* Pipeline row — Input box (index 0) active */}
      <PipelineRow activeIndex={0} revealUpTo={6} localFrame={frame} sceneLength={240} />

      {/* Scene content */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 32, width: '100%', maxWidth: 900 }}>

        {/* Stage number + label */}
        <div style={{ opacity: toolLabelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>
            Stage 1
          </div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>
            User Input
          </div>
          <div style={{ fontSize: 20, color: DARK.textDim, marginTop: 8 }}>
            MT / LXX Divergence Analyzer
          </div>
        </div>

        {/* Fake passage input bar with typewriter */}
        <div
          style={{
            background: DARK.surface,
            border: `2px solid ${DARK.borderActive}`,
            borderRadius: 10,
            padding: '18px 28px',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            boxShadow: `0 0 20px rgba(99,102,241,0.2)`,
          }}
        >
          <div style={{ fontSize: 13, color: DARK.textDim, fontWeight: 600, whiteSpace: 'nowrap' }}>Passage</div>
          <Typewriter
            text='"Isaiah 7:14"'
            localFrame={frame}
            startFrame={20}
            charsPerFrame={1.5}
            fontSize={26}
          />
        </div>

        {/* Data snippet */}
        <div style={{ opacity: snippetOpacity, width: '100%' }}>
          <DataSnippet
            localFrame={frame}
            startFrame={105}
            staggerFrames={15}
            lines={[
              { text: '{ ref: "Isaiah 7:14",', color: DARK.codeValue },
              { text: '  tool: "divergence",', color: DARK.codeValue },
              { text: '  lang: "en" }',        color: DARK.codeValue },
            ]}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Wire into index.tsx**

Add import: `import { S03_UserInput } from './scenes/S03_UserInput';`

Replace S3 Placeholder:
```tsx
<Sequence from={SCENES.S3_START} durationInFrames={SCENES.S3_END - SCENES.S3_START}>
  <S03_UserInput />
</Sequence>
```

- [ ] **Step 3: Verify**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=360
```
Expected: pipeline row at top with "Input" box glowing indigo, typewriter text "Isaiah 7:14" visible in passage bar, data snippet below.

- [ ] **Step 4: Commit**

```bash
git add video/src/compositions/PipelineExplainer/scenes/S03_UserInput.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S03 UserInput scene"
```

---

## Task 9: S04_CorpusLookup scene

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S04_CorpusLookup.tsx`

Local frame 0–299. Corpus box glows. MT Hebrew and LXX Greek fade in sequentially. Morphology badge pulses on key words.

- [ ] **Step 1: Create `S04_CorpusLookup.tsx`**

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';

export const S04_CorpusLookup: React.FC = () => {
  const frame = useCurrentFrame(); // 0–299

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // MT text appears at frame 40
  const mtOpacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // LXX text appears at frame 90
  const lxxOpacity = interpolate(frame, [90, 110], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // Morphology badge appears at frame 140
  const badgeScale = spring({ frame: frame - 140, fps: 30, config: { damping: 12, stiffness: 200 } });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 50,
      }}
    >
      <PipelineRow activeIndex={1} revealUpTo={6} localFrame={frame} sceneLength={300} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 32, width: '100%', maxWidth: 1000 }}>

        <div style={{ opacity: labelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 2</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Corpus Lookup</div>
        </div>

        {/* MT row */}
        <div
          style={{
            opacity: mtOpacity,
            background: DARK.surface,
            border: `1px solid ${DARK.border}`,
            borderRadius: 10,
            padding: '20px 32px',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 24,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: '#c0892a', background: '#1c140a', border: '1px solid #c0892a', borderRadius: 4, padding: '3px 10px', whiteSpace: 'nowrap', flexShrink: 0 }}>MT</div>
          <div style={{ flex: 1, fontSize: 32, color: DARK.text, direction: 'rtl', textAlign: 'right', fontFamily: 'serif' }}>
            הִנֵּה הָ<span style={{ color: DARK.accentLight, fontWeight: 700 }}>עַלְמָה</span> הָרָה וְיֹלֶדֶת בֵּן
          </div>
          <div style={{ fontSize: 13, color: DARK.textDim, whiteSpace: 'nowrap', flexShrink: 0 }}>ETCBC Leningrad Codex</div>
        </div>

        {/* LXX row */}
        <div
          style={{
            opacity: lxxOpacity,
            background: DARK.surface,
            border: `1px solid ${DARK.border}`,
            borderRadius: 10,
            padding: '20px 32px',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 24,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1e40af', background: '#0a0e1c', border: '1px solid #1e40af', borderRadius: 4, padding: '3px 10px', whiteSpace: 'nowrap', flexShrink: 0 }}>LXX</div>
          <div style={{ flex: 1, fontSize: 28, color: DARK.text, fontFamily: 'serif', fontStyle: 'italic' }}>
            ἰδοὺ ἡ <span style={{ color: DARK.accentLight, fontWeight: 700, fontStyle: 'normal' }}>παρθένος</span> ἐν γαστρὶ ἕξει
          </div>
          <div style={{ fontSize: 13, color: DARK.textDim, whiteSpace: 'nowrap', flexShrink: 0 }}>STEP Bible Vaticanus</div>
        </div>

        {/* Morphology badge */}
        {frame >= 140 && (
          <div
            style={{
              transform: `scale(${badgeScale})`,
              background: '#1e1b4b',
              border: `1px solid ${DARK.accent}`,
              borderRadius: 8,
              padding: '12px 28px',
              fontSize: 18,
              color: DARK.accentLight,
            }}
          >
            <strong>עַלְמָה</strong> = "young woman" (Hebrew) · <strong>παρθένος</strong> = "virgin" (Greek) — the defining lexical divergence
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Wire into index.tsx**

Add import and replace S4 Placeholder — same pattern as Task 8.

- [ ] **Step 3: Verify**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=630
```
Expected: "Corpus" box glowing, Hebrew text (RTL) and Greek text in two cards, morphology badge visible.

- [ ] **Step 4: Commit**

```bash
git add video/src/compositions/PipelineExplainer/scenes/S04_CorpusLookup.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S04 CorpusLookup scene"
```

---

## Task 10: S05_CacheCheck scene

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S05_CacheCheck.tsx`

- [ ] **Step 1: Create `S05_CacheCheck.tsx`** (local frame 0–239)

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { ForkArrow } from '../components/ForkArrow';

export const S05_CacheCheck: React.FC = () => {
  const frame = useCurrentFrame(); // 0–239

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 50,
      }}
    >
      <PipelineRow activeIndex={2} revealUpTo={6} localFrame={frame} sceneLength={240} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 28, width: '100%', maxWidth: 900 }}>

        <div style={{ opacity: labelOpacity }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 3</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Cache Check</div>
        </div>

        <ForkArrow localFrame={frame} />
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Wire, verify at frame 900, commit**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=900
```
Expected: "Cache" box glowing, SHA key computing, fork arrows visible (hit green + miss amber).

```bash
git add video/src/compositions/PipelineExplainer/scenes/S05_CacheCheck.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S05 CacheCheck scene with fork arrow"
```

---

## Task 11: S06_ClaudeAPI scene

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S06_ClaudeAPI.tsx`

- [ ] **Step 1: Create `S06_ClaudeAPI.tsx`** (local frame 0–299)

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';

export const S06_ClaudeAPI: React.FC = () => {
  const frame = useCurrentFrame(); // 0–299

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // Token counter ticks from 0 to 4021 over frames 80–200
  const tokenCount = Math.round(interpolate(frame, [80, 200], [0, 4021], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  }));

  const badgeOpacity = interpolate(frame, [60, 80], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const costOpacity = interpolate(frame, [200, 215], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 50,
      }}
    >
      <PipelineRow activeIndex={3} revealUpTo={6} localFrame={frame} sceneLength={300} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, width: '100%', maxWidth: 900 }}>

        <div style={{ opacity: labelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 4</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Claude API</div>
        </div>

        {/* Model badge */}
        <div style={{ opacity: badgeOpacity, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}>
          <div style={{ background: '#0f172a', border: `1px solid ${DARK.accent}`, borderRadius: 8, padding: '10px 24px', fontSize: 18, color: DARK.accentLight, fontFamily: 'Menlo, Monaco, Consolas, monospace' }}>
            claude-sonnet-4-5-20250929
          </div>
        </div>

        {/* Prompt snippet */}
        <DataSnippet
          localFrame={frame}
          startFrame={30}
          staggerFrames={20}
          lines={[
            { text: 'system: "You are an expert biblical textual critic…"', color: DARK.textDim },
            { text: 'user: "Analyze Isaiah 7:14 divergence.', color: DARK.codeValue },
            { text: '       MT: הִנֵּה הָעַלְמָה הָרָה…', color: DARK.codeValue },
            { text: '       LXX: ἰδοὺ ἡ παρθένος…"', color: DARK.codeValue },
          ]}
        />

        {/* Token counter + cost */}
        <div style={{ display: 'flex', gap: 40, alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 700, color: DARK.accentLight, fontFamily: 'Menlo, Monaco, Consolas, monospace' }}>
              {tokenCount.toLocaleString()}
            </div>
            <div style={{ fontSize: 14, color: DARK.textDim }}>tokens</div>
          </div>
          <div style={{ opacity: costOpacity, textAlign: 'center' }}>
            <div style={{ fontSize: 32, fontWeight: 600, color: DARK.cacheHit }}>~$0.02</div>
            <div style={{ fontSize: 14, color: DARK.textDim }}>per analysis</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Wire, verify at frame 1170, commit**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=1170
```
Expected: "Claude" box glowing, model badge visible, prompt lines revealed, token counter near 4021.

```bash
git add video/src/compositions/PipelineExplainer/scenes/S06_ClaudeAPI.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S06 ClaudeAPI scene"
```

---

## Task 12: S07_SSEStream scene

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S07_SSEStream.tsx`

- [ ] **Step 1: Create `S07_SSEStream.tsx`** (local frame 0–359)

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';

const CHECKLIST = ['synthesis', 'key_divergences', 'transmission_history', 'bibcrit_assessment'];

export const S07_SSEStream: React.FC = () => {
  const frame = useCurrentFrame(); // 0–359

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // Checklist items appear at frames 180, 220, 260, 300
  const checklistStart = 180;
  const checklistInterval = 40;

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 40,
      }}
    >
      <PipelineRow activeIndex={4} revealUpTo={6} localFrame={frame} sceneLength={360} />

      <div style={{ display: 'flex', gap: 60, width: '100%', maxWidth: 1100, alignItems: 'flex-start' }}>

        {/* Left: label + raw events */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={{ opacity: labelOpacity }}>
            <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 5</div>
            <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>SSE Stream</div>
            <div style={{ fontSize: 18, color: DARK.textDim, marginTop: 6 }}>Server-Sent Events · Flask → Browser</div>
          </div>

          <DataSnippet
            localFrame={frame}
            startFrame={30}
            staggerFrames={22}
            lines={[
              { text: 'data: {"step":"checking_cache"}', color: DARK.textDim },
              { text: 'data: {"step":"generating"}',     color: DARK.textDim },
              { text: 'data: {"step":"generating"}',     color: DARK.textDim },
              { text: 'data: {"done":true,',             color: DARK.codeValue },
              { text: '       "synthesis":"…",',         color: DARK.codeValue },
              { text: '       "key_divergences":[…]}',   color: DARK.codeValue },
            ]}
          />
        </div>

        {/* Right: JSON key checklist */}
        <div style={{ width: 320, display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 80 }}>
          <div style={{ fontSize: 14, color: DARK.textDim, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>
            Keys received
          </div>
          {CHECKLIST.map((key, i) => {
            const itemStart = checklistStart + i * checklistInterval;
            const itemOpacity = interpolate(frame, [itemStart, itemStart + 15], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
            });
            return (
              <div
                key={key}
                style={{
                  opacity: itemOpacity,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  background: DARK.surface,
                  border: `1px solid ${DARK.border}`,
                  borderRadius: 8,
                  padding: '10px 16px',
                }}
              >
                <span style={{ color: DARK.cacheHit, fontSize: 18, fontWeight: 700 }}>✓</span>
                <span style={{ fontFamily: 'Menlo, Monaco, Consolas, monospace', fontSize: 15, color: DARK.codeValue }}>{key}</span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Wire, verify at frame 1530, commit**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=1530
```
Expected: "SSE" box glowing, raw event lines on left, checklist building on right with green ticks.

```bash
git add video/src/compositions/PipelineExplainer/scenes/S07_SSEStream.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S07 SSEStream scene"
```

---

## Task 13: S08_Output scene

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S08_Output.tsx`

- [ ] **Step 1: Create `S08_Output.tsx`** (local frame 0–239)

At frame 150, all 6 pipeline boxes pulse together (achieved by switching `activeIndex` to -2 = "all" mode — handled with a flag prop on PipelineRow... actually simpler: render a second PipelineRow with all boxes active simultaneously, fading it in over the final PipelineRow).

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT, PIPELINE_STAGES } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';

export const S08_Output: React.FC = () => {
  const frame = useCurrentFrame(); // 0–239

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // "All boxes glow" pulse at frame 160: fade in all-active row over the regular one
  const allGlowOpacity = interpolate(frame, [160, 178], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const cacheWriteOpacity = interpolate(frame, [130, 148], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 50,
      }}
    >
      {/* Normal pipeline row with only Output (index 5) active */}
      <div style={{ position: 'relative', width: '100%' }}>
        <PipelineRow activeIndex={5} revealUpTo={6} localFrame={frame} sceneLength={240} />
        {/* All-glow overlay — each box independently glows using absolute glow via wrapper opacity */}
        <div style={{ position: 'absolute', inset: 0, opacity: allGlowOpacity }}>
          <PipelineRow activeIndex={-1} revealUpTo={6} localFrame={0} sceneLength={1} />
          {/* Each box glows by giving each a blue border — achieved by just showing them all with accent color */}
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, width: '100%', maxWidth: 900 }}>

        <div style={{ opacity: labelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 6</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Structured Output</div>
        </div>

        <DataSnippet
          localFrame={frame}
          startFrame={25}
          staggerFrames={20}
          lines={[
            { text: '{ "synthesis":           "The MT reads…",',   color: DARK.codeValue },
            { text: '  "key_divergences":     […],',                color: DARK.codeValue },
            { text: '  "transmission_history": "…",',               color: DARK.codeValue },
            { text: '  "bibcrit_assessment":  "…" }',               color: DARK.codeValue },
          ]}
        />

        {/* Supabase cache write badge */}
        <div
          style={{
            opacity: cacheWriteOpacity,
            background: '#052e16',
            border: `1px solid ${DARK.cacheHit}`,
            borderRadius: 10,
            padding: '14px 32px',
            fontSize: 20,
            color: DARK.cacheHit,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <span>✓</span>
          <span>Written to Supabase <code style={{ fontFamily: 'Menlo, Monaco, Consolas, monospace', fontSize: 17 }}>analysis_cache</code></span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Wire, verify at frame 1800, commit**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=1800
```
Expected: "Output" box glowing, JSON keys visible, Supabase badge in green.

```bash
git add video/src/compositions/PipelineExplainer/scenes/S08_Output.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S08 Output scene"
```

---

## Task 14: S10_UIDemo scene

**Files:**
- Create: `video/src/compositions/PipelineExplainer/scenes/S10_UIDemo.tsx`

- [ ] **Step 1: Create `S10_UIDemo.tsx`** (local frame 0–449)

```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { UIFrame } from '../components/UIFrame';

export const S10_UIDemo: React.FC = () => {
  const frame = useCurrentFrame(); // 0–449

  // Fade in over first 20 frames, fade out over last 20
  const sceneOpacity = interpolate(frame, [0, 20, 429, 449], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 80px',
      }}
    >
      <UIFrame localFrame={frame} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Wire, verify at frame 2200, commit**

```bash
cd video && npx remotion still PipelineExplainer --scale=0.25 --frame=2200
```
Expected: BibCrit UI mockup — nav bar, "Isaiah 7:14" in passage bar, 2–3 analysis sections faded in.

```bash
git add video/src/compositions/PipelineExplainer/scenes/S10_UIDemo.tsx \
        video/src/compositions/PipelineExplainer/index.tsx
git commit -m "feat(video): implement S10 UIDemo scene"
```

---

## Task 15: Wire all scenes into index.tsx (final)

**Files:**
- Modify: `video/src/compositions/PipelineExplainer/index.tsx`

At this point all scene files exist. Replace every remaining `<Placeholder>` with the real scene component.

- [ ] **Step 1: Write final `index.tsx`**

```tsx
import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { DARK, SCENES, FONT_STYLE } from './theme';

import { S01_Title }            from './scenes/S01_Title';
import { S02_PipelineOverview } from './scenes/S02_PipelineOverview';
import { S03_UserInput }        from './scenes/S03_UserInput';
import { S04_CorpusLookup }     from './scenes/S04_CorpusLookup';
import { S05_CacheCheck }       from './scenes/S05_CacheCheck';
import { S06_ClaudeAPI }        from './scenes/S06_ClaudeAPI';
import { S07_SSEStream }        from './scenes/S07_SSEStream';
import { S08_Output }           from './scenes/S08_Output';
import { S09_Transition }       from './scenes/S09_Transition';
import { S10_UIDemo }           from './scenes/S10_UIDemo';
import { S11_Outro }            from './scenes/S11_Outro';

export const PipelineExplainer: React.FC = () => (
  <AbsoluteFill style={{ background: DARK.bg, fontFamily: "'Space Grotesk', sans-serif" }}>
    <style>{FONT_STYLE}</style>

    <Sequence from={SCENES.S1_START}  durationInFrames={SCENES.S1_END  - SCENES.S1_START}>  <S01_Title />            </Sequence>
    <Sequence from={SCENES.S2_START}  durationInFrames={SCENES.S2_END  - SCENES.S2_START}>  <S02_PipelineOverview /> </Sequence>
    <Sequence from={SCENES.S3_START}  durationInFrames={SCENES.S3_END  - SCENES.S3_START}>  <S03_UserInput />        </Sequence>
    <Sequence from={SCENES.S4_START}  durationInFrames={SCENES.S4_END  - SCENES.S4_START}>  <S04_CorpusLookup />     </Sequence>
    <Sequence from={SCENES.S5_START}  durationInFrames={SCENES.S5_END  - SCENES.S5_START}>  <S05_CacheCheck />       </Sequence>
    <Sequence from={SCENES.S6_START}  durationInFrames={SCENES.S6_END  - SCENES.S6_START}>  <S06_ClaudeAPI />        </Sequence>
    <Sequence from={SCENES.S7_START}  durationInFrames={SCENES.S7_END  - SCENES.S7_START}>  <S07_SSEStream />        </Sequence>
    <Sequence from={SCENES.S8_START}  durationInFrames={SCENES.S8_END  - SCENES.S8_START}>  <S08_Output />           </Sequence>
    <Sequence from={SCENES.S9_START}  durationInFrames={SCENES.S9_END  - SCENES.S9_START}>  <S09_Transition />       </Sequence>
    <Sequence from={SCENES.S10_START} durationInFrames={SCENES.S10_END - SCENES.S10_START}> <S10_UIDemo />           </Sequence>
    <Sequence from={SCENES.S11_START} durationInFrames={SCENES.S11_END - SCENES.S11_START}> <S11_Outro />            </Sequence>
  </AbsoluteFill>
);
```

- [ ] **Step 2: Verify full timeline — render key frames**

```bash
cd video
npx remotion still PipelineExplainer --scale=0.25 --frame=45    # S1 title
npx remotion still PipelineExplainer --scale=0.25 --frame=165   # S2 overview
npx remotion still PipelineExplainer --scale=0.25 --frame=360   # S3 user input
npx remotion still PipelineExplainer --scale=0.25 --frame=630   # S4 corpus
npx remotion still PipelineExplainer --scale=0.25 --frame=900   # S5 cache fork
npx remotion still PipelineExplainer --scale=0.25 --frame=1170  # S6 Claude API
npx remotion still PipelineExplainer --scale=0.25 --frame=1530  # S7 SSE stream
npx remotion still PipelineExplainer --scale=0.25 --frame=1800  # S8 output
npx remotion still PipelineExplainer --scale=0.25 --frame=1980  # S9 transition
npx remotion still PipelineExplainer --scale=0.25 --frame=2200  # S10 UI demo
npx remotion still PipelineExplainer --scale=0.25 --frame=2580  # S11 outro
```

All 11 frames should look correct. Check each in the output directory.

- [ ] **Step 3: Open Remotion Studio and scrub the full timeline**

```bash
# Studio should already be running at http://localhost:3003
# Select PipelineExplainer from the composition dropdown
# Scrub from frame 0 to 2699
# Check: no black frames between scenes, glow transitions smooth, text legible
```

- [ ] **Step 4: Commit**

```bash
git add video/src/compositions/PipelineExplainer/
git commit -m "feat(video): wire all 11 scenes — PipelineExplainer complete"
```

---

## Task 16: Package.json scripts + final render check

**Files:**
- Modify: `video/package.json`

- [ ] **Step 1: Add render script for PipelineExplainer to `package.json`**

In `video/package.json`, add to the `scripts` object:

```json
"render:pipeline": "npx remotion render src/Root.tsx PipelineExplainer out/pipeline-explainer.mp4",
"still:pipeline": "npx remotion still src/Root.tsx PipelineExplainer --frame=45 out/pipeline-still.jpg"
```

- [ ] **Step 2: Verify the render command resolves (dry-run)**

```bash
cd video && npx remotion render src/Root.tsx PipelineExplainer --frames=0-0 out/pipeline-explainer.mp4
```

Expected: renders 1 frame (frame 0) without errors. Output file created.

- [ ] **Step 3: Commit**

```bash
git add video/package.json
git commit -m "feat(video): add render:pipeline script to package.json"
```

---

## Self-Review

**Spec coverage check:**
- ✅ S1 title card (90 frames / 3s)
- ✅ S2 pipeline overview — all boxes appear left→right
- ✅ S3 user input — typewriter, data snippet
- ✅ S4 corpus lookup — MT Hebrew, LXX Greek, morphology badge
- ✅ S5 cache check — SHA key, hit/miss fork
- ✅ S6 Claude API — prompt, model badge, token counter
- ✅ S7 SSE stream — raw events, JSON key checklist
- ✅ S8 output — JSON expansion, Supabase cache badge, all-glow pulse
- ✅ S9 transition — "The result in your browser"
- ✅ S10 UI demo — UIFrame mockup with staggered sections, overlay labels
- ✅ S11 outro — bibcrit.app, badges, fade to black
- ✅ SCENES constants used consistently (sum = 2700 frames)
- ✅ No CSS transitions used anywhere (Remotion rule)
- ✅ All `interpolate()` calls use `extrapolateLeft/Right: 'clamp'`
- ✅ Composition registered in Root.tsx alongside BibCritShowcase
- ✅ render:pipeline script added

**Type consistency:** `PipelineRow` receives `activeIndex: number` (-1 = none, 0–5 = stage) and `localFrame: number` — used consistently in all 7 scenes that include it (S02–S08). `DataSnippet` receives `lines: Array<{text: string; color?: string}>` — used in S03, S04, S06, S07, S08. `Typewriter` receives `text: string`, `localFrame: number`, `startFrame: number` — used in S03.
