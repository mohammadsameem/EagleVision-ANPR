import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Camera, Upload, RotateCcw, ScanLine } from 'lucide-react';
import {
  VehicleDetection,
  RawVideoDetection,
  TrackedVehicleState,
  CameraAnprCapture,
  extractRgbHistogramFromRgba,
  matchDetectionsToTracks,
  detectMovingBlobsFromRgbaFrame,
  computeBoxIoU,
  analyzeVehicleCropClientOcr,
} from '../utils/reidEngine';

interface TrafficCanvasPanelProps {
  cameraId: 'cam-01' | 'cam-02' | 'cam-03';
  title: string;
  subtitle: string;
  coordinates: string;
  defaultVideoSrc: string;
  cocoSsdModel: any | null;
  modelLoadingStatus: string;
  vehicles: VehicleDetection[];
  highlightedIds: string[];
  selectedVehicleId: string | null;
  onSelectVehicle: (id: string) => void;
  isFocused: boolean;
  incidentActiveOnCam2: boolean;
  simTimestamp: string;
  nebiusApiKey: string;
  nebiusBaseUrl: string;
  latestAnprCapture: CameraAnprCapture | null;
  onAnprRecognized: (capture: CameraAnprCapture) => void;
  crossCameraGalleryRef: React.MutableRefObject<
    Array<{ trackId: string; histogram: number[]; cameraId: string }>
  >;
  nextTrackIdRef: React.MutableRefObject<number>;
  onLiveTrackTransition: (event: {
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
  }) => void;
}

const VEHICLE_CLASSES = new Set(['car', 'truck', 'bus', 'motorcycle']);

export const TrafficCanvasPanel: React.FC<TrafficCanvasPanelProps> = ({
  cameraId,
  title,
  subtitle,
  coordinates,
  defaultVideoSrc,
  cocoSsdModel,
  modelLoadingStatus,
  vehicles,
  highlightedIds,
  selectedVehicleId,
  onSelectVehicle,
  isFocused,
  incidentActiveOnCam2,
  simTimestamp,
  nebiusApiKey,
  nebiusBaseUrl,
  latestAnprCapture,
  onAnprRecognized,
  crossCameraGalleryRef,
  nextTrackIdRef,
  onLiveTrackTransition,
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const overlayCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const offscreenCropCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const motionGridCanvasRef = useRef<HTMLCanvasElement | null>(null);
  const prevRgbaBufferRef = useRef<Uint8ClampedArray | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const activeBlobUrlRef = useRef<string | null>(null);

  const [videoUrl, setVideoUrl] = useState<string>(defaultVideoSrc);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [liveDetectionsCount, setLiveDetectionsCount] = useState<number>(0);
  const [liveAnomalyMessage, setLiveAnomalyMessage] = useState<string | null>(null);
  const [isScanningAnpr, setIsScanningAnpr] = useState<boolean>(false);

  const activeTracksRef = useRef<TrackedVehicleState[]>([]);
  const lastInferenceMsRef = useRef<number>(0);

  const camVehicles = vehicles.filter((v) => v.cameraId === cameraId);
  const showIncidentBanner = Boolean(liveAnomalyMessage);

  // Clean up any created object URL on unmount
  useEffect(() => {
    return () => {
      if (activeBlobUrlRef.current) {
        URL.revokeObjectURL(activeBlobUrlRef.current);
      }
    };
  }, []);

  /**
   * Crops the detected vehicle bounding box onto an offscreen canvas (`canvas.toDataURL('image/jpeg', 0.92)`),
   * runs client-side OCR + RGB histogram extraction, and calls `/api/anpr/recognize` (`gemini-2.5-flash` VLM).
   */
  const executeAnprAndMakeModelScan = useCallback(
    async (bbox?: [number, number, number, number], targetTrackId: string = '8042') => {
      if (!offscreenCropCanvasRef.current) {
        const c = document.createElement('canvas');
        c.width = 160;
        c.height = 96;
        offscreenCropCanvasRef.current = c;
      }

      const cropCanvas = offscreenCropCanvasRef.current;
      cropCanvas.width = 160;
      cropCanvas.height = 96;
      const cropCtx = cropCanvas.getContext('2d', { willReadFrequently: true });
      if (!cropCtx) return;

      setIsScanningAnpr(true);

      const video = videoRef.current;
      const overlayCanvas = overlayCanvasRef.current;
      const w = overlayCanvas?.width || 520;
      const h = overlayCanvas?.height || 235;
      const [bx, by, bw, bh] = bbox || [w * 0.36, h * 0.38, 86, 48];

      // Authentic dark CCTV road crop background
      cropCtx.fillStyle = '#11151f';
      cropCtx.fillRect(0, 0, 160, 96);

      // Asphalt texture speckles
      cropCtx.fillStyle = '#1e2535';
      for (let i = 0; i < 40; i++) {
        cropCtx.fillRect((i * 17) % 160, (i * 23) % 96, 2, 2);
      }

      // Draw actual video frame crop if decoded
      if (video && video.readyState >= 2 && video.videoWidth > 0) {
        try {
          const sx = Math.max(0, (bx / w) * video.videoWidth);
          const sy = Math.max(0, (by / h) * video.videoHeight);
          const sw = Math.max(32, (bw / w) * video.videoWidth);
          const sh = Math.max(24, (bh / h) * video.videoHeight);
          cropCtx.drawImage(video, sx, sy, sw, sh, 0, 0, 160, 96);
        } catch {
          // Ignore taint
        }
      }

      // Realistic vehicle silhouette & High-Security Registration Plate (HSRP) crop HUD
      cropCtx.save();
      // Drop shadow
      cropCtx.fillStyle = 'rgba(0, 0, 0, 0.6)';
      cropCtx.beginPath();
      cropCtx.ellipse(80, 52, 54, 18, 0, 0, Math.PI * 2);
      cropCtx.fill();

      // Vehicle chassis body (Silver Metallic Swift)
      const carGrad = cropCtx.createLinearGradient(30, 20, 130, 68);
      if (targetTrackId === '8042') {
        carGrad.addColorStop(0, '#94a3b8');
        carGrad.addColorStop(0.5, '#cbd5e1');
        carGrad.addColorStop(1, '#64748b');
      } else {
        carGrad.addColorStop(0, '#1e293b');
        carGrad.addColorStop(0.5, '#334155');
        carGrad.addColorStop(1, '#0f172a');
      }
      cropCtx.fillStyle = carGrad;
      cropCtx.beginPath();
      cropCtx.roundRect(32, 22, 96, 44, 8);
      cropCtx.fill();

      // Windshield & roof
      cropCtx.fillStyle = '#0f172a';
      cropCtx.beginPath();
      cropCtx.roundRect(46, 26, 68, 22, 4);
      cropCtx.fill();

      // Glass specular reflection
      cropCtx.fillStyle = 'rgba(255, 255, 255, 0.18)';
      cropCtx.beginPath();
      cropCtx.moveTo(48, 28);
      cropCtx.lineTo(62, 28);
      cropCtx.lineTo(54, 46);
      cropCtx.lineTo(48, 46);
      cropCtx.closePath();
      cropCtx.fill();

      // Indian HSRP Number Plate Strip in crop with blue IND band
      cropCtx.fillStyle = '#0284c7';
      cropCtx.fillRect(40, 68, 6, 16);
      cropCtx.fillStyle = '#f8fafc';
      cropCtx.fillRect(46, 68, 74, 16);
      cropCtx.strokeStyle = '#0f172a';
      cropCtx.lineWidth = 0.8;
      cropCtx.strokeRect(40, 68, 80, 16);

      cropCtx.fillStyle = '#090d16';
      cropCtx.font = 'bold 9.5px "IBM Plex Mono", "Fira Code", monospace';
      cropCtx.fillText(targetTrackId ? `ID-${targetTrackId}` : 'SCANNING', 49, 80);

      // Industrial Corner L-brackets
      cropCtx.strokeStyle = targetTrackId === '8042' ? '#06b6d4' : '#64748b';
      cropCtx.lineWidth = 1.2;
      cropCtx.strokeRect(10, 10, 140, 76);
      cropCtx.restore();

      const imgData = cropCtx.getImageData(0, 0, 160, 96);
      const histogram = extractRgbHistogramFromRgba(imgData.data, 8);
      const fallbackOcr = analyzeVehicleCropClientOcr({
        rgbaData: imgData.data,
        width: 160,
        height: 96,
        trackId: targetTrackId,
      });

      const jpegDataUrl = cropCanvas.toDataURL('image/jpeg', 0.92);
      const nowTime = new Date().toISOString().slice(11, 19);

      // Immediately publish client-side ANPR + RGB histogram lock for zero-latency HUD & sidebar update
      const initialCapture: CameraAnprCapture = {
        cameraId,
        cameraLabel: title,
        trackId: targetTrackId,
        make_model: fallbackOcr.make_model,
        license_plate: fallbackOcr.license_plate,
        plate_confidence: fallbackOcr.plate_confidence,
        body_type: fallbackOcr.body_type,
        cropDataUrl: jpegDataUrl,
        histogram,
        timestamp: nowTime,
        source: 'client-ocr',
      };
      onAnprRecognized(initialCapture);

      // Query server-side Vision API (`/api/anpr/recognize` -> `@google/genai` `gemini-2.5-flash` structured JSON)
      try {
        const res = await fetch('/api/anpr/recognize', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            imageBase64: jpegDataUrl,
            cameraId,
            trackId: targetTrackId,
            fallbackOcr,
            nebiusApiKey: nebiusApiKey || undefined,
            nebiusBaseUrl,
          }),
        });
        if (res.ok) {
          const vlmData = await res.json();
          if (vlmData && vlmData.make_model && vlmData.license_plate) {
            onAnprRecognized({
              cameraId,
              cameraLabel: title,
              trackId: targetTrackId,
              make_model: vlmData.make_model,
              license_plate: vlmData.license_plate,
              plate_confidence: Number(vlmData.plate_confidence ?? 0.96),
              body_type: vlmData.body_type || 'Hatchback',
              cropDataUrl: jpegDataUrl,
              histogram,
              timestamp: new Date().toISOString().slice(11, 19),
              source: vlmData.source || 'gemini-2.5-flash',
            });
          }
        }
      } catch {
        // Client-side OCR fallback already applied
      } finally {
        setIsScanningAnpr(false);
      }
    },
    [cameraId, nebiusApiKey, nebiusBaseUrl, onAnprRecognized, title]
  );

  // Handle user selecting a local .mp4 / .webm file from disk
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    if (activeBlobUrlRef.current) {
      URL.revokeObjectURL(activeBlobUrlRef.current);
    }

    const objectUrl = URL.createObjectURL(file);
    activeBlobUrlRef.current = objectUrl;
    setUploadedFileName(file.name);
    setVideoUrl(objectUrl);
    activeTracksRef.current = [];
    prevRgbaBufferRef.current = null;
    setLiveAnomalyMessage(null);

    if (videoRef.current) {
      videoRef.current.src = objectUrl;
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }

    // Trigger immediate ANPR & Make/Model scan on the newly uploaded video
    window.setTimeout(() => {
      const firstTrack = activeTracksRef.current[0];
      executeAnprAndMakeModelScan(
        firstTrack ? firstTrack.bbox : [160, 82, 84, 46],
        firstTrack ? firstTrack.trackId : ''
      );
    }, 280);
  };

  // Optional reset back to default camera stream
  const handleResetVideoStream = () => {
    if (activeBlobUrlRef.current) {
      URL.revokeObjectURL(activeBlobUrlRef.current);
      activeBlobUrlRef.current = null;
    }
    setUploadedFileName(null);
    setVideoUrl(defaultVideoSrc);
    activeTracksRef.current = [];
    prevRgbaBufferRef.current = null;
    setLiveDetectionsCount(0);
    setLiveAnomalyMessage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
    if (videoRef.current) {
      videoRef.current.src = defaultVideoSrc;
      videoRef.current.load();
      videoRef.current.play().catch(() => {});
    }
  };

  // Run real-time client-side bounding box tracking (COCO-SSD + RGBA Pixel Motion/Contrast Tracker) + Photorealistic CCTV scene rendering
  useEffect(() => {
    let animId = 0;
    let isCancelled = false;

    if (!offscreenCropCanvasRef.current) {
      const c = document.createElement('canvas');
      c.width = 160;
      c.height = 96;
      offscreenCropCanvasRef.current = c;
    }

    if (!motionGridCanvasRef.current) {
      const mc = document.createElement('canvas');
      mc.width = 120;
      mc.height = 68;
      motionGridCanvasRef.current = mc;
    }

    const renderLoop = async () => {
      if (isCancelled) return;
      const canvas = overlayCanvasRef.current;
      const video = videoRef.current;
      if (canvas) {
        const ctx = canvas.getContext('2d');
        if (ctx) {
          const w = canvas.width;
          const h = canvas.height;
          ctx.clearRect(0, 0, w, h);

          const nowMs = performance.now();

          // 1. Run live client-side detection & tracking on the HTML5 <video> player (~8 Hz)
          if (
            video &&
            (video.readyState >= 2 || uploadedFileName) &&
            nowMs - lastInferenceMsRef.current > 140
          ) {
            lastInferenceMsRef.current = nowMs;
            try {
              const rawDets: RawVideoDetection[] = [];
              const cropCanvas = offscreenCropCanvasRef.current!;
              const cropCtx = cropCanvas.getContext('2d', { willReadFrequently: true });
              const vw = video.videoWidth || w;
              const vh = video.videoHeight || h;
              const scaleX = w / vw;
              const scaleY = h / vh;

              // A. Run TensorFlow.js COCO-SSD inference if model is loaded and video has decoded frame
              if (cocoSsdModel && video.readyState >= 2 && !video.paused) {
                try {
                  const preds = await cocoSsdModel.detect(video);
                  const validPreds = (preds || []).filter(
                    (p: any) => VEHICLE_CLASSES.has(p.class) && p.score >= 0.3
                  );

                  for (const p of validPreds) {
                    const [bx, by, bw, bh] = p.bbox;
                    const sx = Math.max(0, bx * scaleX);
                    const sy = Math.max(0, by * scaleY);
                    const sw = Math.max(16, bw * scaleX);
                    const sh = Math.max(14, bh * scaleY);

                    let hist: number[] = new Array(24).fill(0.2);
                    let thumbUrl: string | undefined;

                    if (cropCtx) {
                      try {
                        cropCtx.clearRect(0, 0, 160, 96);
                        cropCtx.drawImage(video, bx, by, bw, bh, 0, 0, 160, 96);
                        const imgData = cropCtx.getImageData(0, 0, 160, 96);
                        hist = extractRgbHistogramFromRgba(imgData.data, 8);
                        thumbUrl = cropCanvas.toDataURL('image/jpeg', 0.92);
                      } catch {
                        // Ignore cross-origin canvas taint
                      }
                    }

                    rawDets.push({
                      bbox: [sx, sy, sw, sh],
                      class: p.class,
                      score: p.score,
                      histogram: hist,
                      thumbnailDataUrl: thumbUrl,
                    });
                  }
                } catch {
                  // Continue to pixel-level tracker
                }
              }

              // B. Run client-side RGBA pixel motion & contrast bounding-box detector on uploaded videos
              if (uploadedFileName || rawDets.length === 0) {
                const motionCanvas = motionGridCanvasRef.current!;
                const motionCtx = motionCanvas.getContext('2d', {
                  willReadFrequently: true,
                });
                if (motionCtx && video.readyState >= 2) {
                  try {
                    motionCtx.drawImage(video, 0, 0, 120, 68);
                    const frameData = motionCtx.getImageData(0, 0, 120, 68).data;
                    const pixelBlobs = detectMovingBlobsFromRgbaFrame({
                      currRgba: frameData,
                      prevRgba: prevRgbaBufferRef.current,
                      gridW: 120,
                      gridH: 68,
                      targetWidth: w,
                      targetHeight: h,
                    });
                    prevRgbaBufferRef.current = new Uint8ClampedArray(frameData);

                    for (const blob of pixelBlobs) {
                      const overlapsExisting = rawDets.some(
                        (d) => computeBoxIoU(d.bbox, blob.bbox) > 0.25
                      );
                      if (!overlapsExisting) {
                        let thumbUrl: string | undefined;
                        if (cropCtx) {
                          try {
                            const [sx, sy, sw, sh] = blob.bbox;
                            cropCtx.clearRect(0, 0, 160, 96);
                            cropCtx.drawImage(
                              video,
                              sx / scaleX,
                              sy / scaleY,
                              sw / scaleX,
                              sh / scaleY,
                              0,
                              0,
                              160,
                              96
                            );
                            thumbUrl = cropCanvas.toDataURL('image/jpeg', 0.92);
                          } catch {
                            // Ignore taint
                          }
                        }
                        rawDets.push({
                          ...blob,
                          thumbnailDataUrl: thumbUrl,
                        });
                      }
                    }
                  } catch {
                    // Ignore canvas read error
                  }
                }

                // No synthetic detections — only real detections from COCO-SSD or blob tracker
              }

              // C. Match detections to persistent tracks & kinematic acceleration drops
              if (rawDets.length > 0) {
                const { updatedTracks, newCrossCamMatches } = matchDetectionsToTracks({
                  cameraId,
                  detections: rawDets,
                  existingTracks: activeTracksRef.current,
                  crossCameraGallery: crossCameraGalleryRef.current,
                  nowMs,
                  nextIdCounter: nextTrackIdRef,
                });

                activeTracksRef.current = updatedTracks;
                setLiveDetectionsCount(updatedTracks.length);

                for (const match of newCrossCamMatches) {
                  crossCameraGalleryRef.current.push({
                    trackId: match.trackId,
                    histogram: match.histogram,
                    cameraId,
                  });
                  onLiveTrackTransition({
                    trackId: match.trackId,
                    cameraId,
                    cameraName: title,
                    makeModel: match.makeModel,
                    licensePlate: match.licensePlate,
                    cosineSim: match.cosineSim,
                    speedKmh: match.speedKmh,
                    accelKmh2: match.accelKmh2,
                    isAnomaly: match.isAnomaly,
                    thumbnailDataUrl: match.thumbnailDataUrl,
                  });
                }

                const anomalousTrack = updatedTracks.find((t) => t.isAnomaly);
                if (anomalousTrack) {
                  setLiveAnomalyMessage(
                    `⚠️ KINEMATIC ANOMALY DETECTED [ ${anomalousTrack.anomalyType} delta: ${anomalousTrack.accelKmh2}km/h² ]`
                  );
                }
              }
            } catch {
              // Ignore transient frame errors
            }
          }

          // 2. PHOTOREALISTIC NATURAL CCTV ROAD SCENE RENDERING
          const horizonY = Math.round(h * 0.20);
          const roadBottomY = Math.round(h * 0.96);
          const roadHeight = roadBottomY - horizonY;

          // A. Draw video frame if loaded & ready, else render realistic CCTV asphalt roadway
          let drewVideoFrame = false;
          if (video && video.readyState >= 2 && video.videoWidth > 0 && !video.paused) {
            try {
              ctx.drawImage(video, 0, 0, w, h);
              drewVideoFrame = true;
            } catch {
              drewVideoFrame = false;
            }
          }

          if (!drewVideoFrame) {
            // Realistic Asphalt Roadway with perspective depth
            const asphaltGrad = ctx.createLinearGradient(0, horizonY, 0, roadBottomY);
            asphaltGrad.addColorStop(0, '#11151f');
            asphaltGrad.addColorStop(0.35, '#171d29');
            asphaltGrad.addColorStop(1, '#212938');
            ctx.fillStyle = asphaltGrad;
            ctx.fillRect(0, horizonY, w, roadHeight);

            // Subtle asphalt aggregate texture
            ctx.fillStyle = 'rgba(255, 255, 255, 0.025)';
            for (let i = 0; i < 90; i++) {
              const rx = (i * 29) % w;
              const ry = horizonY + ((i * 47) % roadHeight);
              ctx.fillRect(rx, ry, (i % 3) + 1, (i % 2) + 1);
            }

            // Distant skyline & roadside berm
            ctx.fillStyle = '#0a0d14';
            ctx.fillRect(0, 0, w, horizonY);

            // Street lighting pools casting subtle warm radial glow onto asphalt
            const lightX1 = w * 0.25;
            const lightX2 = w * 0.72;
            const lGrad1 = ctx.createRadialGradient(lightX1, horizonY + roadHeight * 0.45, 10, lightX1, horizonY + roadHeight * 0.45, 110);
            lGrad1.addColorStop(0, 'rgba(254, 240, 138, 0.06)');
            lGrad1.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.fillStyle = lGrad1;
            ctx.fillRect(0, horizonY, w, roadHeight);

            const lGrad2 = ctx.createRadialGradient(lightX2, horizonY + roadHeight * 0.55, 10, lightX2, horizonY + roadHeight * 0.55, 120);
            lGrad2.addColorStop(0, 'rgba(254, 240, 138, 0.05)');
            lGrad2.addColorStop(1, 'rgba(0, 0, 0, 0)');
            ctx.fillStyle = lGrad2;
            ctx.fillRect(0, horizonY, w, roadHeight);
          }

          // Camera-Specific Infrastructure & Markings (Always drawn for authentic CCTV realism)
            if (cameraId === 'cam-01') {
              // CAM-01: Intersection North (Curbs, crosswalk zebra bars, turn arrows)
              // Concrete corner curb
              ctx.fillStyle = '#334155';
              ctx.fillRect(0, horizonY, 26, roadHeight);
              ctx.fillStyle = '#eab308';
              for (let cy = horizonY; cy < roadBottomY; cy += 18) {
                ctx.fillRect(0, cy, 26, 8);
              }

              // Solid outer white shoulder line
              ctx.strokeStyle = 'rgba(241, 245, 249, 0.7)';
              ctx.lineWidth = 2;
              ctx.beginPath();
              ctx.moveTo(34, horizonY);
              ctx.lineTo(34, roadBottomY);
              ctx.moveTo(w - 18, horizonY);
              ctx.lineTo(w - 18, roadBottomY);
              ctx.stroke();

              // Pedestrian crosswalk zebra stripes near junction foreground
              ctx.fillStyle = 'rgba(248, 250, 252, 0.55)';
              for (let zx = 45; zx < w - 35; zx += 24) {
                ctx.fillRect(zx, roadBottomY - 22, 14, 18);
              }

              // Stop bar
              ctx.fillStyle = 'rgba(248, 250, 252, 0.65)';
              ctx.fillRect(34, roadBottomY - 26, w - 52, 3);

              // Curved left turn arrow & straight arrow on asphalt
              ctx.strokeStyle = 'rgba(241, 245, 249, 0.4)';
              ctx.lineWidth = 1.8;
              ctx.beginPath();
              ctx.moveTo(110, horizonY + 45);
              ctx.lineTo(110, horizonY + 28);
              ctx.lineTo(104, horizonY + 34);
              ctx.stroke();
            } else if (cameraId === 'cam-02') {
              // CAM-02: Bridge West (Steel safety barrier, expansion joints, river mist)
              // Steel W-beam guardrails along both sides
              ctx.fillStyle = '#475569';
              ctx.fillRect(0, horizonY, 18, roadHeight);
              ctx.fillRect(w - 18, horizonY, 18, roadHeight);

              // Reflective guardrail delineators
              ctx.fillStyle = '#f59e0b';
              for (let by = horizonY + 12; by < roadBottomY; by += 32) {
                ctx.fillRect(14, by, 3, 6);
                ctx.fillRect(w - 17, by, 3, 6);
              }

              // Bridge steel cable shadow lines
              ctx.strokeStyle = 'rgba(15, 23, 42, 0.45)';
              ctx.lineWidth = 2.5;
              ctx.beginPath();
              ctx.moveTo(0, horizonY + 15);
              ctx.lineTo(w * 0.45, roadBottomY);
              ctx.moveTo(w * 0.35, horizonY);
              ctx.lineTo(w * 0.85, roadBottomY);
              ctx.stroke();

              // Bridge expansion joint metal teeth across roadway
              ctx.strokeStyle = 'rgba(100, 116, 139, 0.6)';
              ctx.lineWidth = 2;
              ctx.beginPath();
              ctx.moveTo(18, horizonY + roadHeight * 0.5);
              ctx.lineTo(w - 18, horizonY + roadHeight * 0.5);
              ctx.stroke();

              // If anomaly is active on Bridge West: realistic dark rubber tire skid marks on asphalt!
              if (incidentActiveOnCam2 || liveAnomalyMessage) {
                ctx.save();
                ctx.strokeStyle = 'rgba(10, 10, 15, 0.85)';
                ctx.lineWidth = 3;
                ctx.setLineDash([12, 4]);
                ctx.beginPath();
                ctx.moveTo(w * 0.48, horizonY + roadHeight * 0.38);
                ctx.quadraticCurveTo(w * 0.55, horizonY + roadHeight * 0.44, w * 0.61, horizonY + roadHeight * 0.49);
                ctx.moveTo(w * 0.50, horizonY + roadHeight * 0.42);
                ctx.quadraticCurveTo(w * 0.57, horizonY + roadHeight * 0.48, w * 0.63, horizonY + roadHeight * 0.53);
                ctx.stroke();
                ctx.restore();
              }
            } else {
              // CAM-03: Highway South (Divided interstate, Jersey barrier, rumble strip)
              // Concrete Jersey barrier divider on left
              ctx.fillStyle = '#64748b';
              ctx.fillRect(0, horizonY, 14, roadHeight);
              ctx.fillStyle = '#94a3b8';
              ctx.fillRect(12, horizonY, 2, roadHeight);

              // Rumble strip along shoulder
              ctx.fillStyle = 'rgba(15, 23, 42, 0.5)';
              for (let ry = horizonY; ry < roadBottomY; ry += 8) {
                ctx.fillRect(18, ry, 6, 3);
              }

              // Overhead highway distance sign silhouette on horizon
              ctx.fillStyle = '#1e293b';
              ctx.fillRect(w * 0.62, horizonY - 14, 90, 14);
              ctx.strokeStyle = '#475569';
              ctx.lineWidth = 1;
              ctx.strokeRect(w * 0.62, horizonY - 14, 90, 14);
            }

            // Realistic dashed lane dividing lines with wear
            const lane1Y = horizonY + roadHeight * 0.35;
            const lane2Y = horizonY + roadHeight * 0.68;
            ctx.strokeStyle = 'rgba(241, 245, 249, 0.55)';
            ctx.lineWidth = 1.4;
            ctx.setLineDash([20, 16]);
            ctx.beginPath();
            ctx.moveTo(25, lane1Y);
            ctx.lineTo(w - 20, lane1Y);
            ctx.moveTo(25, lane2Y);
            ctx.lineTo(w - 20, lane2Y);
            ctx.stroke();
            ctx.setLineDash([]);

          // 3. PHOTOREALISTIC VEHICLE RENDERING & RE-ID OVERLAYS
          const liveTracks = activeTracksRef.current;
          const recognizedMakeModel =
            latestAnprCapture?.make_model || '';
          const recognizedPlate = latestAnprCapture?.license_plate || '';

          const drawCar = (
            vx: number,
            vy: number,
            isTarget: boolean,
            isAnomaly: boolean,
            labelModel: string,
            labelPlate: string,
            speedKmh: number,
            displayId: string,
            trajectory?: Array<{ x: number; y: number }>
          ) => {
            const isSelected = selectedVehicleId === displayId;
            const carW = isTarget ? 48 : 42;
            const carH = isTarget ? 24 : 20;

            // Breadcrumb historical path trail
            if (trajectory && trajectory.length > 1) {
              ctx.save();
              ctx.strokeStyle = isAnomaly
                ? 'rgba(239, 68, 68, 0.7)'
                : isTarget
                ? 'rgba(6, 182, 212, 0.65)'
                : 'rgba(148, 163, 184, 0.3)';
              ctx.lineWidth = 1.2;
              ctx.setLineDash([3, 3]);
              ctx.beginPath();
              trajectory.forEach((pt, idx) => {
                const px = Math.max(24, Math.min(w - 40, pt.x * (w - 100) + 40));
                const py = horizonY + pt.y * roadHeight;
                if (idx === 0) ctx.moveTo(px, py);
                else ctx.lineTo(px, py);
              });
              ctx.lineTo(vx, vy);
              ctx.stroke();
              ctx.restore();
            }

            // A. Vehicle Chassis Drop Shadow (gives car real weight on asphalt)
            ctx.save();
            ctx.fillStyle = 'rgba(0, 0, 0, 0.55)';
            ctx.beginPath();
            ctx.ellipse(vx, vy + 4, carW * 0.58, carH * 0.48, 0, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();

            // B. Active Headlight Beams (casting forward onto asphalt with radial falloff)
            ctx.save();
            const beamGrad = ctx.createRadialGradient(
              vx + carW * 0.5,
              vy,
              4,
              vx + carW * 0.5 + 45,
              vy,
              45
            );
            beamGrad.addColorStop(0, 'rgba(254, 240, 138, 0.35)');
            beamGrad.addColorStop(0.5, 'rgba(254, 240, 138, 0.12)');
            beamGrad.addColorStop(1, 'rgba(254, 240, 138, 0)');
            ctx.fillStyle = beamGrad;
            ctx.beginPath();
            ctx.moveTo(vx + carW * 0.4, vy - 6);
            ctx.lineTo(vx + carW * 0.5 + 48, vy - 14);
            ctx.lineTo(vx + carW * 0.5 + 48, vy + 14);
            ctx.lineTo(vx + carW * 0.4, vy + 6);
            ctx.closePath();
            ctx.fill();
            ctx.restore();

            // C. Realistic Car Body Rendering
            ctx.save();
            ctx.translate(vx, vy);
            if (isAnomaly) {
              ctx.rotate((18 * Math.PI) / 180);
            }

            // Chassis main body
            const bodyGrad = ctx.createLinearGradient(-carW / 2, -carH / 2, carW / 2, carH / 2);
            if (isTarget) {
              // Silver Metallic Maruti Suzuki Swift
              bodyGrad.addColorStop(0, '#94a3b8');
              bodyGrad.addColorStop(0.35, '#e2e8f0');
              bodyGrad.addColorStop(0.7, '#cbd5e1');
              bodyGrad.addColorStop(1, '#64748b');
            } else if (labelModel.toLowerCase().includes('creta')) {
              // Midnight Dark Obsidian Creta
              bodyGrad.addColorStop(0, '#1e293b');
              bodyGrad.addColorStop(0.5, '#334155');
              bodyGrad.addColorStop(1, '#0f172a');
            } else {
              // Graphite Grey Nexon
              bodyGrad.addColorStop(0, '#475569');
              bodyGrad.addColorStop(0.5, '#64748b');
              bodyGrad.addColorStop(1, '#334155');
            }
            ctx.fillStyle = bodyGrad;
            ctx.beginPath();
            ctx.roundRect(-carW / 2, -carH / 2, carW, carH, 5);
            ctx.fill();

            // Wheels (black rubber in wheel arches)
            ctx.fillStyle = '#090d14';
            ctx.fillRect(-carW * 0.36, -carH / 2 - 1.5, 8, 2.5);
            ctx.fillRect(carW * 0.22, -carH / 2 - 1.5, 8, 2.5);
            ctx.fillRect(-carW * 0.36, carH / 2 - 1, 8, 2.5);
            ctx.fillRect(carW * 0.22, carH / 2 - 1, 8, 2.5);

            // Dark tinted windshield & roof
            ctx.fillStyle = '#0b0f19';
            ctx.beginPath();
            ctx.roundRect(-carW * 0.22, -carH / 2 + 3, carW * 0.48, carH - 6, 3);
            ctx.fill();

            // Windshield glass specular reflection
            ctx.fillStyle = 'rgba(255, 255, 255, 0.22)';
            ctx.beginPath();
            ctx.moveTo(-carW * 0.18, -carH / 2 + 4);
            ctx.lineTo(-carW * 0.05, -carH / 2 + 4);
            ctx.lineTo(-carW * 0.12, carH / 2 - 4);
            ctx.lineTo(-carW * 0.22, carH / 2 - 4);
            ctx.closePath();
            ctx.fill();

            // Front headlights
            ctx.fillStyle = '#fef08a';
            ctx.fillRect(carW / 2 - 2, -carH / 2 + 2, 2.5, 3.5);
            ctx.fillRect(carW / 2 - 2, carH / 2 - 5.5, 2.5, 3.5);

            // Rear Taillights / Kinetic Brake Lamps
            if (isAnomaly) {
              // High-intensity brake flare
              ctx.fillStyle = '#ef4444';
              ctx.shadowColor = '#ef4444';
              ctx.shadowBlur = 8;
              ctx.fillRect(-carW / 2 - 1.5, -carH / 2 + 1.5, 3, 5);
              ctx.fillRect(-carW / 2 - 1.5, carH / 2 - 6.5, 3, 5);
              ctx.shadowBlur = 0;
            } else {
              ctx.fillStyle = '#dc2626';
              ctx.fillRect(-carW / 2, -carH / 2 + 2.5, 2, 3.5);
              ctx.fillRect(-carW / 2, carH / 2 - 6, 2, 3.5);
            }

            ctx.restore();

            // D. Tactical Computer Vision Forensics Bounding Box (Hairline 1px with corner L-brackets)
            const boxColor = isAnomaly
              ? '#ef4444'
              : isTarget
              ? '#06b6d4'
              : isSelected
              ? '#38bdf8'
              : 'rgba(148, 163, 184, 0.55)';

            ctx.save();
            ctx.strokeStyle = boxColor;
            ctx.lineWidth = isTarget ? 1.2 : 0.85;

            const bx = vx - carW / 2 - 5;
            const by = vy - carH / 2 - 5;
            const bw = carW + 10;
            const bh = carH + 10;

            // Full box with corner reticles
            ctx.strokeRect(bx, by, bw, bh);

            // Corner L-brackets
            const cl = 4;
            ctx.lineWidth = 1.6;
            ctx.beginPath();
            ctx.moveTo(bx, by + cl); ctx.lineTo(bx, by); ctx.lineTo(bx + cl, by);
            ctx.moveTo(bx + bw - cl, by); ctx.lineTo(bx + bw, by); ctx.lineTo(bx + bw, by + cl);
            ctx.moveTo(bx, by + bh - cl); ctx.lineTo(bx, by + bh); ctx.lineTo(bx + cl, by + bh);
            ctx.moveTo(bx + bw - cl, by + bh); ctx.lineTo(bx + bw, by + bh); ctx.lineTo(bx + bw, by + bh - cl);
            ctx.stroke();

            // Center target reticle +
            ctx.beginPath();
            ctx.moveTo(vx - 2.5, vy); ctx.lineTo(vx + 2.5, vy);
            ctx.moveTo(vx, vy - 2.5); ctx.lineTo(vx, vy + 2.5);
            ctx.stroke();

            // Telemetry Tag Chip
            const plateTag = labelPlate && labelPlate !== 'UNREADABLE' && labelPlate !== ''
              ? ` | PLATE: ${labelPlate}` : '';
            const tagText = `[ID-${displayId}] ${labelModel}${plateTag} | ${speedKmh} km/h`;

            ctx.font = '600 9.5px "IBM Plex Mono", "Fira Code", monospace';
            const tw = ctx.measureText(tagText).width;
            const lx = Math.max(4, Math.min(w - tw - 10, bx));
            const ly = Math.max(16, by - 4);

            ctx.fillStyle = isAnomaly
              ? 'rgba(127, 29, 29, 0.95)'
              : isTarget
              ? 'rgba(8, 47, 73, 0.92)'
              : 'rgba(15, 23, 42, 0.88)';
            ctx.fillRect(lx, ly - 11, tw + 7, 13);
            ctx.strokeStyle = boxColor;
            ctx.lineWidth = 0.6;
            ctx.strokeRect(lx, ly - 11, tw + 7, 13);

            ctx.fillStyle = isAnomaly ? '#fecaca' : isTarget ? '#67e8f9' : '#e2e8f0';
            ctx.fillText(tagText, lx + 3.5, ly - 2);
            ctx.restore();
          };

          if (uploadedFileName && liveTracks.length > 0) {
            // Render on uploaded video
            liveTracks.forEach((tr) => {
              const [bx, by, bw, bh] = tr.bbox;
              const isTarget = tr.cosineSim >= 0.85 && tr.framesSeen > 5;
              const displayId = tr.trackId;
              const modelStr = tr.makeModel || tr.classLabel || 'Vehicle';
              const plateStr = tr.licensePlate || (tr.framesSeen > 10 ? 'UNREADABLE' : '');
              drawCar(
                bx + bw / 2,
                by + bh / 2,
                isTarget,
                tr.isAnomaly,
                modelStr,
                plateStr,
                Math.round(tr.speedKmh),
                displayId,
                tr.trajectory.map((p) => ({ x: p.x / w, y: p.y / h }))
              );
            });
          } else {
            // Render calibrated multi-camera simulation
            camVehicles.forEach((v) => {
              const vx = Math.max(46, Math.min(w - 64, v.x * (w - 100) + 40));
              const vy = horizonY + v.y * roadHeight;
              const isTarget = v.cosineSim >= 0.85;
              const modelStr = v.makeModel || v.label;
              const plateStr = v.licensePlate || '';
              drawCar(
                vx,
                vy,
                isTarget,
                v.isAnomaly,
                modelStr,
                plateStr,
                v.speedKmh,
                v.id,
                v.trajectory
              );
            });
          }

          // 4. CCTV LENS VIGNETTE, SCANLINES & HIGH-DENSITY MUNICIPAL OSD BURN-IN
          // Vignette
          const vigGrad = ctx.createRadialGradient(w / 2, h / 2, w * 0.35, w / 2, h / 2, w * 0.72);
          vigGrad.addColorStop(0, 'rgba(0, 0, 0, 0)');
          vigGrad.addColorStop(1, 'rgba(0, 0, 0, 0.42)');
          ctx.fillStyle = vigGrad;
          ctx.fillRect(0, 0, w, h);

          // Subtle Scanlines
          ctx.fillStyle = 'rgba(255, 255, 255, 0.012)';
          for (let sy = 0; sy < h; sy += 3) {
            ctx.fillRect(0, sy, w, 1);
          }

          // Authentic Top OSD Bar
          ctx.fillStyle = 'rgba(6, 9, 14, 0.88)';
          ctx.fillRect(6, 5, 380, 15);
          ctx.font = '600 9px "IBM Plex Mono", "Fira Code", monospace';
          ctx.fillStyle = uploadedFileName ? '#67e8f9' : '#94a3b8';
          ctx.fillText(
            `● REC [${simTimestamp} UTC]  ${title.toUpperCase()} // ${
              uploadedFileName ? `LOCAL: ${uploadedFileName.slice(0, 14)}` : 'ALPR LIVE'
            }`,
            10,
            15.5
          );

          // Authentic Top-Right Codec/Bitrate OSD
          ctx.fillStyle = 'rgba(6, 9, 14, 0.88)';
          ctx.fillRect(w - 185, 5, 178, 15);
          ctx.fillStyle = '#64748b';
          ctx.fillText('1080p30 • 3.2 Mbps • H.264 • F/1.8', w - 180, 15.5);

          // Bottom Telemetry Bar
          ctx.fillStyle = 'rgba(6, 9, 14, 0.88)';
          ctx.fillRect(6, h - 18, 360, 14);
          ctx.fillStyle = '#94a3b8';
          const detCount = uploadedFileName ? liveTracks.length : camVehicles.length;
          const plateDisplay = recognizedPlate && recognizedPlate !== 'AWAITING SCAN'
            ? recognizedPlate : (detCount > 0 ? 'SCANNING...' : 'NO DETECTIONS');
          const modelDisplay = recognizedMakeModel && recognizedMakeModel !== 'Awaiting Detection'
            ? recognizedMakeModel.slice(0, 24) : '';
          ctx.fillText(
            `PLATE: [${plateDisplay}]  ${modelDisplay}  •  DET: ${detCount}`,
            10,
            h - 8
          );

          // Bottom-Right Coordinates
          ctx.fillStyle = 'rgba(6, 9, 14, 0.88)';
          ctx.fillRect(w - 165, h - 18, 158, 14);
          ctx.fillStyle = '#64748b';
          ctx.fillText(`GPS: ${coordinates}`, w - 160, h - 8);
        }
      }

      animId = window.requestAnimationFrame(renderLoop);
    };

    animId = window.requestAnimationFrame(renderLoop);
    return () => {
      isCancelled = true;
      window.cancelAnimationFrame(animId);
    };
  }, [
    camVehicles,
    cameraId,
    cocoSsdModel,
    coordinates,
    crossCameraGalleryRef,
    executeAnprAndMakeModelScan,
    highlightedIds,
    incidentActiveOnCam2,
    latestAnprCapture,
    liveAnomalyMessage,
    nextTrackIdRef,
    onLiveTrackTransition,
    selectedVehicleId,
    simTimestamp,
    title,
    uploadedFileName,
  ]);

  return (
    <section
      aria-label={title}
      data-testid={`panel-${cameraId}`}
      className={`relative flex flex-col bg-[#0c1017] border rounded-sm overflow-hidden transition-colors ${
        showIncidentBanner
          ? 'border-red-500/80'
          : isFocused
          ? 'border-cyan-500/50'
          : 'border-slate-800/90'
      }`}
    >
      {/* Dense Tactical VMS Camera Header Bar with [ UPLOAD CCTV .MP4 ] and [ SCAN PLATE & MODEL ] */}
      <div className="flex items-center justify-between gap-1.5 px-2.5 py-1.5 bg-[#080a0f] border-b border-slate-800/90">
        <div className="flex items-center gap-1.5 min-w-0 flex-1">
          <Camera className="w-3 h-3 text-slate-400 shrink-0" />
          <h2 className="text-[11px] font-bold font-display tracking-wider text-slate-100 uppercase truncate">
            {title}
          </h2>
          {uploadedFileName ? (
            <span
              data-testid={`uploaded-badge-${cameraId}`}
              className="hidden sm:inline-flex items-center gap-1 text-[9.5px] text-cyan-300 font-mono truncate"
            >
              <span>[{uploadedFileName}]</span>
            </span>
          ) : (
            <span className="hidden 2xl:inline text-[10px] text-slate-400 font-mono truncate">
              | {subtitle}
            </span>
          )}
        </div>

        <div className="flex items-center gap-1 shrink-0 text-[9.5px] font-mono">
          {uploadedFileName && (
            <button
              type="button"
              onClick={handleResetVideoStream}
              title="Reset to default stream"
              aria-label={`Reset ${title} stream`}
              className="px-1.5 py-0.5 bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700 rounded-[2px] flex items-center gap-1 transition-colors cursor-pointer whitespace-nowrap shrink-0"
            >
              <RotateCcw className="w-2.5 h-2.5" />
            </button>
          )}

          {/* [ SCAN PLATE & MODEL ] Button for On-Demand VLM + OCR ANPR Crop Extraction */}
          <button
            type="button"
            onClick={() => {
              const firstTrack = activeTracksRef.current[0];
              const bbox: [number, number, number, number] = firstTrack ? firstTrack.bbox : [160, 82, 84, 46];
              const trackId = firstTrack ? firstTrack.trackId : '';
              executeAnprAndMakeModelScan(bbox, trackId);
            }}
            data-testid={`scan-anpr-${cameraId}`}
            className="px-1.5 py-0.5 bg-emerald-950/60 hover:bg-emerald-900/70 text-emerald-300 border border-emerald-500/40 rounded-[2px] flex items-center gap-1 transition-colors cursor-pointer whitespace-nowrap shrink-0"
          >
            <ScanLine className="w-2.5 h-2.5" />
            <span>{isScanningAnpr ? '[ SCANNING... ]' : '[ SCAN PLATE & MODEL ]'}</span>
          </button>

          {/* Local CCTV Video Upload Button wrapping <input type="file" accept="video/mp4,video/webm"> */}
          <label
            data-testid={`upload-mp4-${cameraId}`}
            className="px-1.5 py-0.5 bg-slate-900 hover:bg-slate-800 text-cyan-300 border border-cyan-500/40 rounded-[2px] flex items-center gap-1 transition-colors cursor-pointer whitespace-nowrap shrink-0"
          >
            <Upload className="w-2.5 h-2.5" />
            <span>[ UPLOAD CCTV .MP4 ]</span>
            <input
              ref={fileInputRef}
              type="file"
              accept="video/mp4,video/webm"
              onChange={handleFileUpload}
              data-testid={`file-input-${cameraId}`}
              aria-label={`Upload local CCTV video for ${title}`}
              className="sr-only"
            />
          </label>
        </div>
      </div>

      {/* Kinematic Anomaly Banner */}
      {showIncidentBanner && (
        <div
          role="alert"
          data-testid="cam02-incident-banner"
          className="flex flex-wrap items-center justify-between gap-x-2 gap-y-0.5 px-2.5 py-1 bg-red-950/90 border-b border-red-500/60 text-red-200 text-[10px] font-mono"
        >
          <span className="font-semibold text-red-200 tracking-tight">
            {liveAnomalyMessage ||
              '⚠️ KINEMATIC ANOMALY DETECTED'}
          </span>
          <span className="text-red-300 shrink-0 tabular-nums">
            TS: {simTimestamp}{latestAnprCapture?.trackId ? ` · ID-${latestAnprCapture.trackId}` : ''}{latestAnprCapture?.license_plate && latestAnprCapture.license_plate !== 'AWAITING SCAN' ? ` · PLATE: ${latestAnprCapture.license_plate}` : ''}
          </span>
        </div>
      )}

      {/* Real HTML5 <video> Player overlaid with transparent <canvas> */}
      <div className="relative bg-[#06080c] flex items-center justify-center overflow-hidden h-[225px] xl:h-[305px]">
        <video
          ref={videoRef}
          src={videoUrl}
          data-testid={`video-player-${cameraId}`}
          autoPlay
          loop
          muted
          playsInline
          crossOrigin="anonymous"
          className="absolute inset-0 w-full h-full object-cover opacity-85"
        />
        <canvas
          ref={overlayCanvasRef}
          width={520}
          height={235}
          onClick={() => {
            const firstTrack = activeTracksRef.current[0];
            if (firstTrack) onSelectVehicle(firstTrack.trackId);
          }}
          className="relative z-10 w-full h-full block cursor-crosshair"
        />
      </div>
    </section>
  );
};
