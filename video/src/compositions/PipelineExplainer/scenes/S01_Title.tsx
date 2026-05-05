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
