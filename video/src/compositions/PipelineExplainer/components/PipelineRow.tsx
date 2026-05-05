import React from 'react';
import { interpolate } from 'remotion';
import { DARK, PIPELINE_STAGES, EASE_OUT } from '../theme';
import { PipelineBox } from './PipelineBox';
import { Arrow } from './Arrow';

interface PipelineRowProps {
  activeIndex: number;   // -1 = none active, 0–5 = active stage
  revealUpTo: number;    // how many boxes have appeared (0–6); used in S02
  localFrame: number;    // local frame from parent scene
  sceneLength: number;   // total duration of the current scene
}

export const PipelineRow: React.FC<PipelineRowProps> = ({
  activeIndex, revealUpTo, localFrame, sceneLength
}) => {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 0,
        width: '100%',
      }}
    >
      {PIPELINE_STAGES.map((stage, i) => {
        const isVisible = i < revealUpTo;
        // In S02 (reveal mode), each box appears 20 frames after the previous
        const boxRevealFrame = i * 20;
        const boxOpacity = interpolate(
          localFrame,
          [boxRevealFrame, boxRevealFrame + 15],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: EASE_OUT }
        );

        // For S03-S08, revealUpTo = 6 so boxOpacity is always 1 after 15 frames
        const effectiveOpacity = isVisible ? boxOpacity : 0;

        // Arrow after each box except the last
        const arrowRevealFrame = boxRevealFrame + 15;
        const arrowProgress = i < PIPELINE_STAGES.length - 1
          ? interpolate(
              localFrame,
              [arrowRevealFrame, arrowRevealFrame + 12],
              [0, 1],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
            )
          : 0;

        return (
          <React.Fragment key={stage.id}>
            <div style={{ opacity: effectiveOpacity }}>
              <PipelineBox
                label={stage.label}
                sub={stage.sub}
                isActive={activeIndex === i}
                localFrame={localFrame}
                sceneLength={sceneLength}
                isVisible={true}
              />
            </div>
            {i < PIPELINE_STAGES.length - 1 && (
              <div style={{ opacity: i < revealUpTo - 1 ? 1 : 0 }}>
                <Arrow revealProgress={arrowProgress} />
              </div>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};
