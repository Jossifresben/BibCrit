import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { ForkArrow } from '../components/ForkArrow';

export const S05_CacheCheck: React.FC = () => {
  const frame = useCurrentFrame(); // 0–239

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 50,
      }}
    >
      <PipelineRow activeIndex={2} revealUpTo={6} localFrame={frame} sceneLength={240} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 28, width: '100%', maxWidth: 900 }}>

        <div style={{ opacity: labelOpacity }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 3</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Cache Check</div>
        </div>

        <ForkArrow localFrame={frame} />
      </div>
    </AbsoluteFill>
  );
};
