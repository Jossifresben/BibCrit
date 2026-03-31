import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const MANUSCRIPTS = [
  { siglum: '1QIsaᵃ',   name: 'Great Isaiah Scroll, Qumran Cave 1', date: 'c. 125 BCE', align: 'IND' as const,  desc: '21 divergences from MT, 8 align with LXX' },
  { siglum: '4QIsaᵃ',   name: 'Isaiah Scroll, Qumran Cave 4',       date: '150–68 BCE', align: 'MT' as const,  desc: 'Proto-Masoretic alignment, 3 divergences' },
  { siglum: '4QIsaᵇ',   name: 'Isaiah Scroll b, Qumran Cave 4',     date: '100–68 BCE', align: 'LXX' as const, desc: 'Notable agreements with LXX Vorlage' },
];

export const SceneDSS: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.dss * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 120px',
        gap: 16,
      }}
    >
      {MANUSCRIPTS.map((ms, i) => {
        const cardStart = 15 + i * 45;
        const opacity = interpolate(frame, [cardStart, cardStart + 20], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const scaleY = interpolate(frame, [cardStart, cardStart + 20], [0.4, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });

        return (
          <div
            key={i}
            style={{
              width: '100%',
              maxWidth: 820,
              background: PALETTE.card,
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 10,
              padding: '18px 24px',
              opacity,
              transform: `scaleY(${scaleY})`,
              transformOrigin: 'top center',
              display: 'flex',
              alignItems: 'center',
              gap: 20,
            }}
          >
            <div style={{ fontSize: 28, fontWeight: 700, color: PALETTE.dss, minWidth: 100 }}>
              {ms.siglum}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 14, color: PALETTE.muted, marginBottom: 4 }}>{ms.name} · {ms.date}</div>
              <div style={{ fontSize: 16, color: PALETTE.fg }}>{ms.desc}</div>
            </div>
            <TraditionBadge tradition={ms.align} />
          </div>
        );
      })}

      <ToolLabel label="DSS Bridge Tool" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
