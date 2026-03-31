import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const DIST = [
  { label: 'Closer to LXX', pct: 55, color: PALETTE.lxx },
  { label: 'Mixed',          pct: 25, color: '#8e44ad' },
  { label: 'Closer to MT',  pct: 20, color: PALETTE.mt },
];

const CITATIONS = [
  { father: 'Origen',        dates: '184–253 CE', form: 'LXX' as const,    work: 'Contra Celsum 1.35', text: '"ἰδοὺ ἡ παρθένος ἐν γαστρὶ ἕξει…"' },
  { father: 'Justin Martyr', dates: '100–165 CE', form: 'LXX' as const,    work: 'Dialogue with Trypho 43', text: 'Cites LXX verbatim against Jewish MT reading' },
  { father: 'Irenaeus',      dates: '130–202 CE', form: 'TARGUM' as const, work: 'Against Heresies 3.21', text: 'Notes Hebrew uses עַלְמָה, not בְּתוּלָה' },
];

export const ScenePatristic: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.patristic * TIMING.labelReveal);

  const barProgress = interpolate(frame, [10, 50], [0, 1], {
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
        padding: '0 80px',
        gap: 28,
      }}
    >
      {/* Distribution bar */}
      <div style={{ width: '100%', maxWidth: 1500 }}>
        <div style={{ fontSize: 16, fontWeight: 700, color: PALETTE.muted, textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
          Text form distribution — Isaiah 7:14 · 23 citations
        </div>
        <div style={{ display: 'flex', height: 52, borderRadius: 8, overflow: 'hidden', gap: 3 }}>
          {DIST.map((seg) => (
            <div
              key={seg.label}
              style={{
                flex: seg.pct * barProgress,
                background: seg.color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 16,
                fontWeight: 700,
                color: '#fff',
                overflow: 'hidden',
                whiteSpace: 'nowrap' as const,
                transition: 'flex 0.3s',
              }}
            >
              {barProgress > 0.3 ? `${seg.pct}%` : ''}
            </div>
          ))}
        </div>
      </div>

      {/* Citation cards */}
      {CITATIONS.map((c, i) => {
        const cardStart = 55 + i * 40;
        const opacity = interpolate(frame, [cardStart, cardStart + 18], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const y = interpolate(frame, [cardStart, cardStart + 18], [14, 0], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });

        return (
          <div
            key={i}
            style={{
              width: '100%',
              maxWidth: 1500,
              background: PALETTE.card,
              border: `1px solid ${PALETTE.border}`,
              borderRadius: 10,
              padding: '20px 32px',
              opacity,
              transform: `translateY(${y}px)`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 10 }}>
              <span style={{ fontWeight: 700, fontSize: 24, color: PALETTE.fg }}>{c.father}</span>
              <span style={{ fontSize: 18, color: PALETTE.muted }}>{c.dates}</span>
              <TraditionBadge tradition={c.form} size="sm" />
              <span style={{ fontSize: 18, color: PALETTE.muted, marginLeft: 'auto', fontStyle: 'italic' }}>{c.work}</span>
            </div>
            <div style={{ fontSize: 20, color: PALETTE.muted, fontStyle: 'italic' }}>{c.text}</div>
          </div>
        );
      })}

      <ToolLabel label="Patristic Citation Tracker" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
