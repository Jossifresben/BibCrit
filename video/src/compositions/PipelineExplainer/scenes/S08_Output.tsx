import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';

export const S08_Output: React.FC = () => {
  const frame = useCurrentFrame(); // 0–239

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const allGlowOpacity = interpolate(frame, [160, 178], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const cacheWriteOpacity = interpolate(frame, [130, 148], [0, 1], {
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
      <div style={{ position: 'relative', width: '100%' }}>
        <PipelineRow activeIndex={5} revealUpTo={6} localFrame={frame} sceneLength={240} />
        <div style={{ position: 'absolute', inset: 0, opacity: allGlowOpacity }}>
          <PipelineRow activeIndex={-1} revealUpTo={6} localFrame={0} sceneLength={1} />
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, width: '100%', maxWidth: 900 }}>

        <div style={{ opacity: labelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 6</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Structured Output</div>
        </div>

        <DataSnippet
          localFrame={frame}
          startFrame={25}
          staggerFrames={20}
          lines={[
            { text: '{ "synthesis":           "The MT reads…",',   color: DARK.codeValue },
            { text: '  "key_divergences":     […],',                color: DARK.codeValue },
            { text: '  "transmission_history": "…",',               color: DARK.codeValue },
            { text: '  "bibcrit_assessment":  "…" }',               color: DARK.codeValue },
          ]}
        />

        <div
          style={{
            opacity: cacheWriteOpacity,
            background: '#052e16',
            border: `1px solid ${DARK.cacheHit}`,
            borderRadius: 10,
            padding: '14px 32px',
            fontSize: 20,
            color: DARK.cacheHit,
            fontWeight: 600,
            display: 'flex',
            alignItems: 'center',
            gap: 12,
          }}
        >
          <span>✓</span>
          <span>Written to Supabase <code style={{ fontFamily: 'Menlo, Monaco, Consolas, monospace', fontSize: 17 }}>analysis_cache</code></span>
        </div>
      </div>
    </AbsoluteFill>
  );
};
