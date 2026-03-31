import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';

const WORDS = [
  { lxx: 'ἐν',        vorlage: 'בְּ',      mt: 'בְּ',      status: 'agrees_mt'  },
  { lxx: 'ἀρχῇ',     vorlage: 'רֵאשִׁית', mt: 'רֵאשִׁית', status: 'agrees_mt'  },
  { lxx: 'ἐποίησεν', vorlage: 'בָּרָא',   mt: 'בָּרָא',   status: 'agrees_mt'  },
  { lxx: 'ὁ',        vorlage: '—',         mt: '—',         status: 'idiom_only' },
  { lxx: 'θεὸς',     vorlage: 'אֱלֹהִים', mt: 'אֱלֹהִים', status: 'agrees_mt'  },
  { lxx: 'τὸν',      vorlage: 'אֵת',      mt: 'אֵת',      status: 'agrees_mt'  },
  { lxx: 'οὐρανόν',  vorlage: 'הַשָּׁמַיִם', mt: 'הַשָּׁמַיִם', status: 'agrees_mt' },
];

const STATUS_COLOR: Record<string, string> = {
  agrees_mt:  '#059669',
  unattested: '#dc2626',
  idiom_only: PALETTE.muted,
  agrees_dss: PALETTE.dss,
};

export const SceneBackTranslation: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.backTranslation * TIMING.labelReveal);

  const COLS = [
    { key: 'lxx' as const,     header: 'LXX Greek',           italic: true  },
    { key: 'vorlage' as const, header: 'Vorlage (Hebrew)',     italic: false },
    { key: 'mt' as const,      header: 'MT Hebrew',            italic: false },
  ];

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 60px',
      }}
    >
      {/* Column headers */}
      <div style={{ display: 'flex', width: '100%', maxWidth: 1500, gap: 16, marginBottom: 12 }}>
        {COLS.map((col) => (
          <div key={col.key} style={{ flex: 1, textAlign: 'center', fontSize: 18, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em', color: PALETTE.muted }}>
            {col.header}
          </div>
        ))}
      </div>

      {/* Word grid */}
      <div style={{ display: 'flex', width: '100%', maxWidth: 1500, gap: 16 }}>
        {COLS.map((col) => (
          <div key={col.key} style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
            {WORDS.map((word, i) => {
              const wordStart = 10 + i * 20;
              const opacity = interpolate(frame, [wordStart, wordStart + 12], [0, 1], {
                extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
              });
              const isVorlage = col.key === 'vorlage';
              const bg = isVorlage ? STATUS_COLOR[word.status] + '22' : PALETTE.card;
              const border = isVorlage ? `1.5px solid ${STATUS_COLOR[word.status]}` : `1px solid ${PALETTE.border}`;

              return (
                <div
                  key={i}
                  style={{
                    opacity,
                    background: bg,
                    border,
                    borderRadius: 6,
                    padding: '16px 18px',
                    textAlign: 'center',
                    fontSize: 28,
                    fontFamily: 'serif',
                    fontStyle: col.italic ? 'italic' : 'normal',
                    color: isVorlage ? STATUS_COLOR[word.status] : PALETTE.fg,
                    direction: col.key !== 'lxx' ? 'rtl' : 'ltr',
                  }}
                >
                  {word[col.key]}
                </div>
              );
            })}
          </div>
        ))}
      </div>

      <ToolLabel label="Back-Translation Workbench" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
