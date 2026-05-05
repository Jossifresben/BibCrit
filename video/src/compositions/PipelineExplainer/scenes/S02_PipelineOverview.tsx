import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';

export const S02_PipelineOverview: React.FC = () => {
  const frame = useCurrentFrame(); // 0–149

  // Reveal one box every 20 frames: 6 boxes → complete at frame 120
  const revealUpTo = Math.min(6, Math.floor(frame / 20) + 1);

  const subtitleOpacity = interpolate(frame, [100, 118], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 48,
        padding: '0 100px',
      }}
    >
      <PipelineRow
        activeIndex={-1}
        revealUpTo={revealUpTo}
        localFrame={frame}
        sceneLength={150}
      />

      <div
        style={{
          opacity: subtitleOpacity,
          fontSize: 22,
          color: DARK.textDim,
          fontStyle: 'italic',
        }}
      >
        Every analysis follows this path — let's walk through each stage
      </div>
    </AbsoluteFill>
  );
};
