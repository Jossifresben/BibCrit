import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { BrandSlug } from '../components/BrandSlug';

const TRADITIONS = [
  { label: 'MT',  value: 130, color: PALETTE.mt,  textColor: '#fff', appear: 10 },
  { label: 'LXX', value: 230, color: PALETTE.lxx, textColor: '#fff', appear: 40 },
  { label: 'SP',  value: 130, color: PALETTE.sp,  textColor: '#fff', appear: 70 },
];

export const SceneNumerical: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = { fps: TIMING.fps };
  const labelStart = Math.floor(SCENE_DURATIONS.numerical * TIMING.labelReveal);

  const barProgress = interpolate(frame, [100, 160], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 48,
        padding: '0 80px',
      }}
    >
      <BrandSlug />
      <div style={{ fontSize: 26, color: PALETTE.muted, fontWeight: 600, letterSpacing: '0.08em', textTransform: 'uppercase' }}>
        Genesis 5:16 — Mahalalel's age
      </div>

      {/* Number chips */}
      <div style={{ display: 'flex', gap: 60, alignItems: 'flex-end' }}>
        {TRADITIONS.map((t) => {
          const sc = spring({ frame: frame - t.appear, fps, config: { damping: 14, stiffness: 180 } });
          return (
            <div
              key={t.label}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 12,
                transform: `scale(${sc})`,
                opacity: sc,
              }}
            >
              <div
                style={{
                  width: 240,
                  height: 240,
                  borderRadius: 24,
                  background: t.color,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: 80,
                  fontWeight: 700,
                  color: t.textColor,
                }}
              >
                {t.value}
              </div>
              <div style={{ fontSize: 28, fontWeight: 700, color: t.color, letterSpacing: '0.06em' }}>
                {t.label}
              </div>
            </div>
          );
        })}
      </div>

      {/* Fill bar */}
      <div style={{ width: '100%', maxWidth: 1000, background: PALETTE.border, borderRadius: 8, height: 20, overflow: 'hidden' }}>
        <div
          style={{
            width: `${barProgress * 100}%`,
            height: '100%',
            background: `linear-gradient(90deg, ${PALETTE.mt}, ${PALETTE.lxx}, ${PALETTE.sp})`,
            borderRadius: 8,
          }}
        />
      </div>

      <ToolLabel label="Numerical Discrepancy Modeler" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
