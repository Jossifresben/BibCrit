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
