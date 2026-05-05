import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from 'remotion';
import { DARK, EASE_OUT } from '../theme';
import { PipelineRow } from '../components/PipelineRow';

export const S04_CorpusLookup: React.FC = () => {
  const frame = useCurrentFrame(); // 0–299

  const labelOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const mtOpacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const lxxOpacity = interpolate(frame, [90, 110], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  const badgeScale = spring({ frame: frame - 140, fps: 30, config: { damping: 12, stiffness: 200 } });

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
      <PipelineRow activeIndex={1} revealUpTo={6} localFrame={frame} sceneLength={300} />

      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 32, width: '100%', maxWidth: 1000 }}>

        <div style={{ opacity: labelOpacity, textAlign: 'center' }}>
          <div style={{ fontSize: 16, color: DARK.accent, fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', marginBottom: 8 }}>Stage 2</div>
          <div style={{ fontSize: 40, fontWeight: 700, color: DARK.text }}>Corpus Lookup</div>
        </div>

        {/* MT row */}
        <div
          style={{
            opacity: mtOpacity,
            background: DARK.surface,
            border: `1px solid ${DARK.border}`,
            borderRadius: 10,
            padding: '20px 32px',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 24,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: '#c0892a', background: '#1c140a', border: '1px solid #c0892a', borderRadius: 4, padding: '3px 10px', whiteSpace: 'nowrap', flexShrink: 0 }}>MT</div>
          <div style={{ flex: 1, fontSize: 32, color: DARK.text, direction: 'rtl', textAlign: 'right', fontFamily: 'serif' }}>
            הִנֵּה הָ<span style={{ color: DARK.accentLight, fontWeight: 700 }}>עַלְמָה</span> הָרָה וְיֹלֶדֶת בֵּן
          </div>
          <div style={{ fontSize: 13, color: DARK.textDim, whiteSpace: 'nowrap', flexShrink: 0 }}>ETCBC Leningrad Codex</div>
        </div>

        {/* LXX row */}
        <div
          style={{
            opacity: lxxOpacity,
            background: DARK.surface,
            border: `1px solid ${DARK.border}`,
            borderRadius: 10,
            padding: '20px 32px',
            width: '100%',
            display: 'flex',
            alignItems: 'center',
            gap: 24,
          }}
        >
          <div style={{ fontSize: 13, fontWeight: 700, color: '#1e40af', background: '#0a0e1c', border: '1px solid #1e40af', borderRadius: 4, padding: '3px 10px', whiteSpace: 'nowrap', flexShrink: 0 }}>LXX</div>
          <div style={{ flex: 1, fontSize: 28, color: DARK.text, fontFamily: 'serif', fontStyle: 'italic' }}>
            ἰδοὺ ἡ <span style={{ color: DARK.accentLight, fontWeight: 700, fontStyle: 'normal' }}>παρθένος</span> ἐν γαστρὶ ἕξει
          </div>
          <div style={{ fontSize: 13, color: DARK.textDim, whiteSpace: 'nowrap', flexShrink: 0 }}>STEP Bible Vaticanus</div>
        </div>

        {/* Morphology badge */}
        {frame >= 140 && (
          <div
            style={{
              transform: `scale(${badgeScale})`,
              background: '#1e1b4b',
              border: `1px solid ${DARK.accent}`,
              borderRadius: 8,
              padding: '12px 28px',
              fontSize: 18,
              color: DARK.accentLight,
            }}
          >
            <strong>עַלְמָה</strong> = "young woman" (Hebrew) · <strong>παρθένος</strong> = "virgin" (Greek) — the defining lexical divergence
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};
