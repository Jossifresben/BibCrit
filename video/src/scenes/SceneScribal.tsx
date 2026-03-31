import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { RadarChart } from '../components/RadarChart';
import { BrandSlug } from '../components/BrandSlug';

export const SceneScribal: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.scribal * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 20,
      }}
    >
      <BrandSlug />
      <div style={{ fontSize: 26, fontWeight: 600, color: PALETTE.muted, letterSpacing: '0.1em', textTransform: 'uppercase' }}>
        Isaiah — Translator Profile
      </div>
      <RadarChart startFrame={10} />
      <ToolLabel label="Scribal Tendency Profiler" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
