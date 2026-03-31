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

const SIZE   = 500;
const CX     = SIZE / 2;
const CY     = SIZE / 2;
const RADIUS = 190;

function polarToXY(angleRad: number, r: number) {
  return {
    x: CX + r * Math.sin(angleRad),
    y: CY - r * Math.cos(angleRad),
  };
}

function pointsToPath(points: string): string {
  const pts = points.split(' ');
  return pts.map((pt, i) => `${i === 0 ? 'M' : 'L'}${pt}`).join(' ') + 'Z';
}

interface RadarChartProps {
  startFrame: number;
}

export const RadarChart: React.FC<RadarChartProps> = ({ startFrame }) => {
  const frame = useCurrentFrame();
  const localFrame = Math.max(0, frame - startFrame);

  const n = AXES.length;
  const angleStep = (2 * Math.PI) / n;

  // Axes draw: frames 0–40
  // Polygon stroke draws: frames 50–80
  // Polygon fill fades in: frames 75–105
  // Label text appears: frames 30–60

  const strokeProgress = interpolate(localFrame, [50, 80], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const polygonFillOpacity = interpolate(localFrame, [75, 105], [0, 0.30], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const polygonPoints = AXES.map((ax, i) => {
    const angle = i * angleStep;
    const pt = polarToXY(angle, RADIUS * ax.value);
    return `${pt.x},${pt.y}`;
  }).join(' ');

  const polygonPath = pointsToPath(polygonPoints);

  const rings = [0.25, 0.5, 0.75, 1.0];

  return (
    <svg width={SIZE} height={SIZE} style={{ overflow: 'visible' }}>
      {/* Background rings */}
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
            strokeWidth={1.5}
          />
        );
      })}

      {/* Axes + labels */}
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

        const labelPt = polarToXY(angle, RADIUS + 36);
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
              fontSize={16}
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

      {/* Polygon fill */}
      <path
        d={polygonPath}
        fill={PALETTE.lxx}
        fillOpacity={polygonFillOpacity}
        stroke="none"
      />

      {/* Polygon stroke — animates drawing using pathLength trick */}
      <path
        d={polygonPath}
        fill="none"
        stroke={PALETTE.lxx}
        strokeWidth={3}
        pathLength={1}
        strokeDasharray={1}
        strokeDashoffset={1 - strokeProgress}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Data point dots */}
      {AXES.map((ax, i) => {
        const angle = i * angleStep;
        const pt = polarToXY(angle, RADIUS * ax.value);
        const dotOpacity = interpolate(localFrame, [80, 100], [0, 1], {
          extrapolateLeft: 'clamp',
          extrapolateRight: 'clamp',
        });
        return (
          <circle
            key={i}
            cx={pt.x} cy={pt.y} r={7}
            fill={PALETTE.lxx}
            opacity={dotOpacity}
          />
        );
      })}
    </svg>
  );
};
