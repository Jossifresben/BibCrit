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
