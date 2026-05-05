import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface DataSnippetProps {
  lines: Array<{ text: string; color?: string }>;
  localFrame: number;
  startFrame?: number;    // frame (local) when first line appears; default 20
  staggerFrames?: number; // frames between each line; default 18
}

export const DataSnippet: React.FC<DataSnippetProps> = ({
  lines,
  localFrame,
  startFrame = 20,
  staggerFrames = 18,
}) => {
  return (
    <div
      style={{
        background: DARK.surface2,
        border: `1px solid ${DARK.border}`,
        borderRadius: 8,
        padding: '14px 20px',
        fontFamily: 'Menlo, Monaco, Consolas, monospace',
        fontSize: 18,
        lineHeight: 1.7,
        textAlign: 'left',
      }}
    >
      {lines.map((line, i) => {
        const lineStart = startFrame + i * staggerFrames;
        const opacity = interpolate(
          localFrame,
          [lineStart, lineStart + 12],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
        );
        const translateY = interpolate(
          localFrame,
          [lineStart, lineStart + 12],
          [6, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        return (
          <div
            key={i}
            style={{
              opacity,
              transform: `translateY(${translateY}px)`,
              color: line.color ?? DARK.codeValue,
              whiteSpace: 'pre',
            }}
          >
            {line.text}
          </div>
        );
      })}
    </div>
  );
};
