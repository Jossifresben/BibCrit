import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';
import { TraditionBadge } from '../components/TraditionBadge';

const CARDS = [
  { type: 'Anthropomorphism Avoidance', tradition: 'LXX' as const, ref: 'Exodus 24:10', note: 'MT: "they saw God" → LXX: "they saw the place where the God of Israel stood"' },
  { type: 'Messianic Heightening',      tradition: 'LXX' as const, ref: 'Isaiah 7:14',  note: 'MT: עַלְמָה (young woman) → LXX: παρθένος (virgin)' },
  { type: 'Harmonization',             tradition: 'TARGUM' as const, ref: 'Gen 1:26', note: 'Targum Onkelos softens "Let us make man" to remove plural implied address' },
];

export const SceneTheological: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.theological * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 80px',
        gap: 24,
      }}
    >
      {CARDS.map((card, i) => {
        const cardStart = 15 + i * 50;
        const opacity = interpolate(frame, [cardStart, cardStart + 20], [0, 1], {
          extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
        });
        const x = interpolate(frame, [cardStart, cardStart + 20], [-30, 0], {
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
              padding: '24px 36px',
              opacity,
              transform: `translateX(${x}px)`,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 14 }}>
              <span style={{ fontSize: 24, fontWeight: 700, color: PALETTE.fg }}>{card.type}</span>
              <TraditionBadge tradition={card.tradition} size="sm" />
              <span style={{ fontSize: 18, color: PALETTE.muted, marginLeft: 'auto' }}>{card.ref}</span>
            </div>
            <div style={{ fontSize: 20, color: PALETTE.muted, fontStyle: 'italic' }}>{card.note}</div>
          </div>
        );
      })}

      <ToolLabel label="Theological Revision Detector" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
