import React from 'react';
import { Composition, registerRoot } from 'remotion';
import { BibCritVideo } from './BibCritVideo';
import { PipelineExplainer } from './compositions/PipelineExplainer/index';
import { TOTAL_FRAMES, TIMING } from './theme';

export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition
        id="BibCritShowcase"
        component={BibCritVideo}
        durationInFrames={TOTAL_FRAMES}
        fps={TIMING.fps}
        width={1920}
        height={1080}
      />
      <Composition
        id="PipelineExplainer"
        component={PipelineExplainer}
        durationInFrames={2700}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};

registerRoot(RemotionRoot);
