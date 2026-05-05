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
