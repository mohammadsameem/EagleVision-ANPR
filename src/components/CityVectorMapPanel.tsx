import React from 'react';
import { Compass, Activity } from 'lucide-react';

interface CityVectorMapPanelProps {
  activeCamera: 'cam-01' | 'cam-02' | 'cam-03';
  globalPos: { x: number; y: number };
  timelineProgress: number;
  incidentTriggered: boolean;
  onSelectCameraNode: (cam: 'cam-01' | 'cam-02' | 'cam-03', targetProgress: number) => void;
}

export const CityVectorMapPanel: React.FC<CityVectorMapPanelProps> = ({
  activeCamera,
  globalPos,
  timelineProgress,
  incidentTriggered,
  onSelectCameraNode,
}) => {
  const nodes: Array<{
    id: 'cam-01' | 'cam-02' | 'cam-03';
    code: string;
    label: string;
    x: number;
    y: number;
    targetProgress: number;
    timestamp: string;
    reIdScore: string;
  }> = [
    {
      id: 'cam-01',
      code: 'CAM-01 (CAM-N4)',
      label: 'Intersection North',
      x: 115,
      y: 68,
      targetProgress: 16,
      timestamp: '09:09:00',
      reIdScore: '0.989',
    },
    {
      id: 'cam-02',
      code: 'CAM-02 (CAM-W2)',
      label: 'Bridge West',
      x: 280,
      y: 135,
      targetProgress: 50,
      timestamp: '09:12:18',
      reIdScore: '0.941',
    },
    {
      id: 'cam-03',
      code: 'CAM-03 (CAM-S1)',
      label: 'Highway South',
      x: 455,
      y: 198,
      targetProgress: 84,
      timestamp: '09:15:40',
      reIdScore: '0.964',
    },
  ];

  return (
    <section
      aria-label="SPATIO-TEMPORAL VECTOR MAP"
      data-testid="panel-city-vector-map"
      className="relative flex flex-col bg-[#0c1017] border border-slate-800/90 rounded-sm overflow-hidden"
    >
      {/* Tactical Header */}
      <div className="flex items-center justify-between gap-2 px-2.5 py-1.5 bg-[#080a0f] border-b border-slate-800/90">
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <Compass className="w-3 h-3 text-cyan-400 shrink-0" />
          <h2 className="text-[11px] font-bold font-display tracking-wider text-slate-100 uppercase truncate">
            04: SPATIO-TEMPORAL VECTOR MAP
          </h2>
          <span className="hidden lg:inline text-slate-700 shrink-0" aria-hidden="true">
            |
          </span>
          <span className="hidden lg:inline text-[10px] text-slate-400 font-mono whitespace-nowrap">
            GIS ROUTE // ID-8042
          </span>
        </div>

        <div className="flex items-center gap-1.5 shrink-0 text-[10px] font-mono text-cyan-400 tabular-nums">
          <Activity className="w-3 h-3" />
          <span>TRACE: {Math.round(timelineProgress)}%</span>
        </div>
      </div>

      {/* High-Fidelity Dark GIS / Topological Vector Map */}
      <div className="relative bg-[#06080c] flex items-center justify-center overflow-hidden">
        <svg
          viewBox="0 0 560 235"
          className="w-full h-[225px] xl:h-[310px] select-none"
          role="img"
          aria-label="GIS topological vector map plotting CAM-01, CAM-02, and CAM-03 with dotted teal route and timestamps for ID-8042"
        >
          <defs>
            <pattern id="gisMinorGrid" width="20" height="20" patternUnits="userSpaceOnUse">
              <path
                d="M 20 0 L 0 0 0 20"
                fill="none"
                stroke="rgba(30, 41, 59, 0.35)"
                strokeWidth="0.6"
              />
            </pattern>
            <pattern id="gisMajorGrid" width="80" height="80" patternUnits="userSpaceOnUse">
              <rect width="80" height="80" fill="url(#gisMinorGrid)" />
              <path
                d="M 80 0 L 0 0 0 80"
                fill="none"
                stroke="rgba(51, 65, 85, 0.45)"
                strokeWidth="0.9"
              />
            </pattern>
          </defs>

          {/* GIS Coordinate Grid Background */}
          <rect width="560" height="235" fill="url(#gisMajorGrid)" />

          {/* Topological Elevation Contours (faint surveyor lines) */}
          <g fill="none" stroke="rgba(51, 65, 85, 0.35)" strokeWidth="0.75" strokeDasharray="3 3">
            <path d="M 10 40 Q 160 20, 320 55 T 550 35" />
            <path d="M 10 190 Q 210 155, 380 185 T 550 160" />
            <path d="M 40 115 Q 240 85, 420 125 T 545 105" />
          </g>

          {/* Hydrological River Channel & Bridge West Span */}
          <path
            d="M 0 178 Q 185 152, 280 135 T 560 88"
            fill="none"
            stroke="rgba(8, 51, 68, 0.42)"
            strokeWidth="22"
          />
          <path
            d="M 0 178 Q 185 152, 280 135 T 560 88"
            fill="none"
            stroke="rgba(6, 182, 212, 0.2)"
            strokeWidth="1"
            strokeDasharray="4 4"
          />

          {/* Municipal Arterial Road Network */}
          <g stroke="rgba(51, 65, 85, 0.55)" strokeWidth="3.5" fill="none">
            <path d="M 30 68 L 510 68" />
            <path d="M 115 12 L 115 222" />
            <path d="M 280 12 L 280 222" />
            <path d="M 455 18 L 455 225" />
            <path d="M 65 198 L 535 198" />
          </g>

          {/* Primary Transit Corridor Base Track */}
          <path
            d="M 65 38 L 115 68 Q 198 92, 280 135 Q 368 172, 455 198 L 525 216"
            fill="none"
            stroke="#1e293b"
            strokeWidth="7"
            strokeLinecap="round"
          />

          {/* Full Continuous Estimated Route of ID-8042 in Thin Dotted Teal Line */}
          <path
            d="M 115 68 Q 198 92, 280 135 Q 368 172, 455 198"
            fill="none"
            stroke="#14b8a6"
            strokeWidth="1.75"
            strokeDasharray="3 3"
          />

          {/* Active Traversed Segment Highlight */}
          <path
            d={`M 115 68 L ${globalPos.x} ${globalPos.y}`}
            fill="none"
            stroke="#06b6d4"
            strokeWidth="2.2"
          />

          {/* Inter-Camera Blind-Spot Telemetry Annotations */}
          <text
            x="185"
            y="88"
            fill="#64748b"
            fontSize="8.5"
            fontFamily="'IBM Plex Mono', 'Fira Code', monospace"
          >
            Δd=4.15km · Δt=198s
          </text>
          <text
            x="355"
            y="156"
            fill="#64748b"
            fontSize="8.5"
            fontFamily="'IBM Plex Mono', 'Fira Code', monospace"
          >
            Δd=3.82km · Δt=202s
          </text>

          {/* Interconnected Camera Nodes (CAM-01 -> CAM-02 -> CAM-03) with Timestamp Markers */}
          {nodes.map((node) => {
            const isCurrent = activeCamera === node.id;
            const isCam2Alert = node.id === 'cam-02' && incidentTriggered;
            const nodeColor = isCam2Alert
              ? '#ef4444'
              : isCurrent
              ? '#06b6d4'
              : '#14b8a6';

            return (
              <g
                key={node.id}
                onClick={() => onSelectCameraNode(node.id, node.targetProgress)}
                className="cursor-pointer"
              >
                {/* Sensor FOV Wedge */}
                <polygon
                  points={`${node.x},${node.y} ${node.x + 32},${node.y - 14} ${node.x + 32},${node.y + 14}`}
                  fill={
                    isCam2Alert
                      ? 'rgba(239, 68, 68, 0.14)'
                      : 'rgba(20, 184, 166, 0.12)'
                  }
                />

                {/* Outer Precision Target Ring */}
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={isCurrent ? 8 : 6}
                  fill="#080a0f"
                  stroke={nodeColor}
                  strokeWidth={isCurrent ? 1.75 : 1.25}
                />
                <circle cx={node.x} cy={node.y} r={2.5} fill={nodeColor} />

                {/* Node Code & Exact Timestamp Callout Tag */}
                <rect
                  x={node.x - 58}
                  y={node.y - 31}
                  width="116"
                  height="19"
                  rx="1"
                  fill="rgba(8, 10, 15, 0.92)"
                  stroke={isCam2Alert ? 'rgba(239, 68, 68, 0.7)' : 'rgba(51, 65, 85, 0.85)'}
                  strokeWidth="0.8"
                />
                <text
                  x={node.x}
                  y={node.y - 19}
                  textAnchor="middle"
                  fill={isCam2Alert ? '#fca5a5' : '#e2e8f0'}
                  fontSize="8.5"
                  fontWeight="600"
                  fontFamily="'IBM Plex Mono', 'Fira Code', monospace"
                >
                  {node.code.split(' ')[0]} · {node.timestamp}
                </text>
              </g>
            );
          })}

          {/* Live Interpolated Vehicle Target Reticle (ID-8042) */}
          <g transform={`translate(${globalPos.x}, ${globalPos.y})`}>
            <circle
              r="8"
              fill={incidentTriggered ? 'rgba(239, 68, 68, 0.22)' : 'rgba(6, 182, 212, 0.2)'}
            />
            <circle
              r="3.5"
              fill={incidentTriggered ? '#ef4444' : '#06b6d4'}
              stroke="#080a0f"
              strokeWidth="1"
            />
            <rect
              x="8"
              y="-8"
              width="58"
              height="14"
              rx="1"
              fill="rgba(8, 10, 15, 0.92)"
              stroke={incidentTriggered ? '#ef4444' : '#06b6d4'}
              strokeWidth="0.8"
            />
            <text
              x="37"
              y="1.5"
              textAnchor="middle"
              fill={incidentTriggered ? '#fca5a5' : '#67e8f9'}
              fontSize="8.5"
              fontWeight="600"
              fontFamily="'IBM Plex Mono', 'Fira Code', monospace"
            >
              ID-8042
            </text>
          </g>

          {/* Bottom-left GIS Coordinate Scale Bar */}
          <g transform="translate(8, 216)">
            <rect width="225" height="14" fill="rgba(8, 10, 15, 0.82)" />
            <text
              x="4"
              y="10"
              fill="#64748b"
              fontSize="8.5"
              fontFamily="'IBM Plex Mono', 'Fira Code', monospace"
            >
              WGS84 // 09:09:00 → 09:12:18 → 09:15:40
            </text>
          </g>
        </svg>
      </div>
    </section>
  );
};
