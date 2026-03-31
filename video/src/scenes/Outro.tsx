import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, Img, staticFile } from 'remotion';
import { PALETTE } from '../theme';

export const Outro: React.FC = () => {
  const frame = useCurrentFrame();

  const bgR = Math.round(interpolate(frame, [0, 20], [248, 26], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  const bgG = Math.round(interpolate(frame, [0, 20], [246, 26], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));
  const bgB = Math.round(interpolate(frame, [0, 20], [240, 26], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }));

  const logoOpacity = interpolate(frame, [15, 35], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  const urlOpacity = interpolate(frame, [30, 55], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const urlY = interpolate(frame, [30, 55], [24, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  const tagOpacity = interpolate(frame, [60, 85], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  // Invert logo to white for dark background
  const logoFilter = `brightness(0) invert(1)`;

  return (
    <AbsoluteFill
      style={{
        background: `rgb(${bgR},${bgG},${bgB})`,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 28,
      }}
    >
      <Img
        src={staticFile('BibCrit_logo.svg')}
        style={{
          width: 100,
          height: 100,
          opacity: logoOpacity,
          filter: logoFilter,
        }}
      />
      <div
        style={{
          opacity: urlOpacity,
          transform: `translateY(${urlY}px)`,
          fontSize: 96,
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
          fontSize: 26,
          color: PALETTE.slate,
          letterSpacing: '0.06em',
        }}
      >
        Open access · 8 tools · Powered by Claude
      </div>
    </AbsoluteFill>
  );
};
