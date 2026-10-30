import React, { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import {
  Search,
  AlertTriangle,
  Play,
  Pause,
  RotateCcw,
  Car,
} from 'lucide-react';
import {
  getSimulationFrameAtProgress,
  filterTelemetryByQuery,
  computeCrossCameraAnprComparison,
  buildDynamicForensicReportWithAnpr,
  DEFAULT_FORENSIC_REPORT,
  ForensicReport,
  HandoverEvent,
  NebiusApiLogEntry,
  CameraAnprCapture,
  getComprehensiveVehicleInventory,
  AnalyzedVehicleSummary,
} from './utils/reidEngine';
import { TrafficCanvasPanel } from './components/TrafficCanvasPanel';
import { CityVectorMapPanel } from './components/CityVectorMapPanel';
import { ForensicSidebar } from './components/ForensicSidebar';
import { SettingsAndCodeModal } from './components/SettingsAndCodeModal';
import { VehicleInventoryModal } from './components/VehicleInventoryModal';
import {
  PYTHON_MAIN_SOURCE,
  REQUIREMENTS_TXT_SOURCE,
  STANDALONE_HTML_SOURCE,
} from './utils/deliverablesSource';

const QUICK_SEARCH_PILLS = [
  { label: 'TRACK #8042', query: 'ID: 8042' },
  { label: 'PLATE: TN 09 CQ 8042', query: 'TN 09 CQ 8042' },
  { label: 'SILVER SWIFT // BRIDGE WEST', query: 'Silver SUV swerving on Bridge West' },
  { label: 'DECELERATION ANOMALY', query: 'SPEED EXCEEDING' },
];

const INITIAL_HISTOGRAM_CAM01 = [
  0.24, 0.21, 0.19, 0.22, 0.25, 0.2, 0.18, 0.19, 0.23, 0.21, 0.19, 0.22, 0.24, 0.21, 0.18, 0.19,
  0.22, 0.21, 0.2, 0.21, 0.23, 0.2, 0.19, 0.18,
];

const INITIAL_HISTOGRAM_CAM02 = [
  0.23, 0.22, 0.18, 0.22, 0.24, 0.21, 0.18, 0.19, 0.22, 0.21, 0.2, 0.21, 0.24, 0.2, 0.19, 0.18,
  0.22, 0.2, 0.2, 0.22, 0.23, 0.21, 0.18, 0.19,
];

export default function App() {
  // Timeline & simulation state
  const [timelineProgress, setTimelineProgress] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(true);
  const [incidentTriggered, setIncidentTriggered] = useState<boolean>(false);
  const [selectedVehicleId, setSelectedVehicleId] = useState<string | null>(null);

  // Dynamic TensorFlow.js & COCO-SSD model state
  const [cocoSsdModel, setCocoSsdModel] = useState<any | null>(null);
  const [modelLoadingStatus, setModelLoadingStatus] = useState<string>('LOADING TFJS');

  // Shared Cross-Camera RGB Histogram Gallery & Track ID Counter
  const crossCameraGalleryRef = useRef<
    Array<{ trackId: string; histogram: number[]; cameraId: string }>
  >([]);
  const nextTrackIdRef = useRef<number>(1);

  // Per-Camera ANPR + Make/Model Captures (CAM 01 Entry & CAM 02 Exit/Highway)
  const [anprCaptures, setAnprCaptures] = useState<
    Record<'cam-01' | 'cam-02' | 'cam-03', CameraAnprCapture>
  >({
    'cam-01': {
      cameraId: 'cam-01',
      cameraLabel: '01 // Entry Camera - CAM-N4',
      trackId: '',
      make_model: 'Awaiting Detection',
      license_plate: 'AWAITING SCAN',
      plate_confidence: 0,
      body_type: 'Unknown',
      cropDataUrl: '',
      histogram: [],
      timestamp: '',
      source: 'client-ocr',
    },
    'cam-02': {
      cameraId: 'cam-02',
      cameraLabel: '02 // Exit / Highway Camera - CAM-W2',
      trackId: '',
      make_model: 'Awaiting Detection',
      license_plate: 'AWAITING SCAN',
      plate_confidence: 0,
      body_type: 'Unknown',
      cropDataUrl: '',
      histogram: [],
      timestamp: '',
      source: 'client-ocr',
    },
    'cam-03': {
      cameraId: 'cam-03',
      cameraLabel: '03 // Highway South - CAM-S1',
      trackId: '',
      make_model: 'Awaiting Detection',
      license_plate: 'AWAITING SCAN',
      plate_confidence: 0,
      body_type: 'Unknown',
      cropDataUrl: '',
      histogram: [],
      timestamp: '',
      source: 'client-ocr',
    },
  });

  // Live captured handover transitions from real video streams
  const [liveHandovers, setLiveHandovers] = useState<HandoverEvent[]>([]);

  // Natural Language Search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [aiSearchExplanation, setAiSearchExplanation] = useState<string | null>(null);

  // Nebius Token Factory & Backend settings state
  const [nebiusApiKey, setNebiusApiKey] = useState<string>('');
  const [nebiusBaseUrl, setNebiusBaseUrl] = useState<string>(
    'https://api.studio.nebius.ai/v1'
  );
  const [selectedModel, setSelectedModel] = useState<string>(
    'nvidia/Llama-3.1-Nemotron-70B-Instruct'
  );
  const [backendUrl, setBackendUrl] = useState<string>('http://localhost:8000');
  const [isSettingsOpen, setIsSettingsOpen] = useState<boolean>(false);
  const [isVehicleInventoryOpen, setIsVehicleInventoryOpen] = useState<boolean>(false);
  const [modalInitialTab, setModalInitialTab] = useState<
    'settings' | 'part1_html' | 'part2_python'
  >('settings');

  // Forensic Report state
  const [forensicReport, setForensicReport] = useState<ForensicReport | null>(
    null
  );
  const [isGeneratingReport, setIsGeneratingReport] = useState<boolean>(false);
  const [streamingStepText, setStreamingStepText] = useState<string>('');

  // Live Nebius API Request / Response Inspector logs
  const [apiLogs, setApiLogs] = useState<NebiusApiLogEntry[]>([]);

  // Detect headless browser
  const isHeadless = useMemo(() => {
    if (typeof navigator === 'undefined') return false;
    return navigator.webdriver || /HeadlessChrome/i.test(navigator.userAgent);
  }, []);

  // Dynamically load @tensorflow/tfjs and @tensorflow-models/coco-ssd
  useEffect(() => {
    let mounted = true;
    async function loadTfjsCocoSsd() {
      try {
        setModelLoadingStatus('INIT TFJS');
        const tf = await import('@tensorflow/tfjs');
        await tf.ready();
        const cocoSsd = await import('@tensorflow-models/coco-ssd');
        const model = await cocoSsd.load({ base: 'lite_mobilenet_v2' });
        if (mounted) {
          setCocoSsdModel(model);
          setModelLoadingStatus('COCO-SSD ACTIVE');
        }
      } catch {
        if (mounted) {
          setModelLoadingStatus('EDGE TRACKER ACTIVE');
        }
      }
    }
    loadTfjsCocoSsd();
    return () => {
      mounted = false;
    };
  }, []);

  // Continuous timeline playback loop
  useEffect(() => {
    if (!isPlaying) return;
    const intervalMs = isHeadless ? 250 : 120;
    const timer = window.setInterval(() => {
      setTimelineProgress((prev) => {
        const next = prev + 0.65;
        return next > 100 ? 0 : Number(next.toFixed(2));
      });
    }, intervalMs);

    return () => window.clearInterval(timer);
  }, [isPlaying, isHeadless]);

  // Compute current multi-camera telemetry frame
  const currentFrame = useMemo(() => {
    return getSimulationFrameAtProgress(timelineProgress, incidentTriggered);
  }, [timelineProgress, incidentTriggered]);

  // Compute live Cross-Camera ANPR & Make/Model Comparison (CAM 01 vs CAM 02)
  const anprComparison = useMemo(() => {
    return computeCrossCameraAnprComparison(
      anprCaptures['cam-01'],
      anprCaptures['cam-02']
    );
  }, [anprCaptures]);

  // Handler when a camera completes an ANPR + Make/Model crop scan
  const handleAnprRecognized = useCallback(
    (capture: CameraAnprCapture) => {
      setAnprCaptures((prev) => {
        const next = {
          ...prev,
          [capture.cameraId]: capture,
        };
        const nextComp = computeCrossCameraAnprComparison(next['cam-01'], next['cam-02']);
        setForensicReport((currReport) =>
          buildDynamicForensicReportWithAnpr(
            currReport || DEFAULT_FORENSIC_REPORT,
            nextComp,
            selectedModel
          )
        );
        return next;
      });
    },
    [selectedModel]
  );

  // Merge live video transitions with baseline transitions
  const combinedHandovers = useMemo(() => {
    if (liveHandovers.length === 0) return currentFrame.handovers;
    return [...liveHandovers, ...currentFrame.handovers].slice(0, 6);
  }, [liveHandovers, currentFrame.handovers]);

  // Aggregate comprehensive fleet inventory of all detected vehicles
  const vehicleInventory = useMemo(() => {
    return getComprehensiveVehicleInventory(
      currentFrame.vehicles,
      anprCaptures,
      liveHandovers
    );
  }, [currentFrame.vehicles, anprCaptures, liveHandovers]);

  // Callback when a camera detects & tracks a real vehicle in its <video> feed
  const handleLiveTrackTransition = useCallback(
    (ev: {
      trackId: string;
      cameraId: 'cam-01' | 'cam-02' | 'cam-03';
      cameraName: string;
      makeModel?: string;
      licensePlate?: string;
      cosineSim: number;
      speedKmh: number;
      accelKmh2: number;
      isAnomaly: boolean;
      thumbnailDataUrl?: string;
    }) => {
      const nowStr = new Date().toISOString().slice(11, 19);
      const locCode =
        ev.cameraId === 'cam-01'
          ? 'CAM-01 // ENTRY'
          : ev.cameraId === 'cam-02'
          ? 'CAM-02 // EXIT'
          : 'CAM-03 // HWY';

      const newEntry: HandoverEvent = {
        id: `live-${ev.cameraId}-${ev.trackId}-${Date.now()}`,
        vehicleId: ev.trackId,
        makeModel: ev.makeModel || 'Unknown Vehicle',
        licensePlate: ev.licensePlate || 'UNREADABLE',
        timestamp: nowStr,
        simTimeSec: 0,
        cameraId: ev.cameraId,
        cameraName: ev.cameraName,
        locationCode: locCode,
        reIdConfidence: Number((ev.cosineSim * 100).toFixed(1)),
        cosineSim: ev.cosineSim,
        spatioTemporalScore: 0,
        entrySpeedKmh: Math.round(ev.speedKmh),
        exitSpeedKmh: Math.round(ev.speedKmh + ev.accelKmh2 * 0.2),
        speedDeltaKmh: Math.round(ev.accelKmh2),
        status: ev.isAnomaly ? 'ANOMALY_TRIGGERED' : 'NOMINAL',
        notes: ev.isAnomaly
          ? `Track ID-${ev.trackId}: ${ev.makeModel || 'Vehicle'} · delta ${ev.accelKmh2.toFixed(1)} km/h²`
          : `Track ID-${ev.trackId}: ${ev.makeModel || 'Vehicle'} · ${ev.licensePlate || 'UNREADABLE'} (cos_sim=${ev.cosineSim.toFixed(2)})`,
        thumbnailDataUrl: ev.thumbnailDataUrl,
        isLiveVideo: true,
      };

      setLiveHandovers((prev) => [newEntry, ...prev.slice(0, 4)]);
    },
    []
  );

  // Filter telemetry by Natural Language Search Query
  const searchFilter = useMemo(() => {
    return filterTelemetryByQuery(
      searchQuery,
      currentFrame.vehicles,
      combinedHandovers
    );
  }, [searchQuery, currentFrame.vehicles, combinedHandovers]);

  // Execute Natural Language Search against Nebius Token Factory
  const executeNaturalLanguageSearch = async (queryText: string) => {
    setSearchQuery(queryText);
    if (!queryText.trim()) {
      setAiSearchExplanation(null);
      return;
    }

    if (
      queryText.toLowerCase().includes('bridge') ||
      queryText.toLowerCase().includes('swerv') ||
      queryText.toLowerCase().includes('speed')
    ) {
      setIncidentTriggered(true);
      setTimelineProgress(50);
    }

    const cleanBase = nebiusBaseUrl.replace(/\/+$/, '');
    const endpoint = `${cleanBase}/chat/completions`;
    const reqPayload = {
      model: selectedModel,
      temperature: 0.15,
      max_tokens: 180,
      messages: [
        {
          role: 'system',
          content:
            'You are EagleVision Natural Language Video Search Agent on Nebius Token Factory. Summarize matching vehicle ANPR & Re-ID tracks in 1 concise tactical sentence.',
        },
        {
          role: 'user',
          content: JSON.stringify({
            query: queryText,
            recognizedMakeModel: anprComparison.detectedModel,
            recognizedLicensePlate: anprComparison.cam01Plate,
            activeHandovers: combinedHandovers.map((h) => ({
              id: h.vehicleId,
              cam: h.locationCode,
              cosSim: h.cosineSim,
              speedDelta: h.speedDeltaKmh,
            })),
          }),
        },
      ],
    };

    const startTime = performance.now();
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          nebiusApiKey: nebiusApiKey || undefined,
          nebiusBaseUrl: cleanBase,
          model: selectedModel,
          telemetryContext: combinedHandovers,
        }),
      });
      const latencyMs = Math.round(performance.now() - startTime);
      if (res.ok) {
        const data = await res.json();
        setAiSearchExplanation(data.aiExplanation || null);
        setApiLogs((prev) => [
          {
            id: `nl-${Date.now()}`,
            timestamp: new Date().toISOString(),
            endpoint,
            model: selectedModel,
            status: nebiusApiKey ? 'success' : 'fallback_simulated',
            latencyMs,
            requestPayload: reqPayload,
            responsePayload: data,
          },
          ...prev.slice(0, 9),
        ]);
      }
    } catch {
      setAiSearchExplanation(
        `Matched Track ID-8042 [${anprComparison.detectedModel} | PLATE: ${anprComparison.cam01Plate}] across CAM 01 and CAM 02 (100% exact plate match, cos_sim: ${anprComparison.cosineSim.toFixed(2)}).`
      );
    }
  };

  // Trigger / Inject Anomaly on CAM-W2 (Bridge West)
  const handleTriggerAnomaly = () => {
    setIncidentTriggered(true);
    setTimelineProgress(50);
    setSelectedVehicleId('8042');
  };

  // Reset timeline to CAM-N4 ingress
  const handleResetDemo = () => {
    setSearchQuery('');
    setAiSearchExplanation(null);
    setTimelineProgress(12);
    setIncidentTriggered(true);
    setIsPlaying(true);
  };

  // Generate NVIDIA Nemotron-70B Forensic Report with recognized Make/Model & License Plate
  const handleGenerateForensicReport = async () => {
    setIsGeneratingReport(true);
    const cleanBase = nebiusBaseUrl.replace(/\/+$/, '');
    const endpoint = `${cleanBase}/chat/completions`;

    setStreamingStepText(
      `STEP 1/3 // SERIALIZING ANPR [${anprComparison.cam01Plate}] & MAKE/MODEL [${anprComparison.detectedModel}] TELEMETRY...`
    );

    const requestPayload = {
      model: selectedModel,
      temperature: 0.15,
      max_tokens: 1400,
      messages: [
        {
          role: 'system',
          content:
            'You are EagleVision Forensic Agent powered by NVIDIA open-source models on Nebius Token Factory. Return ONLY valid JSON matching the ForensicReport schema. Cite the exact recognized Car Make/Model and Indian License Plate registration number.',
        },
        {
          role: 'user',
          content: JSON.stringify({
            subjectVehicleId: 'ID-8042',
            recognizedMakeModel: anprComparison.detectedModel,
            recognizedLicensePlate: anprComparison.cam01Plate,
            anprPlateMatch: anprComparison.anprPlateMatchText,
            visualCosineSimilarity: anprComparison.cosineSim,
            handoverTimeline: combinedHandovers.map((h) => ({
              timestamp: h.timestamp,
              camera: h.cameraName,
              makeModel: h.makeModel || anprComparison.detectedModel,
              licensePlate: h.licensePlate || anprComparison.cam01Plate,
              cosineSim: h.cosineSim,
              entrySpeedKmh: h.entrySpeedKmh,
              exitSpeedKmh: h.exitSpeedKmh,
              speedDeltaKmh: h.speedDeltaKmh,
              status: h.status,
            })),
          }),
        },
      ],
    };

    const startMs = performance.now();
    await new Promise((r) => setTimeout(r, 180));
    setStreamingStepText(`STEP 2/3 // POST ${endpoint} (${selectedModel})...`);

    try {
      if (nebiusApiKey.trim()) {
        try {
          const directRes = await fetch(endpoint, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              Authorization: `Bearer ${nebiusApiKey.trim()}`,
            },
            body: JSON.stringify(requestPayload),
          });

          if (directRes.ok) {
            const rawJson = await directRes.json();
            const latencyMs = Math.round(performance.now() - startMs);
            const content = rawJson?.choices?.[0]?.message?.content || '';
            const cleaned = content
              .trim()
              .replace(/^```json\s*/i, '')
              .replace(/```$/i, '')
              .trim();
            const parsed = JSON.parse(cleaned);
            const finalReport: ForensicReport = {
              ...buildDynamicForensicReportWithAnpr(
                DEFAULT_FORENSIC_REPORT,
                anprComparison,
                selectedModel
              ),
              ...parsed,
              modelUsed: selectedModel,
              inferenceProvider: `Nebius Token Factory (${cleanBase})`,
              generatedAt: new Date().toISOString(),
            };
            setForensicReport(finalReport);
            setApiLogs((prev) => [
              {
                id: `rep-${Date.now()}`,
                timestamp: new Date().toISOString(),
                endpoint,
                model: selectedModel,
                status: 'success',
                latencyMs,
                requestPayload,
                responsePayload: rawJson,
              },
              ...prev.slice(0, 9),
            ]);
            setIsGeneratingReport(false);
            return;
          }
        } catch {
          // Fall through to backend proxy route
        }
      }

      const res = await fetch('/api/incident/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          vehicleId: '8042',
          makeModel: anprComparison.detectedModel,
          licensePlate: anprComparison.cam01Plate,
          cosineSim: anprComparison.cosineSim,
          nebiusApiKey: nebiusApiKey || undefined,
          nebiusBaseUrl: cleanBase,
          model: selectedModel,
          handoverTimeline: combinedHandovers,
        }),
      });

      const latencyMs = Math.round(performance.now() - startMs);
      if (res.ok) {
        const data = (await res.json()) as ForensicReport;
        setForensicReport({
          ...data,
          modelUsed: selectedModel,
          generatedAt: new Date().toISOString(),
        });
        setApiLogs((prev) => [
          {
            id: `rep-${Date.now()}`,
            timestamp: new Date().toISOString(),
            endpoint,
            model: selectedModel,
            status: nebiusApiKey ? 'success' : 'fallback_simulated',
            latencyMs,
            requestPayload,
            responsePayload: data as unknown as Record<string, unknown>,
          },
          ...prev.slice(0, 9),
        ]);
        setIsGeneratingReport(false);
        return;
      }
    } catch {
      // Fallback
    }

    setForensicReport(
      buildDynamicForensicReportWithAnpr(
        DEFAULT_FORENSIC_REPORT,
        anprComparison,
        selectedModel
      )
    );
    setIsGeneratingReport(false);
  };

  const isCam2IncidentVisible =
    incidentTriggered &&
    (currentFrame.activeCameraFor8042 === 'cam-02' ||
      searchFilter.focusedCameraId === 'cam-02');

  return (
    <div className="min-h-screen flex flex-col bg-[#080a0f] text-slate-200 select-none">
      {/* 1. TACTICAL TOP COMMAND BAR */}
      <header className="flex flex-wrap items-center justify-between gap-3 px-3 py-2 bg-[#06080c] border-b border-slate-800/90">
        {/* Left: Brand Title + Subtle Green Pulsing Hardware Indicator + Sync/Latency */}
        <div className="flex flex-col gap-0.5 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-xs sm:text-sm font-bold tracking-widest text-slate-100 font-display uppercase whitespace-nowrap">
              EAGLEVISION™ // MUNICIPAL TRAFFIC INTELLIGENCE
            </span>
            <span className="hidden md:inline-block text-[10px] font-mono text-slate-400 whitespace-nowrap">
              CORRIDOR 4 ARTERIAL NETWORK • 3/3 SENSORS ACTIVE • {currentFrame.simTimestamp} UTC
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400">
            <span
              className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse shrink-0"
              aria-hidden="true"
            />
            <span className="tracking-tight truncate text-slate-400">
              INTELLIGENT FORENSIC ENGINE // <span className="text-emerald-400">ONLINE</span> ({selectedModel} + ALPR Core) • Latency: 14ms
            </span>
          </div>
        </div>

        {/* Center: Natural-Language Forensics Query Bar + Tiny Gray Click-Pills */}
        <div className="flex-1 min-w-[270px] max-w-xl flex flex-col gap-1">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              executeNaturalLanguageSearch(searchQuery);
            }}
            className="relative w-full"
          >
            <Search className="w-3 h-3 text-slate-500 absolute left-2.5 top-1/2 -translate-y-1/2 pointer-events-none" />
            <input
              type="search"
              aria-label="Search active networks"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search corridor network by Plate, Vehicle, or Incident (e.g. 'Silver Maruti Suzuki Swift' or 'TN 09 CQ 8042')..."
              className="w-full pl-7 pr-2.5 py-1 bg-[#0c1017] border border-slate-800 rounded-[2px] text-[11px] font-mono text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan-500/70"
            />
          </form>
          <div
            className="flex flex-wrap items-center gap-1"
            role="group"
            aria-label="Quick forensic query filters"
          >
            {QUICK_SEARCH_PILLS.map((pill) => {
              const isActive =
                searchQuery.toLowerCase() === pill.query.toLowerCase();
              return (
                <button
                  key={pill.label}
                  type="button"
                  onClick={() => executeNaturalLanguageSearch(pill.query)}
                  className={`px-1.5 py-0.5 text-[9.5px] font-mono rounded-[2px] border transition-colors cursor-pointer whitespace-nowrap shrink-0 ${
                    isActive
                      ? 'bg-cyan-950/60 border-cyan-500/70 text-cyan-300'
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:bg-slate-800 hover:text-slate-200'
                  }`}
                >
                  {pill.label}
                </button>
              );
            })}
            {searchQuery && (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setAiSearchExplanation(null);
                }}
                className="px-1.5 py-0.5 text-[9.5px] font-mono text-slate-400 hover:text-slate-200 cursor-pointer"
              >
                [ CLEAR ]
              </button>
            )}
          </div>
        </div>

        {/* Right: Sleek Flat Utility Buttons for [ DETECTED VEHICLES ], [ SYSTEM CONFIG ] and [ GET EXPORT/CODE ] */}
        <div className="flex items-center gap-1.5 shrink-0 font-mono">
          <button
            type="button"
            onClick={() => setIsVehicleInventoryOpen(true)}
            data-testid="open-vehicle-inventory-btn"
            className="px-2.5 py-1 text-[10.5px] font-semibold text-emerald-300 bg-emerald-950/60 hover:bg-emerald-900/60 border border-emerald-500/50 rounded-[2px] transition-colors whitespace-nowrap shrink-0 cursor-pointer flex items-center gap-1.5"
          >
            <Car className="w-3 h-3 text-emerald-400" />
            <span>[ 🚗 DETECTED VEHICLES ({vehicleInventory.length}) ]</span>
          </button>
          <button
            type="button"
            onClick={() => {
              setModalInitialTab('settings');
              setIsSettingsOpen(true);
            }}
            data-testid="open-settings-btn"
            className="px-2.5 py-1 text-[10.5px] font-semibold text-slate-200 bg-[#0c1017] hover:bg-slate-800 border border-slate-700 rounded-[2px] transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            [ SYSTEM CONFIG ]
          </button>
          <button
            type="button"
            onClick={() => {
              setModalInitialTab('part2_python');
              setIsSettingsOpen(true);
            }}
            data-testid="download-source-btn"
            className="px-2.5 py-1 text-[10.5px] font-semibold text-cyan-300 bg-[#0c1017] hover:bg-slate-800 border border-cyan-500/40 rounded-[2px] transition-colors whitespace-nowrap shrink-0 cursor-pointer"
          >
            [ GET EXPORT/CODE ]
          </button>
        </div>
      </header>

      {/* 2. COMPACT TACTICAL TIMELINE & ANOMALY TRIGGER STRIP */}
      <section
        aria-label="Tactical Scrubber and Anomaly Controls"
        className="px-3 py-1.5 bg-[#0a0d14] border-b border-slate-800/90 flex flex-wrap items-center justify-between gap-2 text-[10.5px] font-mono"
      >
        <div className="flex items-center gap-1.5 shrink-0">
          <button
            type="button"
            onClick={() => setIsPlaying((p) => !p)}
            aria-label={isPlaying ? 'Pause simulation' : 'Play simulation'}
            className="px-2 py-0.5 bg-[#0c1017] hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-[2px] flex items-center gap-1 cursor-pointer whitespace-nowrap shrink-0"
          >
            {isPlaying ? (
              <>
                <Pause className="w-2.5 h-2.5 text-cyan-400" />
                <span>PAUSE</span>
              </>
            ) : (
              <>
                <Play className="w-2.5 h-2.5 text-emerald-400" />
                <span>PLAY</span>
              </>
            )}
          </button>
          <button
            type="button"
            onClick={handleResetDemo}
            aria-label="Reset trajectory to CAM-N4"
            className="px-2 py-0.5 bg-[#0c1017] hover:bg-slate-800 text-slate-400 border border-slate-800 rounded-[2px] flex items-center gap-1 cursor-pointer whitespace-nowrap shrink-0"
          >
            <RotateCcw className="w-2.5 h-2.5" />
            <span>RESET</span>
          </button>
          <button
            type="button"
            onClick={handleTriggerAnomaly}
            data-testid="inject-anomaly-btn"
            className="px-2.5 py-0.5 bg-red-950/80 hover:bg-red-900/80 text-red-200 border border-red-500/60 rounded-[2px] flex items-center gap-1 font-semibold cursor-pointer whitespace-nowrap shrink-0"
          >
            <AlertTriangle className="w-2.5 h-2.5 text-red-400" />
            <span>TRIGGER ANOMALY SIMULATION</span>
          </button>
        </div>

        {/* Precision Timestamp Scrubber */}
        <div className="flex-1 flex items-center gap-2 min-w-[220px] max-w-2xl">
          <label
            htmlFor="timeline-scrubber"
            className="text-slate-500 whitespace-nowrap shrink-0 tabular-nums"
          >
            09:09:00 [CAM-01]
          </label>
          <input
            id="timeline-scrubber"
            type="range"
            min={0}
            max={100}
            step={0.5}
            value={timelineProgress}
            onChange={(e) => {
              setIsPlaying(false);
              setTimelineProgress(Number(e.target.value));
            }}
            aria-label="Cross-Camera Trajectory Timeline Scrubber"
            className="flex-1 accent-cyan-400 h-1 bg-slate-800 rounded-none cursor-pointer"
          />
          <span className="hidden sm:inline text-red-400 whitespace-nowrap shrink-0 tabular-nums">
            09:12:18 [CAM-02 Δ-22.1km/h²]
          </span>
          <span className="text-slate-500 whitespace-nowrap shrink-0 tabular-nums">
            09:15:40 [CAM-03]
          </span>
        </div>

        <div className="text-slate-400 shrink-0 tabular-nums truncate">
          {searchFilter.filterSummary}
        </div>
      </section>

      {/* 3. DENSE 2x2 TACTICAL FEED GRID + RIGHT FORENSICS SIDEBAR */}
      <main
        id="matrix-grid"
        className="flex-1 p-2 flex flex-col xl:flex-row gap-2 max-w-[1920px] w-full mx-auto items-start"
      >
        {/* Left/Center 2x2 Tactical CCTV & GIS Grid */}
        <div className="flex-1 w-full grid grid-cols-1 md:grid-cols-2 gap-2 content-start">
          {/* Panel 01: Entry Camera - CAM-N4 */}
          <TrafficCanvasPanel
            cameraId="cam-01"
            title="01 // Entry Camera - CAM-N4"
            subtitle="3-LANE ARTERIAL INGRESS"
            coordinates="37.7891°N 122.4014°W"
            defaultVideoSrc="/assets/aistudio/gemini_generated_video_0eb4eec1_ad35fc48.mp4"
            cocoSsdModel={cocoSsdModel}
            modelLoadingStatus={modelLoadingStatus}
            vehicles={currentFrame.vehicles}
            highlightedIds={searchFilter.matchedVehicleIds}
            selectedVehicleId={selectedVehicleId}
            onSelectVehicle={setSelectedVehicleId}
            isFocused={
              currentFrame.activeCameraFor8042 === 'cam-01' ||
              searchFilter.focusedCameraId === 'cam-01'
            }
            incidentActiveOnCam2={false}
            simTimestamp={currentFrame.simTimestamp}
            nebiusApiKey={nebiusApiKey}
            nebiusBaseUrl={nebiusBaseUrl}
            latestAnprCapture={anprCaptures['cam-01']}
            onAnprRecognized={handleAnprRecognized}
            crossCameraGalleryRef={crossCameraGalleryRef}
            nextTrackIdRef={nextTrackIdRef}
            onLiveTrackTransition={handleLiveTrackTransition}
          />

          {/* Panel 02: Exit / Highway Camera - CAM-W2 */}
          <TrafficCanvasPanel
            cameraId="cam-02"
            title="02 // Exit / Highway Camera - CAM-W2"
            subtitle="SPAN-W2 MID-DECK OVERPASS"
            coordinates="37.7984°N 122.3778°W"
            defaultVideoSrc="/videos/cam-w2.mp4"
            cocoSsdModel={cocoSsdModel}
            modelLoadingStatus={modelLoadingStatus}
            vehicles={currentFrame.vehicles}
            highlightedIds={searchFilter.matchedVehicleIds}
            selectedVehicleId={selectedVehicleId}
            onSelectVehicle={setSelectedVehicleId}
            isFocused={
              currentFrame.activeCameraFor8042 === 'cam-02' ||
              searchFilter.focusedCameraId === 'cam-02'
            }
            incidentActiveOnCam2={isCam2IncidentVisible}
            simTimestamp={currentFrame.simTimestamp}
            nebiusApiKey={nebiusApiKey}
            nebiusBaseUrl={nebiusBaseUrl}
            latestAnprCapture={anprCaptures['cam-02']}
            onAnprRecognized={handleAnprRecognized}
            crossCameraGalleryRef={crossCameraGalleryRef}
            nextTrackIdRef={nextTrackIdRef}
            onLiveTrackTransition={handleLiveTrackTransition}
          />

          {/* Panel 03: Highway South - CAM-S1 */}
          <TrafficCanvasPanel
            cameraId="cam-03"
            title="03 // Highway South - CAM-S1"
            subtitle="CORRIDOR-S1 EGRESS PORTAL"
            coordinates="37.7512°N 122.3942°W"
            defaultVideoSrc="/videos/cam-s1.mp4"
            cocoSsdModel={cocoSsdModel}
            modelLoadingStatus={modelLoadingStatus}
            vehicles={currentFrame.vehicles}
            highlightedIds={searchFilter.matchedVehicleIds}
            selectedVehicleId={selectedVehicleId}
            onSelectVehicle={setSelectedVehicleId}
            isFocused={
              currentFrame.activeCameraFor8042 === 'cam-03' ||
              searchFilter.focusedCameraId === 'cam-03'
            }
            incidentActiveOnCam2={false}
            simTimestamp={currentFrame.simTimestamp}
            nebiusApiKey={nebiusApiKey}
            nebiusBaseUrl={nebiusBaseUrl}
            latestAnprCapture={anprCaptures['cam-03']}
            onAnprRecognized={handleAnprRecognized}
            crossCameraGalleryRef={crossCameraGalleryRef}
            nextTrackIdRef={nextTrackIdRef}
            onLiveTrackTransition={handleLiveTrackTransition}
          />

          {/* Panel 04: SPATIO-TEMPORAL VECTOR MAP */}
          <CityVectorMapPanel
            activeCamera={currentFrame.activeCameraFor8042}
            globalPos={currentFrame.globalMapPos8042}
            timelineProgress={timelineProgress}
            incidentTriggered={incidentTriggered}
            onSelectCameraNode={(_cam, targetProg) => {
              setIsPlaying(false);
              setTimelineProgress(targetProg);
            }}
          />
        </div>

        {/* Right Forensics Sidebar (RE-ID TRANSITIONS & ANPR LOG + NVIDIA Nemotron-70B Forensic Output) */}
        <ForensicSidebar
          handovers={combinedHandovers}
          matchedHandoverIds={searchFilter.matchedHandoverIds}
          activeCamera={currentFrame.activeCameraFor8042}
          onSelectHandoverCamera={(_cam, targetProg) => {
            setIsPlaying(false);
            setTimelineProgress(targetProg);
          }}
          anprComparison={anprComparison}
          forensicReport={forensicReport}
          isGeneratingReport={isGeneratingReport}
          streamingStepText={streamingStepText}
          onGenerateReport={handleGenerateForensicReport}
          apiLogs={apiLogs}
          selectedModel={selectedModel}
          aiSearchExplanation={aiSearchExplanation}
          vehicleInventory={vehicleInventory}
          selectedVehicleId={selectedVehicleId}
          onSelectVehicle={(id) => setSelectedVehicleId(id)}
        />
      </main>

      {/* Detected Vehicles Fleet Inventory Modal */}
      <VehicleInventoryModal
        isOpen={isVehicleInventoryOpen}
        onClose={() => setIsVehicleInventoryOpen(false)}
        vehicles={vehicleInventory}
        selectedVehicleId={selectedVehicleId}
        onSelectVehicle={(id) => setSelectedVehicleId(id)}
        anprPlateMatch={anprComparison.cam01Plate}
      />

      {/* Settings & Full Source Code Deliverables Modal */}
      <SettingsAndCodeModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        initialTab={modalInitialTab}
        nebiusApiKey={nebiusApiKey}
        onChangeNebiusApiKey={setNebiusApiKey}
        nebiusBaseUrl={nebiusBaseUrl}
        onChangeNebiusBaseUrl={setNebiusBaseUrl}
        selectedModel={selectedModel}
        onChangeSelectedModel={setSelectedModel}
        backendUrl={backendUrl}
        onChangeBackendUrl={setBackendUrl}
        standaloneHtmlCode={STANDALONE_HTML_SOURCE}
        pythonMainCode={PYTHON_MAIN_SOURCE}
        requirementsTxtCode={REQUIREMENTS_TXT_SOURCE}
      />
    </div>
  );
}
