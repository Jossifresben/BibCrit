import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { DARK, SCENES, FONT_STYLE } from './theme';
import { S01_Title } from './scenes/S01_Title';
import { S02_PipelineOverview } from './scenes/S02_PipelineOverview';
import { S03_UserInput } from './scenes/S03_UserInput';
import { S09_Transition } from './scenes/S09_Transition';
import { S11_Outro } from './scenes/S11_Outro';

// Placeholder — replace each null with real scene import in Task 15
const Placeholder: React.FC<{ label: string }> = ({ label }) => (
  <AbsoluteFill style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
    <div style={{ color: '#6366f1', fontSize: 48, fontWeight: 700 }}>{label}</div>
  </AbsoluteFill>
);

export const PipelineExplainer: React.FC = () => (
  <AbsoluteFill style={{ background: DARK.bg, fontFamily: "'Space Grotesk', sans-serif" }}>
    <style>{FONT_STYLE}</style>

    <Sequence from={SCENES.S1_START}  durationInFrames={SCENES.S1_END  - SCENES.S1_START}>
      <S01_Title />
    </Sequence>
    <Sequence from={SCENES.S2_START}  durationInFrames={SCENES.S2_END  - SCENES.S2_START}>
      <S02_PipelineOverview />
    </Sequence>
    <Sequence from={SCENES.S3_START}  durationInFrames={SCENES.S3_END  - SCENES.S3_START}>
      <S03_UserInput />
    </Sequence>
    <Sequence from={SCENES.S4_START}  durationInFrames={SCENES.S4_END  - SCENES.S4_START}>
      <Placeholder label="S4 Corpus Lookup" />
    </Sequence>
    <Sequence from={SCENES.S5_START}  durationInFrames={SCENES.S5_END  - SCENES.S5_START}>
      <Placeholder label="S5 Cache Check" />
    </Sequence>
    <Sequence from={SCENES.S6_START}  durationInFrames={SCENES.S6_END  - SCENES.S6_START}>
      <Placeholder label="S6 Claude API" />
    </Sequence>
    <Sequence from={SCENES.S7_START}  durationInFrames={SCENES.S7_END  - SCENES.S7_START}>
      <Placeholder label="S7 SSE Stream" />
    </Sequence>
    <Sequence from={SCENES.S8_START}  durationInFrames={SCENES.S8_END  - SCENES.S8_START}>
      <Placeholder label="S8 Output" />
    </Sequence>
    <Sequence from={SCENES.S9_START}  durationInFrames={SCENES.S9_END  - SCENES.S9_START}>
      <S09_Transition />
    </Sequence>
    <Sequence from={SCENES.S10_START} durationInFrames={SCENES.S10_END - SCENES.S10_START}>
      <Placeholder label="S10 UI Demo" />
    </Sequence>
    <Sequence from={SCENES.S11_START} durationInFrames={SCENES.S11_END - SCENES.S11_START}>
      <S11_Outro />
    </Sequence>
  </AbsoluteFill>
);
