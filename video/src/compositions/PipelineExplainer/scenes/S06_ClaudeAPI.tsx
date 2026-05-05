import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';

export const S06_ClaudeAPI: React.FC = () => {
  const frame = useCurrentFrame(); // 0–299

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const tokenCount = Math.round(interpolate(frame, [80, 200], [0, 4021], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  }));

  const badgeOpacity = interpolate(frame, [60, 80], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const costOpacity = interpolate(frame, [200, 215], [0, 1], {
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
      <PipelineRow activeIndex={3} revealUpTo={6} localFrame={frame} sceneLength={300} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 28, width: '100%', maxWidth: 900 }}>

        <div style={{ opacity: labelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 4</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Claude API</div>
        </div>

        <div style={{ opacity: badgeOpacity, display: 'flex', gap: 16, alignItems: 'center', flexWrap: 'wrap', justifyContent: 'center' }}>
          <div style={{ background: '#0f172a', border: `1px solid ${DARK.accent}`, borderRadius: 8, padding: '10px 24px', fontSize: 18, color: DARK.accentLight, fontFamily: 'Menlo, Monaco, Consolas, monospace' }}>
            claude-sonnet-4-5-20250929
          </div>
        </div>

        <DataSnippet
          localFrame={frame}
          startFrame={30}
          staggerFrames={20}
          lines={[
            { text: 'system: "You are an expert biblical textual critic…"', color: DARK.textDim },
            { text: 'user: "Analyze Isaiah 7:14 divergence.', color: DARK.codeValue },
            { text: '       MT: הִנֵּה הָעַלְמָה הָרָה…', color: DARK.codeValue },
            { text: '       LXX: ἰδοὺ ἡ παρθένος…"', color: DARK.codeValue },
          ]}
        />

        <div style={{ display: 'flex', gap: 40, alignItems: 'center' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: 48, fontWeight: 700, color: DARK.accentLight, fontFamily: 'Menlo, Monaco, Consolas, monospace' }}>
              {tokenCount.toLocaleString()}
            </div>
            <div style={{ fontSize: 14, color: DARK.textDim }}>tokens</div>
          </div>
          <div style={{ opacity: costOpacity, textAlign: 'center' }}>
            <div style={{ fontSize: 32, fontWeight: 600, color: DARK.cacheHit }}>~$0.02</div>
            <div style={{ fontSize: 14, color: DARK.textDim }}>per analysis</div>
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
