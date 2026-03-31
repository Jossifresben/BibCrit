import React from 'react';
import { AbsoluteFill } from 'remotion';
import { PALETTE } from '../theme';

export const SceneDivergence: React.FC = () => (
  <AbsoluteFill style={{ background: PALETTE.parchment, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <span style={{ fontSize: 32, fontWeight: 700 }}>MT/LXX Divergence Analyzer</span>
  </AbsoluteFill>
);
