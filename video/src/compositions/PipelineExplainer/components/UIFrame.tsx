import React from 'react';
import { interpolate } from 'remotion';
import { DARK, EASE_OUT } from '../theme';

interface UIFrameProps {
  localFrame: number;
}

const SECTIONS = [
  {
    title: 'Synthesis',
    tag: '← synthesis key',
    body: 'The MT reads הָעַלְמָה ("the young woman") while the LXX renders παρθένος ("virgin"), a lexical choice that drove centuries of Christological debate. The divergence originates in translational ideology, not manuscript variation.',
  },
  {
    title: 'Key Divergences',
    tag: '← key_divergences array',
    body: '1. עַלְמָה → παρθένος (lexical)  ·  2. וְקָרָאת → καλέσεις (person shift)  ·  3. עִמָּנוּ אֵל → Εμμανουηλ (transliteration vs translation)',
  },
  {
    title: 'Transmission History',
    tag: null,
    body: 'Aquila (2nd c.) corrects παρθένος to νεᾶνις ("young woman") in his revision — evidence that the LXX choice was recognized as interpretive within antiquity.',
  },
  {
    title: 'BibCrit Assessment',
    tag: null,
    body: "Scholarly confidence: High. The lexical shift is attested in Origen's Hexapla (col. V), Irenaeus Adv. Haer. 3.21, and the Dead Sea Scrolls (1QIsaᵃ col. VII reads עלמה without article).",
  },
];

export const UIFrame: React.FC<UIFrameProps> = ({ localFrame }) => {
  // Nav bar fades in first
  const navOpacity = interpolate(localFrame, [0, 20], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  // Passage bar appears at frame 20
  const barOpacity = interpolate(localFrame, [20, 35], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT,
  });

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        background: DARK.uiBg,
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        borderRadius: 12,
      }}
    >
      {/* Nav bar */}
      <div
        style={{
          opacity: navOpacity,
          background: DARK.uiNavBg,
          borderBottom: `1px solid ${DARK.border}`,
          padding: '16px 40px',
          display: 'flex',
          alignItems: 'center',
          gap: 24,
          flexShrink: 0,
        }}
      >
        <div style={{ fontSize: 22, fontWeight: 700, color: DARK.accentLight }}>BibCrit</div>
        <div style={{ fontSize: 15, color: '#64748b' /* nav subtitle — between textDim and textMuted */ }}>MT / LXX Divergence Analyzer</div>
      </div>

      {/* Passage bar */}
      <div
        style={{
          opacity: barOpacity,
          background: DARK.uiNavBg,
          padding: '20px 40px',
          borderBottom: `1px solid ${DARK.border}`,
          display: 'flex',
          alignItems: 'center',
          gap: 16,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            background: DARK.surface,
            border: `1px solid ${DARK.accent}`,
            borderRadius: 8,
            padding: '10px 20px',
            fontSize: 20,
            color: DARK.text,
            fontWeight: 600,
            minWidth: 300,
          }}
        >
          Isaiah 7:14
        </div>
        <div
          style={{
            background: DARK.accent,
            color: 'white',
            padding: '10px 24px',
            borderRadius: 8,
            fontSize: 16,
            fontWeight: 700,
          }}
        >
          Analyze
        </div>
      </div>

      {/* Analysis sections */}
      <div style={{ flex: 1, padding: '28px 40px', display: 'flex', flexDirection: 'column', gap: 20, overflow: 'hidden' }}>
        {SECTIONS.map((section, i) => {
          const sectionStart = 45 + i * 60;
          const sectionOpacity = interpolate(
            localFrame,
            [sectionStart, sectionStart + 20],
            [0, 1],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
          );
          const sectionY = interpolate(
            localFrame,
            [sectionStart, sectionStart + 20],
            [16, 0],
            { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
          );

          return (
            <div
              key={i}
              style={{
                opacity: sectionOpacity,
                transform: `translateY(${sectionY}px)`,
                background: DARK.surface,
                border: `1px solid ${DARK.border}`,
                borderRadius: 10,
                padding: '18px 24px',
                position: 'relative',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 10 }}>
                <div style={{ fontSize: 16, fontWeight: 700, color: DARK.accentLight }}>
                  {section.title}
                </div>
                {section.tag && (
                  <div
                    style={{
                      fontSize: 12,
                      color: DARK.accent,
                      background: DARK.uiTagBg,
                      border: `1px solid ${DARK.accent}`,
                      borderRadius: 4,
                      padding: '2px 10px',
                      fontStyle: 'italic',
                    }}
                  >
                    {section.tag}
                  </div>
                )}
              </div>
              <div style={{ fontSize: 14, color: DARK.textMuted, lineHeight: 1.6 }}>
                {section.body}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
