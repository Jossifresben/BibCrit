import React from 'react';
import { AbsoluteFill, useCurrentFrame, interpolate } from 'remotion';
import { PALETTE, TIMING, SCENE_DURATIONS } from '../theme';
import { ToolLabel } from '../components/ToolLabel';

const NODES = [
  { id: 'proto',  label: 'Proto-Hebrew',    date: '4th–3rd c. BCE', x: 960,  y:  50,  color: '#334155', text: '#fff' },
  { id: 'mt-src', label: 'Pre-Masoretic',   date: '2nd–1st c. BCE', x: 380,  y: 220,  color: '#334155', text: '#fff' },
  { id: 'lxx',    label: 'Old Greek',       date: '3rd–2nd c. BCE', x: 960,  y: 220,  color: PALETTE.lxx, text: '#fff' },
  { id: 'dss',    label: '1QIsaᵃ',          date: 'c. 125 BCE',     x: 1540, y: 220,  color: PALETTE.dss, text: '#fff' },
  { id: 'mt',     label: 'Masoretic Text',  date: '1st–10th c. CE', x: 380,  y: 430,  color: PALETTE.mt,  text: '#fff' },
  { id: 'hex',    label: 'Hexaplaric LXX',  date: 'c. 240 CE',      x: 840,  y: 430,  color: PALETTE.lxx, text: '#fff' },
  { id: 'luc',    label: 'Lucianic LXX',    date: 'c. 300 CE',      x: 1160, y: 430,  color: PALETTE.lxx, text: '#fff' },
  { id: 'aleppo', label: 'Aleppo Codex',    date: 'c. 930 CE',      x: 220,  y: 640,  color: PALETTE.mt,  text: '#fff' },
  { id: 'len',    label: 'Leningrad Codex', date: '1008 CE',        x: 560,  y: 640,  color: PALETTE.mt,  text: '#fff' },
];

const EDGES = [
  ['proto',  'mt-src'], ['proto', 'lxx'],  ['proto',  'dss'],
  ['mt-src', 'mt'],     ['lxx',   'hex'],  ['lxx',    'luc'],
  ['mt',     'aleppo'], ['mt',    'len'],
];

const NODE_W = 220;
const NODE_H = 64;

export const SceneGenealogy: React.FC = () => {
  const frame = useCurrentFrame();
  const labelStart = Math.floor(SCENE_DURATIONS.genealogy * TIMING.labelReveal);

  return (
    <AbsoluteFill
      style={{
        background: PALETTE.parchment,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <svg
        viewBox="0 0 1920 760"
        style={{ width: '100%', height: '100%' }}
        preserveAspectRatio="xMidYMid meet"
      >
        {/* Edges */}
        {EDGES.map(([fromId, toId], i) => {
          const from = NODES.find((n) => n.id === fromId)!;
          const to   = NODES.find((n) => n.id === toId)!;
          const x1 = from.x;
          const y1 = from.y + NODE_H;
          const x2 = to.x;
          const y2 = to.y;
          const midY = (y1 + y2) / 2;
          const d = `M${x1},${y1} C${x1},${midY} ${x2},${midY} ${x2},${y2}`;
          const pathLen = 200;
          const edgeStart = 20 + i * 18;
          const progress = interpolate(frame, [edgeStart, edgeStart + 30], [1, 0], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });

          return (
            <path
              key={i}
              d={d}
              fill="none"
              stroke={PALETTE.border}
              strokeWidth={2}
              strokeDasharray={pathLen}
              strokeDashoffset={progress * pathLen}
            />
          );
        })}

        {/* Nodes */}
        {NODES.map((node, i) => {
          const nodeStart = 5 + i * 22;
          const opacity = interpolate(frame, [nodeStart, nodeStart + 18], [0, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });
          const scale = interpolate(frame, [nodeStart, nodeStart + 18], [0.6, 1], {
            extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
          });

          return (
            <g
              key={node.id}
              transform={`translate(${node.x - NODE_W / 2}, ${node.y})`}
              opacity={opacity}
            >
              <rect
                x={0} y={0}
                width={NODE_W} height={NODE_H}
                rx={8}
                fill={node.color}
                transform={`scale(${scale})`}
                style={{ transformOrigin: `${NODE_W / 2}px ${NODE_H / 2}px` }}
              />
              <text
                x={NODE_W / 2} y={NODE_H / 2 - 9}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={16}
                fontWeight={700}
                fill={node.text}
                fontFamily="'Space Grotesk', sans-serif"
              >
                {node.label}
              </text>
              <text
                x={NODE_W / 2} y={NODE_H / 2 + 12}
                textAnchor="middle"
                dominantBaseline="middle"
                fontSize={12}
                fill="rgba(255,255,255,0.75)"
                fontFamily="'Space Grotesk', sans-serif"
              >
                {node.date}
              </text>
            </g>
          );
        })}
      </svg>

      <ToolLabel label="Manuscript Genealogy" startFrame={labelStart} />
    </AbsoluteFill>
  );
};
