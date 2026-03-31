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
