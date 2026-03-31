import React from 'react';
import { useCurrentFrame, interpolate, Img, staticFile } from 'remotion';
import { PALETTE } from '../theme';

export const BrandSlug: React.FC = () => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        top: 40,
        left: 0,
        right: 0,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        opacity,
      }}
    >
      <Img
        src={staticFile('BibCrit_logo.svg')}
        style={{ width: 64, height: 64 }}
      />
      <span
        style={{
          fontSize: 36,
          fontWeight: 700,
          color: PALETTE.fg,
          letterSpacing: '0.04em',
        }}
      >
        BibCrit
      </span>
    </div>
  );
};
