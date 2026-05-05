import React from 'react';
import { AbsoluteFill, Sequence } from 'remotion';
import { DARK, SCENES, FONT_STYLE } from './theme';
import { S01_Title } from './scenes/S01_Title';
import { S02_PipelineOverview } from './scenes/S02_PipelineOverview';
import { S03_UserInput } from './scenes/S03_UserInput';
import { S04_CorpusLookup } from './scenes/S04_CorpusLookup';
import { S05_CacheCheck } from './scenes/S05_CacheCheck';
import { S06_ClaudeAPI } from './scenes/S06_ClaudeAPI';
import { S07_SSEStream } from './scenes/S07_SSEStream';
import { S08_Output } from './scenes/S08_Output';
import { S09_Transition } from './scenes/S09_Transition';
import { S10_UIDemo } from './scenes/S10_UIDemo';
import { S11_Outro } from './scenes/S11_Outro';

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
      <S04_CorpusLookup />
    </Sequence>
    <Sequence from={SCENES.S5_START}  durationInFrames={SCENES.S5_END  - SCENES.S5_START}>
      <S05_CacheCheck />
    </Sequence>
    <Sequence from={SCENES.S6_START}  durationInFrames={SCENES.S6_END  - SCENES.S6_START}>
      <S06_ClaudeAPI />
    </Sequence>
    <Sequence from={SCENES.S7_START}  durationInFrames={SCENES.S7_END  - SCENES.S7_START}>
      <S07_SSEStream />
    </Sequence>
    <Sequence from={SCENES.S8_START}  durationInFrames={SCENES.S8_END  - SCENES.S8_START}>
      <S08_Output />
    </Sequence>
    <Sequence from={SCENES.S9_START}  durationInFrames={SCENES.S9_END  - SCENES.S9_START}>
      <S09_Transition />
    </Sequence>
    <Sequence from={SCENES.S10_START} durationInFrames={SCENES.S10_END - SCENES.S10_START}>
      <S10_UIDemo />
    </Sequence>
    <Sequence from={SCENES.S11_START} durationInFrames={SCENES.S11_END - SCENES.S11_START}>
      <S11_Outro />
    </Sequence>
  </AbsoluteFill>
);
