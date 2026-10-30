import React, { useState } from 'react';
import {
  Activity,
  Cpu,
  FileJson,
  FileText,
  Download,
  AlertOctagon,
  Terminal,
  ChevronDown,
  ChevronUp,
  Car,
  ShieldAlert,
  CheckCircle2,
} from 'lucide-react';
import {
  HandoverEvent,
  ForensicReport,
  NebiusApiLogEntry,
  CrossCameraAnprComparison,
  AnalyzedVehicleSummary,
} from '../utils/reidEngine';

interface ForensicSidebarProps {
  handovers: HandoverEvent[];
  matchedHandoverIds: string[];
  activeCamera: 'cam-01' | 'cam-02' | 'cam-03';
  onSelectHandoverCamera: (cam: 'cam-01' | 'cam-02' | 'cam-03', targetProgress: number) => void;
  anprComparison: CrossCameraAnprComparison;
  forensicReport: ForensicReport | null;
  isGeneratingReport: boolean;
  streamingStepText: string;
  onGenerateReport: () => void;
  apiLogs: NebiusApiLogEntry[];
  selectedModel: string;
  aiSearchExplanation: string | null;
  vehicleInventory: AnalyzedVehicleSummary[];
  selectedVehicleId: string | null;
  onSelectVehicle: (id: string) => void;
}

/**
 * Renders either a real Base64 JPEG crop from the uploaded/live HTML5 <video>
 * (`canvas.toDataURL('image/jpeg', 0.92)`) or a night-filtered CCTV ANPR crop thumbnail.
 */
const KeyframeCropThumbnail: React.FC<{
  cameraId: 'cam-01' | 'cam-02' | 'cam-03';
  isAnomaly?: boolean;
  thumbnailDataUrl?: string;
  plateText?: string;
  size?: 'sm' | 'md';
}> = ({ cameraId, isAnomaly = false, thumbnailDataUrl, plateText = '', size = 'sm' }) => {
  const camTag =
    cameraId === 'cam-01' ? 'CAM-01 // ENTRY' : cameraId === 'cam-02' ? 'CAM-02 // EXIT' : 'CAM-03 // HWY';

  const dimClass = size === 'md' ? 'w-full h-[56px]' : 'w-[74px] h-[46px] shrink-0';

  return (
    <div
      className={`${dimClass} bg-[#0b0f17] border border-slate-800 rounded-[2px] relative overflow-hidden select-none shadow-inner`}
    >
      {thumbnailDataUrl ? (
        <img
          src={thumbnailDataUrl}
          alt={`Cropped vehicle frame from ${camTag}`}
          referrerPolicy="no-referrer"
          className="w-full h-full object-cover"
        />
      ) : (
        <svg viewBox="0 0 120 56" className="w-full h-full">
          <defs>
            <linearGradient id="cctvAsphalt" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#111622" />
              <stop offset="100%" stopColor="#1e2535" />
            </linearGradient>
            <linearGradient id="silverSwiftBody" x1="0" y1="0" x2="1" y2="1">
              <stop offset="0%" stopColor="#94a3b8" />
              <stop offset="40%" stopColor="#e2e8f0" />
              <stop offset="80%" stopColor="#cbd5e1" />
              <stop offset="100%" stopColor="#64748b" />
            </linearGradient>
          </defs>

          {/* Deep asphalt roadway background */}
          <rect width="120" height="56" fill="url(#cctvAsphalt)" />

          {/* Road lane line */}
          <line
            x1="0"
            y1="46"
            x2="120"
            y2="46"
            stroke="rgba(241,245,249,0.35)"
            strokeWidth="1.2"
            strokeDasharray="14 10"
          />

          {/* Headlight beam cone */}
          <polygon
            points="78,21 120,12 120,38 78,29"
            fill="rgba(254,240,138,0.14)"
          />

          {/* Drop shadow under chassis */}
          <ellipse cx="58" cy="28" rx="26" ry="9" fill="rgba(0,0,0,0.6)" />

          {/* Realistic vehicle body */}
          <g transform={isAnomaly ? 'translate(58, 24) rotate(10)' : 'translate(58, 24)'}>
            {/* Main car body */}
            <rect x="-24" y="-9" width="48" height="18" rx="4" fill="url(#silverSwiftBody)" />
            {/* Wheels */}
            <rect x="-18" y="-11" width="7" height="2" fill="#090d14" />
            <rect x="11" y="-11" width="7" height="2" fill="#090d14" />
            <rect x="-18" y="9" width="7" height="2" fill="#090d14" />
            <rect x="11" y="9" width="7" height="2" fill="#090d14" />
            {/* Windshield & roof */}
            <rect x="-11" y="-6.5" width="22" height="13" rx="2.5" fill="#0f172a" />
            {/* Glass reflection */}
            <polygon points="-9,-5.5 -1,-5.5 -6,5.5 -10,5.5" fill="rgba(255,255,255,0.22)" />
            {/* Headlights */}
            <rect x="22" y="-7.5" width="2" height="3" fill="#fef08a" />
            <rect x="22" y="4.5" width="2" height="3" fill="#fef08a" />
            {/* Taillights */}
            <rect
              x="-24"
              y="-7"
              width="2"
              height="3"
              fill={isAnomaly ? '#ef4444' : '#dc2626'}
            />
            <rect
              x="-24"
              y="4"
              width="2"
              height="3"
              fill={isAnomaly ? '#ef4444' : '#dc2626'}
            />
          </g>

          {/* Authentic High-Security Indian Registration Plate (HSRP) */}
          <rect x="22" y="38" width="5" height="13" fill="#0284c7" />
          <rect x="27" y="38" width="69" height="13" fill="#f8fafc" />
          <rect x="22" y="38" width="74" height="13" fill="none" stroke="#090d16" strokeWidth="0.8" />
          <text
            x="61"
            y="47.5"
            textAnchor="middle"
            fill="#090d16"
            fontSize="7"
            fontFamily="'IBM Plex Mono', 'Fira Code', monospace"
            fontWeight="700"
          >
            {plateText}
          </text>

          {/* Industrial Corner L-brackets */}
          <g stroke={isAnomaly ? '#ef4444' : '#06b6d4'} strokeWidth="1" fill="none">
            <path d="M 12 12 L 8 12 L 8 16" />
            <path d="M 108 12 L 112 12 L 112 16" />
            <path d="M 8 48 L 8 52 L 12 52" />
            <path d="M 112 48 L 112 52 L 108 52" />
          </g>
        </svg>
      )}
      <div className="absolute top-0.5 left-0.5 px-1 py-0 bg-black/85 text-[6.5px] font-mono text-cyan-300 leading-tight">
        {camTag}
      </div>
    </div>
  );
};

export const ForensicSidebar: React.FC<ForensicSidebarProps> = ({
  handovers,
  matchedHandoverIds,
  activeCamera,
  onSelectHandoverCamera,
  anprComparison,
  forensicReport,
  isGeneratingReport,
  streamingStepText,
  onGenerateReport,
  apiLogs,
  selectedModel,
  aiSearchExplanation,
  vehicleInventory,
  selectedVehicleId,
  onSelectVehicle,
}) => {
  const [reportFormat, setReportFormat] = useState<'vehicles' | 'markdown' | 'json'>('vehicles');
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(false);

  const progressMap: Record<'cam-01' | 'cam-02' | 'cam-03', number> = {
    'cam-01': 16,
    'cam-02': 50,
    'cam-03': 84,
  };

  const handleExportReport = () => {
    if (!forensicReport) return;
    const blob = new Blob([JSON.stringify(forensicReport, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${forensicReport.reportId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const latestLog = apiLogs[0] || null;

  return (
    <aside
      aria-label="RE-ID TRANSITIONS & ANPR LOG"
      className="w-full xl:w-[465px] xl:max-h-[calc(100vh-100px)] shrink-0 flex flex-col bg-[#0c1017] border border-slate-800/90 rounded-sm overflow-hidden"
    >
      {/* TOP HALF: RE-ID TRANSITIONS & ANPR LOG + SIDE-BY-SIDE CAM 01 vs CAM 02 COMPARISON CARD */}
      <div className="p-2.5 border-b border-slate-800/90">
        <div className="flex items-center justify-between mb-1.5">
          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <h2 className="text-[11px] font-bold font-display tracking-wider text-slate-100 uppercase">
              RE-ID TRANSITIONS &amp; ANPR LOG
            </h2>
          </div>
          <span className="text-[9.5px] font-mono text-emerald-400 tabular-nums">
            ANPR + VLM // ACTIVE
          </span>
        </div>

        {/* Live Side-by-Side CAM 01 vs CAM 02 ANPR & Make/Model Comparison Card */}
        <div
          data-testid="anpr-comparison-card"
          className="mb-2 p-2 rounded-[2px] bg-[#080a0f] border border-cyan-500/40 font-mono space-y-1.5"
        >
          <div className="flex items-center justify-between gap-1">
            <span className="text-[9.5px] font-bold text-emerald-300 tracking-tight">
              {anprComparison.statusBadge}
            </span>
            <span className="text-[9px] text-cyan-300 tabular-nums">
              cos_sim: {anprComparison.cosineSim.toFixed(2)}
            </span>
          </div>

          {/* Side-by-Side Cropped Snapshots from Video 1 (CAM 01) and Video 2 (CAM 02) */}
          <div className="grid grid-cols-2 gap-1.5">
            <div>
              <KeyframeCropThumbnail
                cameraId="cam-01"
                thumbnailDataUrl={anprComparison.cam01Capture.cropDataUrl}
                plateText={anprComparison.cam01Plate}
                size="md"
              />
              <div className="mt-0.5 flex items-center justify-between text-[8.5px] text-slate-400 tabular-nums">
                <span>VIDEO 1 (CAM 01)</span>
                <span className="text-slate-200 font-semibold">{anprComparison.cam01Plate}</span>
              </div>
            </div>
            <div>
              <KeyframeCropThumbnail
                cameraId="cam-02"
                isAnomaly={true}
                thumbnailDataUrl={anprComparison.cam02Capture.cropDataUrl}
                plateText={anprComparison.cam02Plate}
                size="md"
              />
              <div className="mt-0.5 flex items-center justify-between text-[8.5px] text-slate-400 tabular-nums">
                <span>VIDEO 2 (CAM 02)</span>
                <span className="text-slate-200 font-semibold">{anprComparison.cam02Plate}</span>
              </div>
            </div>
          </div>

          {/* Recognized Make/Model & Exact ANPR Plate Match Telemetry */}
          <div className="pt-1 border-t border-slate-800/90 space-y-0.5 text-[9.5px]">
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-400 shrink-0">Detected Model:</span>
              <span
                data-testid="anpr-detected-model"
                className="text-slate-100 font-semibold truncate"
              >
                {anprComparison.detectedModel}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-400 shrink-0">ANPR Plate Match:</span>
              <span
                data-testid="anpr-plate-match"
                className="text-cyan-300 font-semibold truncate tabular-nums"
              >
                {anprComparison.anprPlateMatchText}
              </span>
            </div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-slate-400 shrink-0">Visual Cosine Similarity:</span>
              <span className="text-emerald-400 font-semibold tabular-nums">
                cos_sim: {anprComparison.cosineSim.toFixed(2)} ( Body:{' '}
                {anprComparison.cam01Capture.body_type} )
              </span>
            </div>
          </div>
        </div>

        {aiSearchExplanation && (
          <div className="mb-1.5 px-2 py-1 bg-cyan-950/30 border border-cyan-500/40 rounded-[2px] text-[10px] font-mono text-cyan-200 leading-snug">
            <span className="font-semibold text-cyan-400">[NEMOTRON NL-SEARCH]: </span>
            {aiSearchExplanation}
          </div>
        )}

        {/* Chronological Camera Handover Sequence */}
        <div
          className="space-y-1 max-h-[118px] overflow-y-auto pr-0.5"
          role="list"
          aria-label="Cross-camera handover timeline"
        >
          {handovers.map((item) => {
            const isMatched = matchedHandoverIds.includes(item.id);
            const isCurrent = activeCamera === item.cameraId;
            const isAnomaly = item.status === 'ANOMALY_TRIGGERED';

            return (
              <div
                key={item.id}
                role="listitem"
                onClick={() =>
                  onSelectHandoverCamera(item.cameraId, progressMap[item.cameraId])
                }
                className={`p-1.5 rounded-[2px] border transition-colors cursor-pointer flex items-start gap-2 ${
                  isAnomaly
                    ? 'bg-red-950/20 border-red-500/50 hover:border-red-400'
                    : isCurrent
                    ? 'bg-cyan-950/20 border-cyan-500/50'
                    : isMatched
                    ? 'bg-[#080a0f] border-slate-800 hover:border-slate-700'
                    : 'bg-[#080a0f]/50 border-slate-800/50 opacity-55'
                }`}
              >
                <KeyframeCropThumbnail
                  cameraId={item.cameraId}
                  isAnomaly={isAnomaly}
                  thumbnailDataUrl={item.thumbnailDataUrl}
                  plateText={item.licensePlate || anprComparison.cam01Plate}
                />

                <div className="flex-1 min-w-0 font-mono">
                  <div className="flex items-center justify-between text-[9.5px] tabular-nums mb-0.5">
                    <span className="font-semibold text-slate-100 truncate">
                      {item.locationCode} · [{item.licensePlate || anprComparison.cam01Plate}]
                    </span>
                    <span className="text-slate-400 shrink-0">{item.timestamp}</span>
                  </div>

                  <div className="flex items-center justify-between text-[9px] tabular-nums mb-0.5">
                    <span className={isAnomaly ? 'text-red-300' : 'text-cyan-400'}>
                      {item.makeModel || anprComparison.detectedModel} · cos_sim:{' '}
                      {item.cosineSim.toFixed(2)}
                    </span>
                    <span
                      className={
                        item.speedDeltaKmh < 0
                          ? 'text-red-400 font-semibold'
                          : 'text-slate-300'
                      }
                    >
                      {item.entrySpeedKmh}→{item.exitSpeedKmh} km/h
                    </span>
                  </div>

                  <p className="text-[9px] text-slate-400 leading-tight truncate">
                    {item.notes}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* BOTTOM HALF: NVIDIA Nemotron-70B Forensic Output + Nebius Inspector */}
      <div className="flex-1 flex flex-col p-2.5 min-h-0">
        <div className="flex items-center justify-between gap-2 mb-1.5">
          <div className="flex items-center gap-1.5 min-w-0">
            <Cpu className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <h2 className="text-[11px] font-bold font-display tracking-wider text-slate-100 uppercase truncate">
              NVIDIA Nemotron-70B Forensic Output
            </h2>
          </div>

          <div className="flex items-center gap-1 bg-[#080a0f] p-0.5 rounded-[2px] border border-slate-800 shrink-0 font-mono">
            <button
              type="button"
              onClick={() => setReportFormat('vehicles')}
              className={`px-2 py-0.5 text-[9.5px] rounded-[2px] transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                reportFormat === 'vehicles'
                  ? 'bg-cyan-500 text-slate-950 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Car className="w-2.5 h-2.5 inline mr-1" />
              VEHICLES ({vehicleInventory.length})
            </button>
            <button
              type="button"
              onClick={() => setReportFormat('markdown')}
              className={`px-2 py-0.5 text-[9.5px] rounded-[2px] transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                reportFormat === 'markdown'
                  ? 'bg-slate-800 text-slate-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileText className="w-2.5 h-2.5 inline mr-1" />
              AUDIT LOG
            </button>
            <button
              type="button"
              onClick={() => setReportFormat('json')}
              className={`px-2 py-0.5 text-[9.5px] rounded-[2px] transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                reportFormat === 'json'
                  ? 'bg-slate-800 text-slate-100 font-semibold'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FileJson className="w-2.5 h-2.5 inline mr-1" />
              RAW JSON
            </button>
          </div>
        </div>

        {/* Actionable Flat Tactical Button */}
        <button
          type="button"
          onClick={onGenerateReport}
          disabled={isGeneratingReport}
          data-testid="generate-forensic-report-btn"
          className="w-full py-1.5 px-3 mb-1.5 bg-slate-800 hover:bg-slate-700 disabled:opacity-50 border border-slate-600 text-slate-100 font-mono font-semibold text-[10px] tracking-tight rounded-[2px] transition-colors flex items-center justify-center cursor-pointer whitespace-nowrap shrink-0"
        >
          <span>
            {isGeneratingReport
              ? `[ CALLING NEBIUS (${selectedModel.split('/')[1] || selectedModel})... ]`
              : '[ GENERATE FORENSIC INCIDENT REPORT ]'}
          </span>
        </button>

        {isGeneratingReport && (
          <div className="mb-1.5 px-2 py-1 rounded-[2px] bg-[#080a0f] border border-cyan-500/40 text-[9.5px] font-mono text-cyan-300">
            {streamingStepText}
          </div>
        )}

        {/* Dense Professional Content Container: Vehicles List or Audit Log or JSON */}
        <div
          data-testid="forensic-report-container"
          className="flex-1 overflow-y-auto pr-1 text-[10px] text-slate-300 min-h-[135px]"
        >
          {reportFormat === 'vehicles' ? (
            <div className="space-y-1.5">
              <div className="flex items-center justify-between pb-1 border-b border-slate-800 text-[9px] font-mono text-slate-400">
                <span>DETECTED FLEET // {vehicleInventory.length} VEHICLES CLASSIFIED</span>
                <span className="text-emerald-400 font-semibold">ALPR + VLM ACTIVE</span>
              </div>
              {vehicleInventory.map((veh) => {
                const isSelected = selectedVehicleId === veh.id;
                return (
                  <div
                    key={`${veh.id}-${veh.cameraId}`}
                    onClick={() => onSelectVehicle(veh.id)}
                    className={`p-2 rounded-[2px] border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-cyan-950/40 border-cyan-500/70 shadow-sm'
                        : veh.isAnomaly
                        ? 'bg-red-950/20 border-red-500/50 hover:border-red-400'
                        : 'bg-[#080a0f] border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex items-center gap-1.5 min-w-0">
                        {veh.thumbnailDataUrl ? (
                          <img
                            src={veh.thumbnailDataUrl}
                            alt={veh.makeModel}
                            className="w-10 h-6 object-cover rounded-[1px] border border-slate-700 shrink-0"
                          />
                        ) : (
                          <div className="w-10 h-6 bg-slate-900 border border-slate-800 flex items-center justify-center shrink-0">
                            <Car className="w-3 h-3 text-slate-500" />
                          </div>
                        )}
                        <div className="min-w-0">
                          <div className="flex items-center gap-1">
                            <span
                              className={`px-1 py-0 text-[8.5px] font-bold rounded-[1px] ${
                                veh.cosineSim >= 0.85
                                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-500/40'
                                  : 'bg-slate-800 text-slate-300'
                              }`}
                            >
                              ID-{veh.id}
                            </span>
                            <span className="text-[10px] font-bold text-slate-100 truncate">
                              {veh.makeModel}
                            </span>
                          </div>
                          <span className="text-[9px] text-slate-400 block truncate">
                            {veh.bodyType} • {veh.color}
                          </span>
                        </div>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="inline-flex items-center gap-1 px-1.5 py-0 bg-black/70 border border-slate-700 rounded-[2px]">
                          <span className="w-1 h-2 bg-blue-500 rounded-[1px]" />
                          <span className="text-[9.5px] font-bold text-slate-100 tabular-nums">
                            {veh.licensePlate}
                          </span>
                        </div>
                        <span className="text-[8.5px] text-emerald-400 block tabular-nums">
                          {(veh.plateConfidence * 100).toFixed(0)}% OCR
                        </span>
                      </div>
                    </div>

                    <div className="mt-1.5 pt-1 border-t border-slate-800/80 flex items-center justify-between text-[9px] text-slate-400 tabular-nums">
                      <span className="truncate">{veh.cameraName.split('-')[0]}</span>
                      <div className="flex items-center gap-2">
                        <span className="text-slate-200 font-semibold">{veh.speedKmh} km/h</span>
                        {veh.isAnomaly ? (
                          <span className="text-red-400 font-bold">[ANOMALY]</span>
                        ) : veh.cosineSim >= 0.85 ? (
                          <span className="text-emerald-400 font-semibold">[MATCH {(veh.cosineSim * 100).toFixed(0)}%]</span>
                        ) : (
                          <span className="text-slate-500">[NOMINAL]</span>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : !forensicReport ? (
            <div className="h-32 flex flex-col items-center justify-center text-center px-4 border border-dashed border-slate-800 rounded-[2px]">
              <AlertOctagon className="w-5 h-5 text-slate-500 mb-1" />
              <p className="text-[10.5px] font-medium text-slate-300">
                NO FORENSIC DOSSIER BUFFERED
              </p>
            </div>
          ) : reportFormat === 'json' ? (
            <pre className="p-2 rounded-[2px] bg-[#080a0f] border border-slate-800 text-[9.5px] font-mono text-cyan-300 overflow-x-auto leading-relaxed">
              {JSON.stringify(forensicReport, null, 2)}
            </pre>
          ) : (
            <div className="space-y-2 bg-[#080a0f] p-2 rounded-[2px] border border-slate-800/90 leading-snug">
              <div className="flex items-center justify-between pb-1 border-b border-slate-800 text-[9px] font-mono text-slate-400">
                <span>
                  DOC // {forensicReport.reportId} · {anprComparison.cam01Plate}
                </span>
                <button
                  type="button"
                  onClick={handleExportReport}
                  className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300 cursor-pointer"
                >
                  <Download className="w-2.5 h-2.5" />
                  <span>[ EXPORT JSON ]</span>
                </button>
              </div>

              <div>
                <h3 className="text-[9.5px] font-bold text-slate-100 uppercase tracking-wider mb-0.5 font-mono">
                  I. Executive Summary ({anprComparison.detectedModel} | {anprComparison.cam01Plate})
                </h3>
                <p className="text-[9.5px] text-slate-200 leading-relaxed font-sans">
                  {forensicReport.executiveSummary}
                </p>
              </div>

              <div className="pt-1.5 border-t border-slate-800/80">
                <h3 className="text-[9.5px] font-bold text-slate-100 uppercase tracking-wider mb-0.5">
                  II. Kinematic &amp; Environmental Probable Cause
                </h3>
                <div className="grid grid-cols-2 gap-1.5 my-1 p-1.5 bg-[#0c1017] border border-slate-800 text-[9px] tabular-nums">
                  <div>
                    <span className="text-slate-500 block">DECEL // DELTA:</span>
                    <span className="text-red-400 font-semibold">
                      {forensicReport?.kinematicProbableCause?.speedDropKmh || 'N/A'}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-500 block">ANPR // PLATE MATCH:</span>
                    <span className="text-emerald-300 font-semibold">
                      {anprComparison.cam01Plate} (100% EXACT)
                    </span>
                  </div>
                </div>
                <p className="text-[9.5px] text-slate-200 leading-relaxed font-sans">
                  {forensicReport.kinematicProbableCause.analysis}
                </p>
              </div>

              <div className="pt-1.5 border-t border-slate-800/80">
                <h3 className="text-[9.5px] font-bold text-slate-100 uppercase tracking-wider mb-1 font-mono">
                  III. Multimodal Multi-Camera Timeline
                </h3>
                <div className="space-y-1">
                  {forensicReport.crossCameraTimeline.map((step, i) => (
                    <div
                      key={i}
                      className="p-1.5 bg-[#0c1017] border border-slate-800/80 text-[9px]"
                    >
                      <div className="flex items-center justify-between text-slate-200 tabular-nums font-mono">
                        <span className="font-semibold">
                          {step.timestamp} · {step.camera}
                        </span>
                        <span className="text-cyan-400">{step.reIdScore}</span>
                      </div>
                      <p className="text-slate-200 mt-0.5 font-sans leading-normal">{step.eventDescription}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="pt-1.5 border-t border-slate-800/80">
                <h3 className="text-[9.5px] font-bold text-slate-100 uppercase tracking-wider mb-0.5 font-mono">
                  IV. Probable Liability / Fault Attribution
                </h3>
                <div className="flex items-center justify-between text-[9px] mb-0.5 font-mono">
                  <span className="text-slate-200 font-semibold truncate">
                    {forensicReport.liabilityAndFault.primaryFaultId}
                  </span>
                  <span className="text-red-400 font-bold tabular-nums shrink-0">
                    {forensicReport.liabilityAndFault.estimatedFaultPercentage}% FAULT
                  </span>
                </div>
                <p className="text-[9.5px] text-slate-200 leading-relaxed font-sans">
                  {forensicReport.liabilityAndFault.judicialAssessment}
                </p>
              </div>

              <div className="pt-1.5 border-t border-slate-800/80">
                <h3 className="text-[9.5px] font-bold text-slate-100 uppercase tracking-wider mb-0.5 font-mono">
                  V. Judicial / Municipal Incident Recommendation
                </h3>
                <ul className="space-y-0.5 text-[9px] text-slate-200 list-disc pl-4 font-sans">
                  {forensicReport.recommendations.emergencyDispatch.map((rec, i) => (
                    <li key={`ed-${i}`}>
                      <span className="text-cyan-400 font-semibold">[DISPATCH]</span> {rec}
                    </li>
                  ))}
                  {forensicReport.recommendations.cityPlannerActions.map((rec, i) => (
                    <li key={`cp-${i}`}>
                      <span className="text-emerald-400 font-semibold">[CIVIL ENG]</span> {rec}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Live Nebius API Request / Response Inspector Drawer */}
        <div
          data-testid="nebius-api-inspector"
          className="mt-1.5 pt-1.5 border-t border-slate-800/90 font-mono"
        >
          <button
            type="button"
            onClick={() => setIsInspectorOpen((o) => !o)}
            className="w-full flex items-center justify-between text-[9.5px] text-cyan-400 hover:text-cyan-300 cursor-pointer"
          >
            <span className="flex items-center gap-1.5 font-semibold">
              <Terminal className="w-3 h-3" />
              <span>NEBIUS API REQUEST / RESPONSE INSPECTOR</span>
            </span>
            <span className="flex items-center gap-1 text-[9px] text-slate-400">
              <span>
                {latestLog ? `${latestLog.status.toUpperCase()} · ${latestLog.latencyMs}ms` : 'READY'}
              </span>
              {isInspectorOpen ? (
                <ChevronDown className="w-3 h-3" />
              ) : (
                <ChevronUp className="w-3 h-3" />
              )}
            </span>
          </button>

          {isInspectorOpen && latestLog && (
            <div className="mt-1 p-1.5 rounded-[2px] bg-[#06080c] border border-slate-800 max-h-[95px] overflow-y-auto space-y-1 text-[8.5px]">
              <div className="text-slate-400">
                <span className="text-emerald-400 font-semibold">POST</span> {latestLog.endpoint} ·
                Model: <span className="text-cyan-300">{latestLog.model}</span>
              </div>
              <div>
                <span className="text-slate-500 block">REQUEST PAYLOAD (JSON):</span>
                <pre className="text-slate-300 overflow-x-auto">
                  {JSON.stringify(latestLog.requestPayload, null, 2)}
                </pre>
              </div>
              <div>
                <span className="text-slate-500 block">RESPONSE PAYLOAD:</span>
                <pre className="text-emerald-300 overflow-x-auto">
                  {typeof latestLog.responsePayload === 'string'
                    ? latestLog.responsePayload
                    : JSON.stringify(latestLog.responsePayload, null, 2)}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
};
