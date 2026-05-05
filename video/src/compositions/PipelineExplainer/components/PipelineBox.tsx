import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface PipelineBoxProps {
  label: string;
  sub: string;
  isActive: boolean;
  localFrame: number;    // local frame within the current scene (0 = scene start)
  sceneLength: number;   // total frames in the active scene, for glow fade-out timing
  isVisible?: boolean;   // false = not yet revealed (used in S02 overview)
  children?: React.ReactNode;
}

export const PipelineBox: React.FC<PipelineBoxProps> = ({
  label, sub, isActive, localFrame, sceneLength, isVisible = true, children
}) => {
  const opacity = isVisible ? 1 : 0;

  // Glow fades in over first 15 frames, holds, fades out over last 15 frames
  const glow = isActive
    ? interpolate(
        localFrame,
        [0, 15, sceneLength - 15, sceneLength],
        [0, 1, 1, 0],
        { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
      )
    : 0;

  const labelColor = isActive ? DARK.accentLight : DARK.textMuted;
  const borderColor = isActive ? DARK.borderActive : DARK.border;
  const glowPx = 20 * glow;
  const glowAlpha = (0.5 * glow).toFixed(2);

  return (
    <div
      style={{
        opacity,
        background: DARK.surface,
        border: `2px solid ${borderColor}`,
        borderRadius: 12,
        padding: '18px 22px',
        minWidth: 160,
        textAlign: 'center',
        boxShadow: `0 0 ${glowPx}px rgba(99, 102, 241, ${glowAlpha})`,
        flexShrink: 0,
      }}
    >
      <div style={{ fontSize: 22, fontWeight: 700, color: labelColor, lineHeight: 1 }}>
        {label}
      </div>
      <div style={{ fontSize: 13, color: DARK.textDim, marginTop: 6 }}>
        {sub}
      </div>
      {children && (
        <div style={{ marginTop: 14 }}>{children}</div>
      )}
    </div>
  );
};
