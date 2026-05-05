import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';

const CHECKLIST = ['synthesis', 'key_divergences', 'transmission_history', 'bibcrit_assessment'];

export const S07_SSEStream: React.FC = () => {
  const frame = useCurrentFrame(); // 0–359

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const checklistStart = 180;
  const checklistInterval = 40;

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 40,
      }}
    >
      <PipelineRow activeIndex={4} revealUpTo={6} localFrame={frame} sceneLength={360} />

      <div style={{ display: 'flex', gap: 60, width: '100%', maxWidth: 1100, alignItems: 'flex-start' }}>

        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 24 }}>
          <div style={{ opacity: labelOpacity }}>
            <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 5</div>
            <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>SSE Stream</div>
            <div style={{ fontSize: 18, color: DARK.textDim, marginTop: 6 }}>Server-Sent Events · Flask → Browser</div>
          </div>

          <DataSnippet
            localFrame={frame}
            startFrame={30}
            staggerFrames={22}
            lines={[
              { text: 'data: {"step":"checking_cache"}', color: DARK.textDim },
              { text: 'data: {"step":"generating"}',     color: DARK.textDim },
              { text: 'data: {"step":"generating"}',     color: DARK.textDim },
              { text: 'data: {"done":true,',             color: DARK.codeValue },
              { text: '       "synthesis":"…",',         color: DARK.codeValue },
              { text: '       "key_divergences":[…]}',   color: DARK.codeValue },
            ]}
          />
        </div>

        <div style={{ width: 320, display: 'flex', flexDirection: 'column', gap: 16, paddingTop: 80 }}>
          <div style={{ fontSize: 14, color: DARK.textDim, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 4 }}>
            Keys received
          </div>
          {CHECKLIST.map((key, i) => {
            const itemStart = checklistStart + i * checklistInterval;
            const itemOpacity = interpolate(frame, [itemStart, itemStart + 15], [0, 1], {
              extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
            });
            return (
              <div
                key={key}
                style={{
                  opacity: itemOpacity,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  background: DARK.surface,
                  border: `1px solid ${DARK.border}`,
                  borderRadius: 8,
                  padding: '10px 16px',
                }}
              >
                <span style={{ color: DARK.cacheHit, fontSize: 18, fontWeight: 700 }}>✓</span>
                <span style={{ fontFamily: 'Menlo, Monaco, Consolas, monospace', fontSize: 15, color: DARK.codeValue }}>{key}</span>
              </div>
            );
          })}
        </div>
      </div>
    </AbsoluteFill>
  );
};
