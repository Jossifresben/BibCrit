import React from 'react';
import { Composition } from 'remotion';
import { BibCritVideo } from './BibCritVideo';
import { TOTAL_FRAMES, TIMING } from './theme';

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="BibCritShowcase"
      component={BibCritVideo}
      durationInFrames={TOTAL_FRAMES}
      fps={TIMING.fps}
      width={1920}
      height={1080}
    />
  );
};
