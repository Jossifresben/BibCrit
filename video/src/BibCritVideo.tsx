import React from 'react';
import { AbsoluteFill, Audio, staticFile } from 'remotion';
import { TransitionSeries, linearTiming } from '@remotion/transitions';
import { fade } from '@remotion/transitions/fade';
import { TIMING, SCENE_DURATIONS, PALETTE, FONT_STYLE } from './theme';

import { Intro }                from './scenes/Intro';
import { SceneDivergence }      from './scenes/SceneDivergence';
import { SceneDSS }             from './scenes/SceneDSS';
import { SceneBackTranslation } from './scenes/SceneBackTranslation';
import { SceneScribal }         from './scenes/SceneScribal';
import { SceneNumerical }       from './scenes/SceneNumerical';
import { SceneTheological }     from './scenes/SceneTheological';
import { ScenePatristic }       from './scenes/ScenePatristic';
import { SceneGenealogy }       from './scenes/SceneGenealogy';
import { Outro }                from './scenes/Outro';

const T = linearTiming({ durationInFrames: TIMING.transition });

export const BibCritVideo: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: PALETTE.parchment }}>
      <style>{FONT_STYLE}</style>

      <Audio
        src={staticFile('BibCrit.mp3')}
        volume={(f) => {
          // Fade out over last 60 frames (2s)
          if (f > 2640) return Math.max(0, 1 - (f - 2640) / 60);
          return 1;
        }}
      />

      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.intro}>
          <Intro />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.divergence}>
          <SceneDivergence />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.dss}>
          <SceneDSS />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.backTranslation}>
          <SceneBackTranslation />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.scribal}>
          <SceneScribal />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.numerical}>
          <SceneNumerical />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.theological}>
          <SceneTheological />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.patristic}>
          <ScenePatristic />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.genealogy}>
          <SceneGenealogy />
        </TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={fade()} timing={T} />

        <TransitionSeries.Sequence durationInFrames={SCENE_DURATIONS.outro}>
          <Outro />
        </TransitionSeries.Sequence>
      </TransitionSeries>
    </AbsoluteFill>
  );
};
