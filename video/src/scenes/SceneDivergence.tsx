import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate, spring } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const ROWS = [
  { mt: 'הָעַלְמָה הָרָה',        lxx: 'ἡ παρθένος ἐν γαστρί', badge: 'LEXICAL',      color: PALETTE.lxx },
  { mt: 'וְקָרָאת שְׁמוֹ',         lxx: 'καὶ καλέσεις τὸ ὄνομα', badge: 'ADDITION',    color: '#059669' },
  { mt: 'עִמָּנוּ אֵל',             lxx: 'Εμμανουηλ',             badge: 'THEOLOGICAL', color: PALETTE.vulgate },
  { mt: 'חֶמְאָה וּדְבַשׁ יֹאכֵל', lxx: 'βούτυρον καὶ μέλι',     badge: 'MINOR',       color: PALETTE.muted },
];

export const SceneDivergence: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = { fps: TIMING.fps };

  const labelStart = Math.floor(SCENE_DURATIONS.divergence * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 120px',
        gap: 0,
      }}
    >
      {/* Column headers */}
      <div style={{ display: 'flex', width: '100%', maxWidth: 900, gap: 12, marginBottom: 16 }}>
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <TraditionBadge tradition="MT" />
        </div>
        <div style={{ width: 120 }} />
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center' }}>
          <TraditionBadge tradition="LXX" />
        </div>
      </div>

      {/* Rows */}
      {ROWS.map((row, i) => {
        const rowStart = 20 + i * 35;
        const rowOpacity = interpolate(frame, [rowStart, rowStart + 15], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const rowY = interpolate(frame, [rowStart, rowStart + 15], [12, 0], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const badgeScale = spring({
          frame: frame - (rowStart + 15),
          fps,
          config: { damping: 12, stiffness: 200 },
        });

        return (
          <div
            key={i}
            style={{
              display: 'flex',
              width: '100%',
              maxWidth: 900,
              gap: 12,
              alignItems: 'center',
              opacity: rowOpacity,
              transform: `translateY(${rowY}px)`,
              marginBottom: 18,
              background: PALETTE.card,
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 8,
              padding: '14px 20px',
            }}
          >
            <div style={{ flex: 1, fontSize: 18, color: PALETTE.fg, textAlign: 'right', direction: 'rtl', fontFamily: 'serif' }}>
              {row.mt}
            </div>
            <div
              style={{
                width: 120,
                textAlign: 'center',
                transform: `scale(${badgeScale})`,
              }}
            >
              <span style={{
                background: row.color,
                color: '#fff',
                fontSize: 10,
                fontWeight: 700,
                padding: '3px 8px',
                borderRadius: 4,
                letterSpacing: '0.06em',
                textTransform: 'uppercase' as const,
                whiteSpace: 'nowrap' as const,
              }}>
                {row.badge}
              </span>
            </div>
            <div style={{ flex: 1, fontSize: 18, color: PALETTE.fg, fontFamily: 'serif', fontStyle: 'italic' }}>
              {row.lxx}
            </div>
          </div>
        );
      })}

      <ToolLabel label="MT / LXX Divergence Analyzer" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
