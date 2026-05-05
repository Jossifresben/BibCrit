import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { UIFrame } from '../components/UIFrame';

export const S10_UIDemo: React.FC = () => {
  const frame = useCurrentFrame(); // 0–449

  const sceneOpacity = interpolate(frame, [0, 20, 429, 449], [0, 1, 1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        opacity: sceneOpacity,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '40px 80px',
      }}
    >
      <UIFrame localFrame={frame} />
    </AbsoluteFill>
  );
};
