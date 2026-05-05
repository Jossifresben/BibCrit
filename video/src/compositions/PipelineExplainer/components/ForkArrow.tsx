import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface ForkArrowProps {
  localFrame: number; // local frame within S05 (0 = start of S05)
}

export const ForkArrow: React.FC<ForkArrowProps> = ({ localFrame }) => {
  // Hit path: appears at frame 40, holds until frame 100, fades out
  const hitOpacity = interpolate(
    localFrame,
    [40, 55, 90, 105],
    [0, 1, 1, 0],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
  );

  // Miss path: appears at frame 80, stays fully visible
  const missOpacity = interpolate(
    localFrame,
    [80, 95],
    [0, 1],
    { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
  );

  // SHA key appears char by char starting at frame 20
  const sha = 'SHA256("Isaiah 7:14|divergence|v2|…")';
  const shaChars = Math.min(sha.length, Math.max(0, Math.floor((localFrame - 20) * 1.5)));
  const shaVisible = sha.slice(0, shaChars);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: 24 }}>
      {/* SHA key computation */}
      <div
        style={{
          fontFamily: 'Menlo, Monaco, Consolas, monospace',
          fontSize: 20,
          color: DARK.codeValue,
          opacity: localFrame > 15 ? 1 : 0,
          minHeight: 30,
        }}
      >
        {shaVisible}
        {shaChars < sha.length && <span style={{ borderRight: `2px solid ${DARK.codeValue}`, marginLeft: 2 }} />}
      </div>

      {/* Fork container */}
      <div style={{ display: 'flex', gap: 40 }}>
        {/* Vertical fork line */}
        <div
          style={{
            width: 2,
            height: 120,
            background: DARK.border,
            borderRadius: 1,
            opacity: localFrame > 35 ? 1 : 0,
          }}
        />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 32 }}>
          {/* Hit path */}
          <div style={{ opacity: hitOpacity, display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ width: 40, height: 2, background: DARK.cacheHit }} />
            <div
              style={{
                background: '#052e16',
                border: `1px solid ${DARK.cacheHit}`,
                borderRadius: 8,
                padding: '8px 20px',
                color: DARK.cacheHit,
                fontSize: 18,
                fontWeight: 600,
              }}
            >
              ⚡ Cache Hit → instant result
            </div>
          </div>

          {/* Miss path */}
          <div style={{ opacity: missOpacity, display: 'flex', alignItems: 'center', gap: 16 }}>
            <div style={{ width: 40, height: 2, background: DARK.cacheMiss }} />
            <div
              style={{
                background: '#431407',
                border: `1px solid ${DARK.cacheMiss}`,
                borderRadius: 8,
                padding: '8px 20px',
                color: DARK.cacheMiss,
                fontSize: 18,
                fontWeight: 600,
              }}
            >
              Cache Miss → Claude API ↓
            </div>
          </div>
        </div>
      </div>

      {/* Footnote */}
      <div
        style={{
          opacity: interpolate(localFrame, [100, 115], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          fontSize: 16,
          color: DARK.textDim,
          fontStyle: 'italic',
        }}
      >
        Isaiah 7:14 is now cached — but here's what happened on first request
      </div>
    </div>
  );
};
