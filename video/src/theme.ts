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
