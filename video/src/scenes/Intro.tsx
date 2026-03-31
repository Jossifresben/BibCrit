import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from 'remotion';
import { PALETTE } from '../theme';

const TAGLINE = 'Biblical Textual Criticism';

export const Intro: React.FC = () => {
  const frame = useCurrentFrame();

  const logoOpacity = interpolate(frame, [0, 30], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const logoScale = interpolate(frame, [0, 30], [0.8, 1.0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

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
        gap: 32,
      }}
    >
      {/* Logo + wordmark */}
      <div
        style={{
          opacity: logoOpacity,
          transform: `scale(${logoScale})`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 24,
        }}
      >
        <Img
          src={staticFile('BibCrit_logo.svg')}
          style={{ width: 200, height: 200 }}
        />
        <div
          style={{
            fontSize: 96,
            fontWeight: 700,
            color: PALETTE.fg,
            letterSpacing: '-0.02em',
            lineHeight: 1,
          }}
        >
          BibCrit
        </div>
      </div>

      {/* Tagline typewriter */}
      <div
        style={{
          opacity: taglineOpacity,
          fontSize: 32,
          fontWeight: 400,
          color: PALETTE.muted,
          letterSpacing: '0.15em',
          textTransform: 'uppercase',
          minHeight: 44,
        }}
      >
        {tagline}
        <span style={{ opacity: frame % 20 < 10 ? 1 : 0 }}>|</span>
      </div>
    </AbsoluteFill>
  );
};
