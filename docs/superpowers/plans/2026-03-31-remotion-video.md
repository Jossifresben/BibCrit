# BibCrit Remotion Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 90-second programmatic video in Remotion showcasing all 8 BibCrit tools via animated React mockups in the BibCrit native palette, with background music.

**Architecture:** A standalone Remotion TypeScript project in `video/` at repo root. Ten scenes (Intro + 8 tools + Outro) are sequenced via `@remotion/transitions` `TransitionSeries` with 12-frame fade transitions between each. All animations use Remotion's `interpolate()` and `spring()` — no CSS keyframes. A shared `theme.ts` provides palette and timing constants used by all scenes.

**Tech Stack:** Remotion 4.x, React 18, TypeScript, `@remotion/transitions`, Space Grotesk font (Google Fonts via CSS import)

---

## Frame Budget

| Scene | Frames | Duration |
|---|---|---|
| Intro | 192 | 6.4s |
| SceneDivergence | 282 | 9.4s |
| SceneDSS | 282 | 9.4s |
| SceneBackTranslation | 282 | 9.4s |
| SceneScribal | 282 | 9.4s |
| SceneNumerical | 282 | 9.4s |
| SceneTheological | 282 | 9.4s |
| ScenePatristic | 282 | 9.4s |
| SceneGenealogy | 372 | 12.4s |
| Outro | 282 | 9.4s |
| **9 transitions @ 12f each** | **−108** | **−3.6s** |
| **Total** | **2700** | **90.0s** |

---

## File Map

| File | Responsibility |
|---|---|
| `video/package.json` | Dependencies and npm scripts |
| `video/remotion.config.ts` | Remotion config (codec, resolution) |
| `video/tsconfig.json` | TypeScript config |
| `video/public/BibCrit.mp3` | Audio asset (copied from Downloads) |
| `video/src/theme.ts` | Palette, timing constants, font CSS |
| `video/src/Root.tsx` | Registers `BibCritShowcase` composition |
| `video/src/BibCritVideo.tsx` | `TransitionSeries` scene sequencer + `Audio` |
| `video/src/components/ToolLabel.tsx` | Shared slide-up tool name label |
| `video/src/components/TraditionBadge.tsx` | Shared coloured tradition badge (MT/LXX/DSS…) |
| `video/src/components/RadarChart.tsx` | Animated SVG radar for scribal scene |
| `video/src/scenes/Intro.tsx` | Logo + typewriter tagline |
| `video/src/scenes/SceneDivergence.tsx` | Two-column MT/LXX parallel text + badges |
| `video/src/scenes/SceneDSS.tsx` | Stacked manuscript cards |
| `video/src/scenes/SceneBackTranslation.tsx` | Three-column word grid |
| `video/src/scenes/SceneScribal.tsx` | Radar chart draw animation |
| `video/src/scenes/SceneNumerical.tsx` | Number chips + fill bar |
| `video/src/scenes/SceneTheological.tsx` | Revision cards slide in |
| `video/src/scenes/ScenePatristic.tsx` | Distribution bar + citation cards |
| `video/src/scenes/SceneGenealogy.tsx` | Stemma tree node+edge draw animation |
| `video/src/scenes/Outro.tsx` | Dark bg + bibcrit.app URL + tagline |

---

## Task 1: Project Scaffold

**Files:**
- Create: `video/package.json`
- Create: `video/tsconfig.json`
- Create: `video/remotion.config.ts`
- Create: `video/public/` (directory)

- [ ] **Step 1: Create the video directory and package.json**

```bash
mkdir -p "/Users/jfresco16/Google Drive/Claude/BibCrit/video/public"
mkdir -p "/Users/jfresco16/Google Drive/Claude/BibCrit/video/src/scenes"
mkdir -p "/Users/jfresco16/Google Drive/Claude/BibCrit/video/src/components"
```

Create `video/package.json`:
```json
{
  "name": "bibcrit-video",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "studio": "npx remotion studio src/Root.tsx",
    "render": "npx remotion render src/Root.tsx BibCritShowcase out/bibcrit-showcase.mp4",
    "build": "npx remotion render src/Root.tsx BibCritShowcase out/bibcrit-showcase.mp4 --codec h264"
  },
  "dependencies": {
    "@remotion/transitions": "^4.0.0",
    "remotion": "^4.0.0"
  },
  "devDependencies": {
    "@types/react": "^18.0.0",
    "@types/react-dom": "^18.0.0",
    "react": "^18.0.0",
    "react-dom": "^18.0.0",
    "typescript": "^5.0.0"
  }
}
```

- [ ] **Step 2: Create tsconfig.json**

Create `video/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["ES2020", "DOM"],
    "module": "CommonJS",
    "jsx": "react",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "outDir": "dist"
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create remotion.config.ts**

Create `video/remotion.config.ts`:
```ts
import { Config } from '@remotion/cli/config';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);
```

- [ ] **Step 4: Copy audio asset**

```bash
cp ~/Downloads/BibCrit.mp3 "/Users/jfresco16/Google Drive/Claude/BibCrit/video/public/BibCrit.mp3"
```

- [ ] **Step 5: Install dependencies**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit/video" && npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 6: Add video/ to .gitignore for node_modules**

Append to `/Users/jfresco16/Google Drive/Claude/BibCrit/.gitignore`:
```
video/node_modules/
video/out/
```

- [ ] **Step 7: Commit scaffold**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/package.json video/tsconfig.json video/remotion.config.ts .gitignore
git commit -m "feat(video): scaffold Remotion project"
```

---

## Task 2: Theme Constants

**Files:**
- Create: `video/src/theme.ts`

- [ ] **Step 1: Create theme.ts**

Create `video/src/theme.ts`:
```ts
export const PALETTE = {
  parchment: '#f8f6f0',
  border:    '#d4d0c8',
  card:      '#ffffff',
  fg:        '#1a1a1a',
  muted:     '#888888',
  mt:        '#c0892a',
  mtLight:   '#fef3c7',
  lxx:       '#1e40af',
  lxxLight:  '#dbeafe',
  dss:       '#7c3aed',
  dssLight:  '#f3e8ff',
  sp:        '#2c7c5f',
  targum:    '#27ae60',
  vulgate:   '#c0392b',
  dark:      '#1a1a1a',
  slate:     '#94a3b8',
};

export const TIMING = {
  fps:         30,
  transition:  12,   // frames for cross-dissolve fade
  labelReveal: 0.6,  // fraction through a scene at which ToolLabel begins sliding up
};

// Scene durationInFrames — must sum to TOTAL + 9 × TIMING.transition = 2808
export const SCENE_DURATIONS = {
  intro:           192,
  divergence:      282,
  dss:             282,
  backTranslation: 282,
  scribal:         282,
  numerical:       282,
  theological:     282,
  patristic:       282,
  genealogy:       372,
  outro:           282,
} as const;

export const TOTAL_FRAMES = 2700; // 90s @ 30fps

// Inline Google Fonts CSS for Space Grotesk
export const FONT_STYLE = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;600;700&display=swap');
  * { font-family: 'Space Grotesk', sans-serif; box-sizing: border-box; }
`;
```

- [ ] **Step 2: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/theme.ts
git commit -m "feat(video): add theme palette and timing constants"
```

---

## Task 3: Shared Components

**Files:**
- Create: `video/src/components/ToolLabel.tsx`
- Create: `video/src/components/TraditionBadge.tsx`

- [ ] **Step 1: Create ToolLabel.tsx**

This component slides up from `translateY(20px)` → `translateY(0)` and `opacity 0 → 1` over 20 frames, starting at `startFrame`.

Create `video/src/components/ToolLabel.tsx`:
```tsx
import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { PALETTE } from '../theme';

interface ToolLabelProps {
  label: string;
  startFrame: number;
}

export const ToolLabel: React.FC<ToolLabelProps> = ({ label, startFrame }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [startFrame, startFrame + 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const translateY = interpolate(frame, [startFrame, startFrame + 20], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 60,
        left: 0,
        right: 0,
        textAlign: 'center',
        opacity,
        transform: `translateY(${translateY}px)`,
        fontSize: 22,
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: PALETTE.fg,
      }}
    >
      {label}
    </div>
  );
};
```

- [ ] **Step 2: Create TraditionBadge.tsx**

Create `video/src/components/TraditionBadge.tsx`:
```tsx
import React from 'react';
import { PALETTE } from '../theme';

type Tradition = 'MT' | 'LXX' | 'DSS' | 'SP' | 'IND' | 'ABS' | 'TARGUM' | 'VULGATE';

const COLORS: Record<Tradition, { bg: string; color: string }> = {
  MT:      { bg: PALETTE.mt,      color: '#fff' },
  LXX:     { bg: PALETTE.lxx,     color: '#fff' },
  DSS:     { bg: PALETTE.dss,     color: '#fff' },
  SP:      { bg: PALETTE.sp,      color: '#fff' },
  IND:     { bg: '#ea580c',       color: '#fff' },
  ABS:     { bg: PALETTE.border,  color: PALETTE.muted },
  TARGUM:  { bg: PALETTE.targum,  color: '#fff' },
  VULGATE: { bg: PALETTE.vulgate, color: '#fff' },
};

interface TraditionBadgeProps {
  tradition: Tradition;
  size?: 'sm' | 'md';
}

export const TraditionBadge: React.FC<TraditionBadgeProps> = ({
  tradition,
  size = 'md',
}) => {
  const { bg, color } = COLORS[tradition];
  const fontSize = size === 'sm' ? 11 : 13;
  const padding = size === 'sm' ? '2px 7px' : '4px 10px';

  return (
    <span
      style={{
        display: 'inline-block',
        background: bg,
        color,
        fontSize,
        fontWeight: 700,
        padding,
        borderRadius: 4,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
      }}
    >
      {tradition}
    </span>
  );
};
```

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/components/
git commit -m "feat(video): add ToolLabel and TraditionBadge shared components"
```

---

## Task 4: RadarChart Component

**Files:**
- Create: `video/src/components/RadarChart.tsx`

The radar draws 5 axes from centre outward (stroke-dashoffset animation), then fills the polygon.

- [ ] **Step 1: Create RadarChart.tsx**

Create `video/src/components/RadarChart.tsx`:
```tsx
import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { PALETTE } from '../theme';

const AXES = [
  { label: 'Literalness',       value: 0.72 },
  { label: 'Anthropomorphism',  value: 0.55 },
  { label: 'Messianic',         value: 0.80 },
  { label: 'Harmonization',     value: 0.45 },
  { label: 'Paraphrase',        value: 0.60 },
];

const SIZE   = 260;
const CX     = SIZE / 2;
const CY     = SIZE / 2;
const RADIUS = 100;

function polarToXY(angleRad: number, r: number) {
  return {
    x: CX + r * Math.sin(angleRad),
    y: CY - r * Math.cos(angleRad),
  };
}

interface RadarChartProps {
  startFrame: number; // frame at which animation begins
}

export const RadarChart: React.FC<RadarChartProps> = ({ startFrame }) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - startFrame);

  const n = AXES.length;
  const angleStep = (2 * Math.PI) / n;

  // Axes draw over frames 0–40 (each axis staggers by 8 frames)
  // Polygon fades in over frames 50–70
  // Labels appear one by one from frame 30

  const polygonOpacity = interpolate(localFrame, [50, 70], [0, 0.35], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const polygonPoints = AXES.map((ax, i) => {
    const angle = i * angleStep;
    const pt = polarToXY(angle, RADIUS * ax.value);
    return `${pt.x},${pt.y}`;
  }).join(' ');

  // Grid rings (static background)
  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <svg width={SIZE} height={SIZE} style={{ overflow: 'visible' }}>
      {/* Background rings */}
      {rings.map((r) => {
        const pts = AXES.map((_, i) => {
          const angle = i * angleStep;
          const pt = polarToXY(angle, RADIUS * r);
          return `${pt.x},${pt.y}`;
        }).join(' ');
        return (
          <polygon
            key={r}
            points={pts}
            fill="none"
            stroke={PALETTE.border}
            strokeWidth={1}
          />
        );
      })}

      {/* Axes */}
      {AXES.map((ax, i) => {
        const angle = i * angleStep;
        const end = polarToXY(angle, RADIUS);
        const axisProgress = interpolate(
          localFrame,
          [i * 8, i * 8 + 20],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        const ex = CX + (end.x - CX) * axisProgress;
        const ey = CY + (end.y - CY) * axisProgress;

        // Label
        const labelPt = polarToXY(angle, RADIUS + 22);
        const labelOpacity = interpolate(
          localFrame,
          [30 + i * 6, 46 + i * 6],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

        return (
          <g key={i}>
            <line
              x1={CX} y1={CY}
              x2={ex} y2={ey}
              stroke={PALETTE.border}
              strokeWidth={1.5}
            />
            <text
              x={labelPt.x}
              y={labelPt.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={10}
              fill={PALETTE.muted}
              opacity={labelOpacity}
              fontFamily="'Space Grotesk', sans-serif"
              fontWeight={600}
            >
              {ax.label}
            </text>
          </g>
        );
      })}

      {/* Filled polygon */}
      <polygon
        points={polygonPoints}
        fill={PALETTE.lxx}
        fillOpacity={polygonOpacity}
        stroke={PALETTE.lxx}
        strokeWidth={2}
        strokeOpacity={Math.min(polygonOpacity * 3, 1)}
      />

      {/* Data point dots */}
      {AXES.map((ax, i) => {
        const angle = i * angleStep;
        const pt = polarToXY(angle, RADIUS * ax.value);
        const dotOpacity = interpolate(localFrame, [55, 70], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        return (
          <circle
            key={i}
            cx={pt.x} cy={pt.y} r={4}
            fill={PALETTE.lxx}
            opacity={dotOpacity}
          />
        );
      })}
    </svg>
  );
};
```

- [ ] **Step 2: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/components/RadarChart.tsx
git commit -m "feat(video): add animated RadarChart component"
```

---

## Task 5: Root and BibCritVideo Shell

**Files:**
- Create: `video/src/Root.tsx`
- Create: `video/src/BibCritVideo.tsx`

- [ ] **Step 1: Create Root.tsx**

Create `video/src/Root.tsx`:
```tsx
import React from 'react';
import { Composition } from 'remotion';
import { BibCritVideo } from './BibCritVideo';
import { TOTAL_FRAMES, TIMING } from './theme';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="BibCritShowcase"
      component={BibCritVideo}
      durationInFrames={TOTAL_FRAMES}
      fps={TIMING.fps}
      width={1920}
      height={1080}
    />
  );
};
```

- [ ] **Step 2: Create BibCritVideo.tsx shell**

Import all scenes (they will be stubs initially — each scene file will be created in subsequent tasks). Create `video/src/BibCritVideo.tsx`:

```tsx
import React from 'react';
import { AbsoluteFill, Audio } from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { TIMING, SCENE_DURATIONS, PALETTE, FONT_STYLE } from './theme';

import { Intro }                from './scenes/Intro';
import { SceneDivergence }      from './scenes/SceneDivergence';
import { SceneDSS }             from './scenes/SceneDSS';
import { SceneBackTranslation } from './scenes/SceneBackTranslation';
import { SceneScribal }         from './scenes/SceneScribal';
import { SceneNumerical }       from './scenes/SceneNumerical';
import { SceneTheological }     from './scenes/SceneTheological';
import { ScenePatristic }       from './scenes/ScenePatristic';
import { SceneGenealogy }       from './scenes/SceneGenealogy';
import { Outro }                from './scenes/Outro';

const T = linearTiming({ durationInFrames: TIMING.transition });

export const BibCritVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: PALETTE.parchment }}>
      <style>{FONT_STYLE}</style>

      <Audio
        src="/BibCrit.mp3"
        volume={(f) => {
          // Fade out over last 60 frames (2s)
          if (f > 2640) return Math.max(0, 1 - (f - 2640) / 60);
          return 1;
        }}
      />

      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.intro}>
          <Intro />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.divergence}>
          <SceneDivergence />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.dss}>
          <SceneDSS />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.backTranslation}>
          <SceneBackTranslation />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.scribal}>
          <SceneScribal />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.numerical}>
          <SceneNumerical />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.theological}>
          <SceneTheological />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.patristic}>
          <ScenePatristic />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.genealogy}>
          <SceneGenealogy />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.outro}>
          <Outro />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 3: Create stub scene files so TypeScript compiles**

Create `video/src/scenes/Intro.tsx` (stub — will be fleshed out in Task 6):
```tsx
import React from 'react';
import { AbsoluteFill } from 'remotion';
import { PALETTE } from '../theme';
export const Intro: React.FC = () => (
  <AbsoluteFill style={{ background: PALETTE.parchment, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <span style={{ fontSize: 40, fontWeight: 700 }}>✦ BibCrit</span>
  </AbsoluteFill>
);
```

Repeat the same stub pattern for all 9 remaining scene files (`SceneDivergence`, `SceneDSS`, `SceneBackTranslation`, `SceneScribal`, `SceneNumerical`, `SceneTheological`, `ScenePatristic`, `SceneGenealogy`, `Outro`) — each exports a React component with an `AbsoluteFill` showing a placeholder label.

- [ ] **Step 4: Verify project opens in Remotion Studio**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit/video" && npm run studio
```

Expected: browser opens at `http://localhost:3000`, shows `BibCritShowcase` composition, 2700 frames, scrubbing shows stubs cycling through.

- [ ] **Step 5: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/
git commit -m "feat(video): wire Root, BibCritVideo shell, stub scenes, audio"
```

---

## Task 6: Intro Scene

**Files:**
- Modify: `video/src/scenes/Intro.tsx`

Logo fades + scales in. Tagline types character by character.

- [ ] **Step 1: Implement Intro.tsx**

Replace the stub. Create `video/src/scenes/Intro.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE } from '../theme';

const TAGLINE = 'Biblical Textual Criticism';

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();

  // Logo: fades in and scales 0.8→1.0 over frames 0–30
  const logoOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const logoScale = interpolate(frame, [0, 30], [0.8, 1.0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Tagline: starts at frame 40, one character every 3 frames
  const charsVisible = Math.floor(Math.max(0, frame - 40) / 3);
  const tagline = TAGLINE.slice(0, charsVisible);

  const taglineOpacity = interpolate(frame, [40, 52], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 20,
      }}
    >
      {/* Logo mark */}
      <div
        style={{
          opacity: logoOpacity,
          transform: `scale(${logoScale})`,
          fontSize: 80,
          fontWeight: 700,
          color: PALETTE.fg,
          letterSpacing: '-0.02em',
          lineHeight: 1,
        }}
      >
        ✦ BibCrit
      </div>

      {/* Tagline */}
      <div
        style={{
          opacity: taglineOpacity,
          fontSize: 26,
          fontWeight: 400,
          color: PALETTE.muted,
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
          minHeight: 36,
        }}
      >
        {tagline}
        <span style={{ opacity: frame % 20 < 10 ? 1 : 0 }}>|</span>
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview in Studio**

Open `http://localhost:3000`, scrub to frame 0–192. Verify: logo fades in, tagline types out, cursor blinks.

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/Intro.tsx
git commit -m "feat(video): implement Intro scene"
```

---

## Task 7: Outro Scene

**Files:**
- Modify: `video/src/scenes/Outro.tsx`

- [ ] **Step 1: Implement Outro.tsx**

Replace the stub. Create `video/src/scenes/Outro.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE } from '../theme';

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();

  // Background: parchment → dark over frames 0–20
  const bgR = Math.round(interpolate(frame, [0, 20], [248, 26], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  const bgG = Math.round(interpolate(frame, [0, 20], [246, 26], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  const bgB = Math.round(interpolate(frame, [0, 20], [240, 26], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));

  // URL fades in frames 25–50
  const urlOpacity = interpolate(frame, [25, 50], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const urlY = interpolate(frame, [25, 50], [20, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Tagline fades in frames 55–80
  const tagOpacity = interpolate(frame, [55, 80], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: `rgb(${bgR},${bgG},${bgB})`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 16,
      }}
    >
      <div
        style={{
          opacity: urlOpacity,
          transform: `translateY(${urlY}px)`,
          fontSize: 72,
          fontWeight: 700,
          color: '#ffffff',
          letterSpacing: '-0.01em',
        }}
      >
        bibcrit.app
      </div>
      <div
        style={{
          opacity: tagOpacity,
          fontSize: 20,
          color: PALETTE.slate,
          letterSpacing: '0.05em',
        }}
      >
        Open access · 8 tools · Powered by Claude
      </div>
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview in Studio**

Scrub to the last 282 frames of the composition. Verify dark fade-in, URL appears, tagline appears below.

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/Outro.tsx
git commit -m "feat(video): implement Outro scene"
```

---

## Task 8: SceneDivergence

**Files:**
- Modify: `video/src/scenes/SceneDivergence.tsx`

Two-column MT/LXX panel. Four text rows appear sequentially, each with a divergence badge.

- [ ] **Step 1: Implement SceneDivergence.tsx**

Replace the stub. Create `video/src/scenes/SceneDivergence.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const ROWS = [
  { mt: 'הָעַלְמָה הָרָה',        lxx: 'ἡ παρθένος ἐν γαστρί', badge: 'LEXICAL',      color: PALETTE.lxx },
  { mt: 'וְקָרָאת שְׁמוֹ',         lxx: 'καὶ καλέσεις τὸ ὄνομα', badge: 'ADDITION',    color: '#059669' },
  { mt: 'עִמָּנוּ אֵל',             lxx: 'Εμμανουηλ',             badge: 'THEOLOGICAL', color: PALETTE.vulgate },
  { mt: 'חֶמְאָה וּדְבַשׁ יֹאכֵל', lxx: 'βούτυρον καὶ μέλι',     badge: 'MINOR',       color: PALETTE.muted },
];

export const SceneDivergence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = { fps: TIMING.fps };

  const labelStart = Math.floor(SCENE_DURATIONS.divergence * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 120px',
        gap: 0,
      }}
    >
      {/* Column headers */}
      <div style={{ display: 'flex', width: '100%', maxWidth: 900, gap: 12, marginBottom: 16 }}>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <TraditionBadge tradition="MT" />
        </div>
        <div style={{ width: 120 }} />
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <TraditionBadge tradition="LXX" />
        </div>
      </div>

      {/* Rows */}
      {ROWS.map((row, i) => {
        const rowStart = 20 + i * 35;
        const rowOpacity = interpolate(frame, [rowStart, rowStart + 15], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const rowY = interpolate(frame, [rowStart, rowStart + 15], [12, 0], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const badgeScale = spring({
          frame: frame - (rowStart + 15),
          fps,
          config: { damping: 12, stiffness: 200 },
        });

        return (
          <div
            key={i}
            style={{
              display: 'flex',
              width: '100%',
              maxWidth: 900,
              gap: 12,
              alignItems: 'center',
              opacity: rowOpacity,
              transform: `translateY(${rowY}px)`,
              marginBottom: 18,
              background: PALETTE.card,
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 8,
              padding: '14px 20px',
            }}
          >
            <div style={{ flex: 1, fontSize: 18, color: PALETTE.fg, textAlign: 'right', direction: 'rtl', fontFamily: 'serif' }}>
              {row.mt}
            </div>
            <div
              style={{
                width: 120,
                textAlign: 'center',
                transform: `scale(${badgeScale})`,
              }}
            >
              <span style={{
                background: row.color,
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: 4,
                letterSpacing: '0.06em',
                textTransform: 'uppercase' as const,
                whiteSpace: 'nowrap' as const,
              }}>
                {row.badge}
              </span>
            </div>
            <div style={{ flex: 1, fontSize: 18, color: PALETTE.fg, fontFamily: 'serif', fontStyle: 'italic' }}>
              {row.lxx}
            </div>
          </div>
        );
      })}

      <ToolLabel label="MT / LXX Divergence Analyzer" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — scrub to Divergence scene, verify rows appear sequentially with badge spring**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/SceneDivergence.tsx
git commit -m "feat(video): implement SceneDivergence"
```

---

## Task 9: SceneDSS

**Files:**
- Modify: `video/src/scenes/SceneDSS.tsx`

- [ ] **Step 1: Implement SceneDSS.tsx**

Replace stub. Create `video/src/scenes/SceneDSS.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const MANUSCRIPTS = [
  { siglum: '1QIsaᵃ',   name: 'Great Isaiah Scroll, Qumran Cave 1', date: 'c. 125 BCE', align: 'IND' as const,  desc: '21 divergences from MT, 8 align with LXX' },
  { siglum: '4QIsaᵃ',   name: 'Isaiah Scroll, Qumran Cave 4',       date: '150–68 BCE', align: 'MT' as const,  desc: 'Proto-Masoretic alignment, 3 divergences' },
  { siglum: '4QIsaᵇ',   name: 'Isaiah Scroll b, Qumran Cave 4',     date: '100–68 BCE', align: 'LXX' as const, desc: 'Notable agreements with LXX Vorlage' },
];

export const SceneDSS: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.dss * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 120px',
        gap: 16,
      }}
    >
      {MANUSCRIPTS.map((ms, i) => {
        const cardStart = 15 + i * 45;
        const opacity = interpolate(frame, [cardStart, cardStart + 20], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const scaleY = interpolate(frame, [cardStart, cardStart + 20], [0.4, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });

        return (
          <div
            key={i}
            style={{
              width: '100%',
              maxWidth: 820,
              background: PALETTE.card,
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 10,
              padding: '18px 24px',
              opacity,
              transform: `scaleY(${scaleY})`,
              transformOrigin: 'top center',
              display: 'flex',
              alignItems: 'center',
              gap: 20,
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 700, color: PALETTE.dss, minWidth: 100 }}>
              {ms.siglum}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, color: PALETTE.muted, marginBottom: 4 }}>{ms.name} · {ms.date}</div>
              <div style={{ fontSize: 16, color: PALETTE.fg }}>{ms.desc}</div>
            </div>
            <TraditionBadge tradition={ms.align} />
          </div>
        );
      })}

      <ToolLabel label="DSS Bridge Tool" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — verify cards expand in sequence with alignment badges**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/SceneDSS.tsx
git commit -m "feat(video): implement SceneDSS"
```

---

## Task 10: SceneBackTranslation

**Files:**
- Modify: `video/src/scenes/SceneBackTranslation.tsx`

- [ ] **Step 1: Implement SceneBackTranslation.tsx**

Replace stub. Create `video/src/scenes/SceneBackTranslation.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';

const WORDS = [
  { lxx: 'ἐν',        vorlage: 'בְּ',      mt: 'בְּ',      status: 'agrees_mt'  },
  { lxx: 'ἀρχῇ',     vorlage: 'רֵאשִׁית', mt: 'רֵאשִׁית', status: 'agrees_mt'  },
  { lxx: 'ἐποίησεν', vorlage: 'בָּרָא',   mt: 'בָּרָא',   status: 'agrees_mt'  },
  { lxx: 'ὁ',        vorlage: '—',         mt: '—',         status: 'idiom_only' },
  { lxx: 'θεὸς',     vorlage: 'אֱלֹהִים', mt: 'אֱלֹהִים', status: 'agrees_mt'  },
  { lxx: 'τὸν',      vorlage: 'אֵת',      mt: 'אֵת',      status: 'agrees_mt'  },
  { lxx: 'οὐρανόν',  vorlage: 'הַשָּׁמַיִם', mt: 'הַשָּׁמַיִם', status: 'agrees_mt' },
];

const STATUS_COLOR: Record<string, string> = {
  agrees_mt:  '#059669',
  unattested: '#dc2626',
  idiom_only: PALETTE.muted,
  agrees_dss: PALETTE.dss,
};

export const SceneBackTranslation: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.backTranslation * TIMING.labelReveal);

  const COLS = [
    { key: 'lxx' as const,     header: 'LXX Greek',           italic: true  },
    { key: 'vorlage' as const, header: 'Vorlage (Hebrew)',     italic: false },
    { key: 'mt' as const,      header: 'MT Hebrew',            italic: false },
  ];

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 80px',
      }}
    >
      {/* Column headers */}
      <div style={{ display: 'flex', width: '100%', maxWidth: 860, gap: 8, marginBottom: 12 }}>
        {COLS.map((col) => (
          <div key={col.key} style={{ flex: 1, textAlign: 'center', fontSize: 12, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: PALETTE.muted }}>
            {col.header}
          </div>
        ))}
      </div>

      {/* Word grid */}
      <div style={{ display: 'flex', width: '100%', maxWidth: 860, gap: 8 }}>
        {COLS.map((col) => (
          <div key={col.key} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 6 }}>
            {WORDS.map((word, i) => {
              const wordStart = 10 + i * 20;
              const opacity = interpolate(frame, [wordStart, wordStart + 12], [0, 1], {
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              });
              const isVorlage = col.key === 'vorlage';
              const bg = isVorlage ? STATUS_COLOR[word.status] + '22' : PALETTE.card;
              const border = isVorlage ? `1.5px solid ${STATUS_COLOR[word.status]}` : `1px solid ${PALETTE.border}`;

              return (
                <div
                  key={i}
                  style={{
                    opacity,
                    background: bg,
                    border,
                    borderRadius: 6,
                    padding: '8px 12px',
                    textAlign: 'center',
                    fontSize: 18,
                    fontFamily: 'serif',
                    fontStyle: col.italic ? 'italic' : 'normal',
                    color: isVorlage ? STATUS_COLOR[word.status] : PALETTE.fg,
                    direction: col.key !== 'lxx' ? 'rtl' : 'ltr',
                  }}
                >
                  {word[col.key]}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <ToolLabel label="Back-Translation Workbench" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — verify three columns appear left to right, Vorlage words colour-coded**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/SceneBackTranslation.tsx
git commit -m "feat(video): implement SceneBackTranslation"
```

---

## Task 11: SceneScribal

**Files:**
- Modify: `video/src/scenes/SceneScribal.tsx`

- [ ] **Step 1: Implement SceneScribal.tsx**

Replace stub. Create `video/src/scenes/SceneScribal.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { RadarChart } from '../components/RadarChart';

export const SceneScribal: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.scribal * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 20,
      }}
    >
      <div style={{ fontSize: 18, fontWeight: 600, color: PALETTE.muted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
        Isaiah — Translator Profile
      </div>
      <RadarChart startFrame={10} />
      <ToolLabel label="Scribal Tendency Profiler" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — verify radar chart axes draw from centre, polygon fills after**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/SceneScribal.tsx
git commit -m "feat(video): implement SceneScribal"
```

---

## Task 12: SceneNumerical

**Files:**
- Modify: `video/src/scenes/SceneNumerical.tsx`

- [ ] **Step 1: Implement SceneNumerical.tsx**

Replace stub. Create `video/src/scenes/SceneNumerical.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';

const TRADITIONS = [
  { label: 'MT',  value: 130, color: PALETTE.mt,  textColor: '#fff', appear: 10 },
  { label: 'LXX', value: 230, color: PALETTE.lxx, textColor: '#fff', appear: 40 },
  { label: 'SP',  value: 130, color: PALETTE.sp,  textColor: '#fff', appear: 70 },
];

export const SceneNumerical: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = { fps: TIMING.fps };
  const labelStart = Math.floor(SCENE_DURATIONS.numerical * TIMING.labelReveal);

  const barProgress = interpolate(frame, [100, 160], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 32,
        padding: '0 120px',
      }}
    >
      <div style={{ fontSize: 18, color: PALETTE.muted, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        Genesis 5:16 — Mahalalel's age
      </div>

      {/* Number chips */}
      <div style={{ display: 'flex', gap: 40, alignItems: 'flex-end' }}>
        {TRADITIONS.map((t) => {
          const sc = spring({ frame: frame - t.appear, fps, config: { damping: 14, stiffness: 180 } });
          return (
            <div
              key={t.label}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 12,
                transform: `scale(${sc})`,
                opacity: sc,
              }}
            >
              <div
                style={{
                  width: 160,
                  height: 160,
                  borderRadius: 16,
                  background: t.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 56,
                  fontWeight: 700,
                  color: t.textColor,
                }}
              >
                {t.value}
              </div>
              <div style={{ fontSize: 20, fontWeight: 700, color: t.color, letterSpacing: '0.06em' }}>
                {t.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Fill bar */}
      <div style={{ width: '100%', maxWidth: 600, background: PALETTE.border, borderRadius: 8, height: 12, overflow: 'hidden' }}>
        <div
          style={{
            width: `${barProgress * 100}%`,
            height: '100%',
            background: `linear-gradient(90deg, ${PALETTE.mt}, ${PALETTE.lxx}, ${PALETTE.sp})`,
            borderRadius: 8,
          }}
        />
      </div>

      <ToolLabel label="Numerical Discrepancy Modeler" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — verify chips spring in, bar fills**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/SceneNumerical.tsx
git commit -m "feat(video): implement SceneNumerical"
```

---

## Task 13: SceneTheological

**Files:**
- Modify: `video/src/scenes/SceneTheological.tsx`

- [ ] **Step 1: Implement SceneTheological.tsx**

Replace stub. Create `video/src/scenes/SceneTheological.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const CARDS = [
  { type: 'Anthropomorphism Avoidance', tradition: 'LXX' as const, ref: 'Exodus 24:10', note: 'MT: "they saw God" → LXX: "they saw the place where the God of Israel stood"' },
  { type: 'Messianic Heightening',      tradition: 'LXX' as const, ref: 'Isaiah 7:14',  note: 'MT: עַלְמָה (young woman) → LXX: παρθένος (virgin)' },
  { type: 'Harmonization',             tradition: 'TARGUM' as const, ref: 'Gen 1:26', note: 'Targum Onkelos softens "Let us make man" to remove plural implied address' },
];

export const SceneTheological: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.theological * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 120px',
        gap: 16,
      }}
    >
      {CARDS.map((card, i) => {
        const cardStart = 15 + i * 50;
        const opacity = interpolate(frame, [cardStart, cardStart + 20], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const x = interpolate(frame, [cardStart, cardStart + 20], [-30, 0], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });

        return (
          <div
            key={i}
            style={{
              width: '100%',
              maxWidth: 820,
              background: PALETTE.card,
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 10,
              padding: '16px 22px',
              opacity,
              transform: `translateX(${x}px)`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 8 }}>
              <span style={{ fontSize: 15, fontWeight: 700, color: PALETTE.fg }}>{card.type}</span>
              <TraditionBadge tradition={card.tradition} size="sm" />
              <span style={{ fontSize: 12, color: PALETTE.muted, marginLeft: 'auto' }}>{card.ref}</span>
            </div>
            <div style={{ fontSize: 14, color: PALETTE.muted, fontStyle: 'italic' }}>{card.note}</div>
          </div>
        );
      })}

      <ToolLabel label="Theological Revision Detector" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — verify cards slide in from left one by one**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/SceneTheological.tsx
git commit -m "feat(video): implement SceneTheological"
```

---

## Task 14: ScenePatristic

**Files:**
- Modify: `video/src/scenes/ScenePatristic.tsx`

- [ ] **Step 1: Implement ScenePatristic.tsx**

Replace stub. Create `video/src/scenes/ScenePatristic.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const DIST = [
  { label: 'Closer to LXX', pct: 55, color: PALETTE.lxx },
  { label: 'Mixed',          pct: 25, color: '#8e44ad' },
  { label: 'Closer to MT',  pct: 20, color: PALETTE.mt },
];

const CITATIONS = [
  { father: 'Origen',        dates: '184–253 CE', form: 'LXX' as const,    work: 'Contra Celsum 1.35', text: '"ἰδοὺ ἡ παρθένος ἐν γαστρὶ ἕξει…"' },
  { father: 'Justin Martyr', dates: '100–165 CE', form: 'LXX' as const,    work: 'Dialogue with Trypho 43', text: 'Cites LXX verbatim against Jewish MT reading' },
  { father: 'Irenaeus',      dates: '130–202 CE', form: 'TARGUM' as const, work: 'Against Heresies 3.21', text: 'Notes Hebrew uses עַלְמָה, not בְּתוּלָה' },
];

export const ScenePatristic: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.patristic * TIMING.labelReveal);

  const barProgress = interpolate(frame, [10, 50], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 120px',
        gap: 20,
      }}
    >
      {/* Distribution bar */}
      <div style={{ width: '100%', maxWidth: 820 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: PALETTE.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
          Text form distribution — Isaiah 7:14 · 23 citations
        </div>
        <div style={{ display: 'flex', height: 32, borderRadius: 8, overflow: 'hidden', gap: 3 }}>
          {DIST.map((seg) => (
            <div
              key={seg.label}
              style={{
                flex: seg.pct * barProgress,
                background: seg.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                fontWeight: 700,
                color: '#fff',
                overflow: 'hidden',
                whiteSpace: 'nowrap' as const,
                transition: 'flex 0.3s',
              }}
            >
              {barProgress > 0.3 ? `${seg.pct}%` : ''}
            </div>
          ))}
        </div>
      </div>

      {/* Citation cards */}
      {CITATIONS.map((c, i) => {
        const cardStart = 55 + i * 40;
        const opacity = interpolate(frame, [cardStart, cardStart + 18], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const y = interpolate(frame, [cardStart, cardStart + 18], [14, 0], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });

        return (
          <div
            key={i}
            style={{
              width: '100%',
              maxWidth: 820,
              background: PALETTE.card,
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 10,
              padding: '12px 20px',
              opacity,
              transform: `translateY(${y}px)`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
              <span style={{ fontWeight: 700, fontSize: 15, color: PALETTE.fg }}>{c.father}</span>
              <span style={{ fontSize: 12, color: PALETTE.muted }}>{c.dates}</span>
              <TraditionBadge tradition={c.form} size="sm" />
              <span style={{ fontSize: 12, color: PALETTE.muted, marginLeft: 'auto', fontStyle: 'italic' }}>{c.work}</span>
            </div>
            <div style={{ fontSize: 13, color: PALETTE.muted, fontStyle: 'italic' }}>{c.text}</div>
          </div>
        );
      })}

      <ToolLabel label="Patristic Citation Tracker" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — verify bar fills then citation cards appear**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/ScenePatristic.tsx
git commit -m "feat(video): implement ScenePatristic"
```

---

## Task 15: SceneGenealogy (Visual Payoff)

**Files:**
- Modify: `video/src/scenes/SceneGenealogy.tsx`

This is the longest and most complex scene. A stemma tree draws itself: nodes appear top-down and SVG edges animate via `stroke-dashoffset`.

- [ ] **Step 1: Implement SceneGenealogy.tsx**

Replace stub. Create `video/src/scenes/SceneGenealogy.tsx`:
```tsx
import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';

// Stemma nodes — positioned in a 900×480 SVG viewport
const NODES = [
  { id: 'proto',  label: 'Proto-Hebrew',    date: '4th–3rd c. BCE', x: 450, y:  50, color: '#334155', text: '#fff' },
  { id: 'mt-src', label: 'Pre-Masoretic',   date: '2nd–1st c. BCE', x: 220, y: 160, color: '#334155', text: '#fff' },
  { id: 'lxx',    label: 'Old Greek',       date: '3rd–2nd c. BCE', x: 450, y: 160, color: PALETTE.lxx, text: '#fff' },
  { id: 'dss',    label: '1QIsaᵃ',          date: 'c. 125 BCE',     x: 700, y: 160, color: PALETTE.dss, text: '#fff' },
  { id: 'mt',     label: 'Masoretic Text',  date: '1st–10th c. CE', x: 220, y: 290, color: PALETTE.mt,  text: '#fff' },
  { id: 'hex',    label: 'Hexaplaric LXX',  date: 'c. 240 CE',      x: 380, y: 290, color: PALETTE.lxx, text: '#fff' },
  { id: 'luc',    label: 'Lucianic LXX',    date: 'c. 300 CE',      x: 560, y: 290, color: PALETTE.lxx, text: '#fff' },
  { id: 'aleppo', label: 'Aleppo Codex',    date: 'c. 930 CE',      x: 120, y: 420, color: PALETTE.mt,  text: '#fff' },
  { id: 'len',    label: 'Leningrad Codex', date: '1008 CE',        x: 300, y: 420, color: PALETTE.mt,  text: '#fff' },
];

const EDGES = [
  ['proto',  'mt-src'], ['proto', 'lxx'],  ['proto',  'dss'],
  ['mt-src', 'mt'],     ['lxx',   'hex'],  ['lxx',    'luc'],
  ['mt',     'aleppo'], ['mt',    'len'],
];

const NODE_W = 130;
const NODE_H = 40;

export const SceneGenealogy: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.genealogy * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 80px',
      }}
    >
      <svg
        viewBox="0 0 900 490"
        style={{ width: '100%', maxWidth: 900 }}
      >
        {/* Edges */}
        {EDGES.map(([fromId, toId], i) => {
          const from = NODES.find((n) => n.id === fromId)!;
          const to   = NODES.find((n) => n.id === toId)!;
          const x1 = from.x;
          const y1 = from.y + NODE_H;
          const x2 = to.x;
          const y2 = to.y;
          const midY = (y1 + y2) / 2;
          const d = `M${x1},${y1} C${x1},${midY} ${x2},${midY} ${x2},${y2}`;
          const pathLen = 120; // approximate
          const edgeStart = 20 + i * 18;
          const progress = interpolate(frame, [edgeStart, edgeStart + 25], [1, 0], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });

          return (
            <path
              key={i}
              d={d}
              fill="none"
              stroke={PALETTE.border}
              strokeWidth={1.5}
              strokeDasharray={pathLen}
              strokeDashoffset={progress * pathLen}
            />
          );
        })}

        {/* Nodes */}
        {NODES.map((node, i) => {
          const nodeStart = 5 + i * 22;
          const opacity = interpolate(frame, [nodeStart, nodeStart + 18], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });
          const scale = interpolate(frame, [nodeStart, nodeStart + 18], [0.6, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });

          return (
            <g
              key={node.id}
              transform={`translate(${node.x - NODE_W / 2}, ${node.y})`}
              opacity={opacity}
              style={{ transformOrigin: `${node.x}px ${node.y + NODE_H / 2}px` }}
            >
              <rect
                x={0} y={0}
                width={NODE_W} height={NODE_H}
                rx={6}
                fill={node.color}
                transform={`scale(${scale})`}
                style={{ transformOrigin: `${NODE_W / 2}px ${NODE_H / 2}px` }}
              />
              <text
                x={NODE_W / 2} y={NODE_H / 2 - 4}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={11}
                fontWeight={700}
                fill={node.text}
                fontFamily="'Space Grotesk', sans-serif"
              >
                {node.label}
              </text>
              <text
                x={NODE_W / 2} y={NODE_H / 2 + 10}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={9}
                fill="rgba(255,255,255,0.7)"
                fontFamily="'Space Grotesk', sans-serif"
              >
                {node.date}
              </text>
            </g>
          );
        })}
      </svg>

      <ToolLabel label="Manuscript Genealogy" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
```

- [ ] **Step 2: Preview — verify nodes appear top-down, edges draw after each node**

- [ ] **Step 3: Commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/src/scenes/SceneGenealogy.tsx
git commit -m "feat(video): implement SceneGenealogy stemma animation"
```

---

## Task 16: Final Polish and Render

**Files:**
- Create: `video/out/` (directory, gitignored)

- [ ] **Step 1: Full preview pass in Studio**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit/video" && npm run studio
```

Walk through the full 2700 frames. Check:
- [ ] Intro: logo scales, tagline types, cursor blinks
- [ ] All 8 tool scenes: animations complete before ToolLabel appears, ToolLabel readable
- [ ] Outro: fade to dark, URL large and clear, tagline legible
- [ ] Transitions: 12-frame cross-dissolves feel smooth
- [ ] Audio: music audible from frame 0, fades at frame 2640

- [ ] **Step 2: Create output directory**

```bash
mkdir -p "/Users/jfresco16/Google Drive/Claude/BibCrit/video/out"
```

- [ ] **Step 3: Render to MP4**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit/video" && npm run render
```

Expected: `video/out/bibcrit-showcase.mp4` created, ~15–30 MB.

- [ ] **Step 4: Verify output**

Open `video/out/bibcrit-showcase.mp4` in QuickTime. Confirm:
- Duration ~90 seconds
- Audio audible, fades near end
- All scenes visible, text legible at 1920×1080

- [ ] **Step 5: Final commit**

```bash
cd "/Users/jfresco16/Google Drive/Claude/BibCrit"
git add video/
git commit -m "feat(video): complete BibCrit Remotion showcase video"
```

---

## Adjusting Timing

If any scene feels too fast or slow, edit `SCENE_DURATIONS` in `theme.ts`. Keep the total sum equal to `TOTAL_FRAMES + 9 × TIMING.transition = 2808`. The Studio scrubber makes it easy to find exact frame offsets for each animation trigger.
