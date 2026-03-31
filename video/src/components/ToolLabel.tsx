import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { PALETTE } from '../theme';

interface ToolLabelProps {
  label: string;
  startFrame: number;
}

export const ToolLabel: React.FC<ToolLabelProps> = ({ label, startFrame }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(frame, [startFrame, startFrame + 20], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const translateY = interpolate(frame, [startFrame, startFrame + 20], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 60,
        left: 0,
        right: 0,
        textAlign: 'center',
        opacity,
        transform: `translateY(${translateY}px)`,
        fontSize: 36,
        fontWeight: 700,
        letterSpacing: '0.06em',
        textTransform: 'uppercase',
        color: PALETTE.fg,
      }}
    >
      {label}
    </div>
  );
};
