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
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
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
