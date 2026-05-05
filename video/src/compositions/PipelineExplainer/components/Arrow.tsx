import React from 'react';
import { DARK } from '../theme';

interface ArrowProps {
  revealProgress: number; // 0 = hidden, 1 = fully drawn
}

export const Arrow: React.FC<ArrowProps> = ({ revealProgress }) => {
  const lineWidth = 60 * revealProgress;
  const arrowOpacity = revealProgress > 0.8 ? (revealProgress - 0.8) / 0.2 : 0;

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        width: 70,
        flexShrink: 0,
        position: 'relative',
        height: 24,
      }}
    >
      {/* Horizontal line */}
      <div
        style={{
          height: 2,
          width: lineWidth,
          background: DARK.accent,
          borderRadius: 1,
        }}
      />
      {/* Arrowhead */}
      <div
        style={{
          opacity: arrowOpacity,
          width: 0,
          height: 0,
          borderTop: '6px solid transparent',
          borderBottom: '6px solid transparent',
          borderLeft: `10px solid ${DARK.accent}`,
          marginLeft: 2,
        }}
      />
    </div>
  );
};
