import React from 'react';
import { AbsoluteFill } from 'remotion';
import { PALETTE } from '../theme';

export const Outro: React.FC = () => (
  <AbsoluteFill style={{ background: PALETTE.dark, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <span style={{ fontSize: 40, fontWeight: 700, color: '#fff' }}>bibcrit.app</span>
  </AbsoluteFill>
);
