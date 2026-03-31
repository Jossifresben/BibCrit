import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { PALETTE } from '../theme';

const AXES = [
  { label: 'Literalness',       value: 0.72 },
  { label: 'Anthropomorphism',  value: 0.55 },
  { label: 'Messianic',         value: 0.80 },
  { label: 'Harmonization',     value: 0.45 },
  { label: 'Paraphrase',        value: 0.60 },
];

const SIZE   = 260;
const CX     = SIZE / 2;
const CY     = SIZE / 2;
const RADIUS = 100;

function polarToXY(angleRad: number, r: number) {
  return {
    x: CX + r * Math.sin(angleRad),
    y: CY - r * Math.cos(angleRad),
  };
}

interface RadarChartProps {
  startFrame: number;
}

export const RadarChart: React.FC<RadarChartProps> = ({ startFrame }) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - startFrame);

  const n = AXES.length;
  const angleStep = (2 * Math.PI) / n;

  const polygonOpacity = interpolate(localFrame, [50, 70], [0, 0.35], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const polygonPoints = AXES.map((ax, i) => {
    const angle = i * angleStep;
    const pt = polarToXY(angle, RADIUS * ax.value);
    return `${pt.x},${pt.y}`;
  }).join(' ');

  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <svg width={SIZE} height={SIZE} style={{ overflow: 'visible' }}>
      {rings.map((r) => {
        const pts = AXES.map((_, i) => {
          const angle = i * angleStep;
          const pt = polarToXY(angle, RADIUS * r);
          return `${pt.x},${pt.y}`;
        }).join(' ');
        return (
          <polygon
            key={r}
            points={pts}
            fill="none"
            stroke={PALETTE.border}
            strokeWidth={1}
          />
        );
      })}

      {AXES.map((ax, i) => {
        const angle = i * angleStep;
        const end = polarToXY(angle, RADIUS);
        const axisProgress = interpolate(
          localFrame,
          [i * 8, i * 8 + 20],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        const ex = CX + (end.x - CX) * axisProgress;
        const ey = CY + (end.y - CY) * axisProgress;

        const labelPt = polarToXY(angle, RADIUS + 22);
        const labelOpacity = interpolate(
          localFrame,
          [30 + i * 6, 46 + i * 6],
          [0, 1],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );

        return (
          <g key={i}>
            <line
              x1={CX} y1={CY}
              x2={ex} y2={ey}
              stroke={PALETTE.border}
              strokeWidth={1.5}
            />
            <text
              x={labelPt.x}
              y={labelPt.y}
              textAnchor="middle"
              dominantBaseline="middle"
              fontSize={10}
              fill={PALETTE.muted}
              opacity={labelOpacity}
              fontFamily="'Space Grotesk', sans-serif"
              fontWeight={600}
            >
              {ax.label}
            </text>
          </g>
        );
      })}

      <polygon
        points={polygonPoints}
        fill={PALETTE.lxx}
        fillOpacity={polygonOpacity}
        stroke={PALETTE.lxx}
        strokeWidth={2}
        strokeOpacity={Math.min(polygonOpacity * 3, 1)}
      />

      {AXES.map((ax, i) => {
        const angle = i * angleStep;
        const pt = polarToXY(angle, RADIUS * ax.value);
        const dotOpacity = interpolate(localFrame, [55, 70], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        return (
          <circle
            key={i}
            cx={pt.x} cy={pt.y} r={4}
            fill={PALETTE.lxx}
            opacity={dotOpacity}
          />
        );
      })}
    </svg>
  );
};
