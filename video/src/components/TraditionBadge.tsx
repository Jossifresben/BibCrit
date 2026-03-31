import React from 'react';
import { PALETTE } from '../theme';

type Tradition = 'MT' | 'LXX' | 'DSS' | 'SP' | 'IND' | 'ABS' | 'TARGUM' | 'VULGATE';

const COLORS: Record<Tradition, { bg: string; color: string }> = {
  MT:      { bg: PALETTE.mt,      color: '#fff' },
  LXX:     { bg: PALETTE.lxx,     color: '#fff' },
  DSS:     { bg: PALETTE.dss,     color: '#fff' },
  SP:      { bg: PALETTE.sp,      color: '#fff' },
  IND:     { bg: '#ea580c',       color: '#fff' },
  ABS:     { bg: PALETTE.border,  color: PALETTE.muted },
  TARGUM:  { bg: PALETTE.targum,  color: '#fff' },
  VULGATE: { bg: PALETTE.vulgate, color: '#fff' },
};

interface TraditionBadgeProps {
  tradition: Tradition;
  size?: 'sm' | 'md';
}

export const TraditionBadge: React.FC<TraditionBadgeProps> = ({
  tradition,
  size = 'md',
}) => {
  const { bg, color } = COLORS[tradition];
  const fontSize = size === 'sm' ? 11 : 13;
  const padding = size === 'sm' ? '2px 7px' : '4px 10px';

  return (
    <span
      style={{
        display: 'inline-block',
        background: bg,
        color,
        fontSize,
        fontWeight: 700,
        padding,
        borderRadius: 4,
        letterSpacing: '0.05em',
        textTransform: 'uppercase',
      }}
    >
      {tradition}
    </span>
  );
};
