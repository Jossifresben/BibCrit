import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';
import { DataSnippet } from '../components/DataSnippet';
import { Typewriter } from '../components/Typewriter';

export const S03_UserInput: React.FC = () => {
  const frame = useCurrentFrame(); // 0–239

  const toolLabelOpacity = interpolate(frame, [40, 55], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const snippetOpacity = interpolate(frame, [100, 115], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <AbsoluteFill
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        padding: '60px 120px 40px',
        gap: 60,
      }}
    >
      <PipelineRow activeIndex={0} revealUpTo={6} localFrame={frame} sceneLength={240} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 32, width: '100%', maxWidth: 900 }}>

        <div style={{ opacity: toolLabelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>
            Stage 1
          </div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>
            User Input
          </div>
          <div style={{ fontSize: 20, color: DARK.textDim, marginTop: 8 }}>
            MT / LXX Divergence Analyzer
          </div>
        </div>

        <div
          style={{
            background: DARK.surface,
            border: `2px solid ${DARK.borderActive}`,
            borderRadius: 10,
            padding: '18px 28px',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 16,
            boxShadow: `0 0 20px rgba(99,102,241,0.2)`,
          }}
        >
          <div style={{ fontSize: 13, color: DARK.textDim, fontWeight: 600, whiteSpace: 'nowrap' }}>Passage</div>
          <Typewriter
            text='"Isaiah 7:14"'
            localFrame={frame}
            startFrame={20}
            charsPerFrame={1.5}
            fontSize={26}
          />
        </div>

        <div style={{ opacity: snippetOpacity, width: '100%' }}>
          <DataSnippet
            localFrame={frame}
            startFrame={105}
            staggerFrames={15}
            lines={[
              { text: '{ ref: "Isaiah 7:14",', color: DARK.codeValue },
              { text: '  tool: "divergence",', color: DARK.codeValue },
              { text: '  lang: "en" }',        color: DARK.codeValue },
            ]}
          />
        </div>
      </div>
    </AbsoluteFill>
  );
};
