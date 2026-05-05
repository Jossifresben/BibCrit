import React from 'react';

interface TypewriterProps {
  text: string;
  localFrame: number;
  startFrame?: number;    // frame when typing begins; default 0
  charsPerFrame?: number; // chars revealed per frame; default 2
  color?: string;
  fontSize?: number;
  fontWeight?: number;
  showCursor?: boolean;
}

export const Typewriter: React.FC<TypewriterProps> = ({
  text,
  localFrame,
  startFrame = 0,
  charsPerFrame = 2,
  color = '#e2e8f0',
  fontSize = 28,
  fontWeight = 600,
  showCursor = true,
}) => {
  const elapsed = Math.max(0, localFrame - startFrame);
  const charsVisible = Math.min(text.length, Math.floor(elapsed * charsPerFrame));
  const isTyping = charsVisible < text.length;
  // Blink cursor: on for 8 frames, off for 8 frames
  const cursorVisible = showCursor && (Math.floor(localFrame / 8) % 2 === 0);

  return (
    <span style={{ color, fontSize, fontWeight, fontFamily: 'Menlo, Monaco, Consolas, monospace' }}>
      {text.slice(0, charsVisible)}
      {isTyping && cursorVisible && (
        <span style={{ opacity: 1, borderRight: `2px solid ${color}`, marginLeft: 2 }} />
      )}
    </span>
  );
};
