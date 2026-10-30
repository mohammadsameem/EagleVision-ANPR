import test from 'node:test';
import assert from 'node:assert/strict';
import {
  computeCosineSimilarity,
  computeSpatioTemporalProbability,
  computeReIdScore,
  detectKinematicAnomaly,
  filterTelemetryByQuery,
  getSimulationFrameAtProgress,
  computeBoxIoU,
  extractRgbHistogramFromRgba,
  computePixelDisplacementKinematics,
  matchDetectionsToTracks,
  detectMovingBlobsFromRgbaFrame,
  analyzeVehicleCropClientOcr,
  computeCrossCameraAnprComparison,
  buildDynamicForensicReportWithAnpr,
  DEFAULT_FORENSIC_REPORT,
  getComprehensiveVehicleInventory,
} from './reidEngine.ts';

test('computeCosineSimilarity returns 1.0 for identical vectors and handles orthogonal vectors', () => {
  const vec = [0.81, 0.42, -0.19, 0.64];
  const sim = computeCosineSimilarity(vec, vec);
  assert.ok(Math.abs(sim - 1.0) < 1e-6);

  const orthoA = [1, 0, 0];
  const orthoB = [0, 1, 0];
  assert.equal(computeCosineSimilarity(orthoA, orthoB), 0);
});

test('computeSpatioTemporalProbability peaks at 1.0 when distance equals velocity * dt', () => {
  const probExact = computeSpatioTemporalProbability(2000, 20, 100, 120);
  assert.equal(probExact, 1.0);

  const probDeviated = computeSpatioTemporalProbability(2120, 20, 100, 120);
  assert.ok(Math.abs(probDeviated - Math.exp(-0.5)) < 1e-4);
});

test('computeReIdScore combines appearance cosine similarity and spatio-temporal probability with weight alpha', () => {
  const embA = [0.8, 0.6, 0.0];
  const embB = [0.8, 0.6, 0.0];
  const result = computeReIdScore(embA, embB, 1500, 15, 100, 0.72, 120);
  assert.equal(result.cosineSim, 1);
  assert.equal(result.spatioTemporalProb, 1);
  assert.equal(result.combinedScore, 1);
});

test('detectKinematicAnomaly flags sudden deceleration and erratic swerves accurately', () => {
  const decel = detectKinematicAnomaly({
    prevSpeedKmh: 82,
    currentSpeedKmh: 28,
    dtSec: 1.9,
    lateralDriftNormalized: 0.04,
  });
  assert.equal(decel.isAnomaly, true);
  assert.equal(decel.anomalyType, 'SUDDEN_DECELERATION');
  assert.ok(decel.decelerationMps2 > 7.0);

  const swerve = detectKinematicAnomaly({
    prevSpeedKmh: 70,
    currentSpeedKmh: 68,
    dtSec: 1.0,
    lateralDriftNormalized: 0.21,
  });
  assert.equal(swerve.isAnomaly, true);
  assert.equal(swerve.anomalyType, 'ERRATIC_SWERVE');
});

test('computeBoxIoU and extractRgbHistogramFromRgba compute accurate bounding box overlap and L2 RGB histograms', () => {
  const iouSame = computeBoxIoU([10, 10, 50, 40], [10, 10, 50, 40]);
  assert.equal(iouSame, 1.0);

  const iouDisjoint = computeBoxIoU([10, 10, 20, 20], [100, 100, 20, 20]);
  assert.equal(iouDisjoint, 0);

  // 2 pixels of pure silver/white RGBA
  const rgba = [200, 205, 210, 255, 200, 205, 210, 255];
  const hist = extractRgbHistogramFromRgba(rgba, 8);
  assert.equal(hist.length, 24);
  const sim = computeCosineSimilarity(hist, hist);
  assert.ok(Math.abs(sim - 1.0) < 1e-3);
});

test('computePixelDisplacementKinematics and matchDetectionsToTracks maintain persistent Track IDs and compute speed', () => {
  const kin = computePixelDisplacementKinematics({
    prevCentroid: { x: 100, y: 120 },
    currCentroid: { x: 145, y: 122 },
    prevSpeedKmh: 60,
    dtSec: 0.25,
  });
  assert.ok(kin.speedKmh > 0);

  const counter = { current: 1 };
  const hist = extractRgbHistogramFromRgba([180, 190, 200, 255, 180, 190, 200, 255], 8);
  const step1 = matchDetectionsToTracks({
    cameraId: 'cam-01',
    detections: [{ bbox: [40, 100, 60, 35], class: 'car', score: 0.92, histogram: hist }],
    existingTracks: [],
    crossCameraGallery: [],
    nowMs: 1000,
    nextIdCounter: counter,
  });
  assert.equal(step1.updatedTracks.length, 1);
  assert.equal(step1.updatedTracks[0].trackId, '1');

  const step2 = matchDetectionsToTracks({
    cameraId: 'cam-01',
    detections: [{ bbox: [55, 101, 60, 35], class: 'car', score: 0.94, histogram: hist }],
    existingTracks: step1.updatedTracks,
    crossCameraGallery: [],
    nowMs: 1200,
    nextIdCounter: counter,
  });
  assert.equal(step2.updatedTracks[0].trackId, '1');
  assert.equal(step2.updatedTracks[0].framesSeen, 2);
});

test('getSimulationFrameAtProgress and filterTelemetryByQuery work across all cameras', () => {
  const frameCam2Anomaly = getSimulationFrameAtProgress(50, true);
  assert.equal(frameCam2Anomaly.activeCameraFor8042, 'cam-02');
  const res = filterTelemetryByQuery('Silver SUV swerving on Bridge West', frameCam2Anomaly.vehicles, frameCam2Anomaly.handovers);
  assert.ok(res.matchedVehicleIds.includes('8042'));
  assert.equal(res.focusedCameraId, 'cam-02');
});

test('detectMovingBlobsFromRgbaFrame detects moving vehicle bounding boxes from RGBA video buffers', () => {
  const gridW = 120;
  const gridH = 68;
  const prevRgba = new Array(gridW * gridH * 4).fill(18);
  const currRgba = new Array(gridW * gridH * 4).fill(18);

  // Paint a bright moving vehicle blob around (x: 42..56, y: 28..38)
  for (let y = 28; y <= 38; y++) {
    for (let x = 42; x <= 56; x++) {
      const idx = (y * gridW + x) * 4;
      currRgba[idx] = 210;
      currRgba[idx + 1] = 225;
      currRgba[idx + 2] = 240;
      currRgba[idx + 3] = 255;
    }
  }

  const dets = detectMovingBlobsFromRgbaFrame({
    currRgba,
    prevRgba,
    gridW,
    gridH,
    targetWidth: 520,
    targetHeight: 235,
  });

  assert.ok(dets.length >= 1);
  assert.equal(dets[0].histogram.length, 24);
  assert.ok(dets[0].bbox[2] >= 38);
});

test('analyzeVehicleCropClientOcr, computeCrossCameraAnprComparison, and buildDynamicForensicReportWithAnpr link Car Make/Model and License Plate across CAM 01 and CAM 02', () => {
  const rgba = new Array(160 * 96 * 4).fill(185);
  const ocr = analyzeVehicleCropClientOcr({
    rgbaData: rgba,
    width: 160,
    height: 96,
    trackId: '1',
  });
  // Client OCR honestly reports what it can determine from pixel data
  assert.ok(ocr.make_model.length > 0);
  assert.ok(['UNREADABLE', 'LOW CONFIDENCE'].includes(ocr.license_plate));
  assert.ok(ocr.plate_confidence >= 0);
  assert.ok(ocr.plate_confidence <= 1);

  const hist = extractRgbHistogramFromRgba(rgba, 8);
  const cam01 = {
    cameraId: 'cam-01' as const,
    cameraLabel: '01 // Entry Camera - CAM-N4',
    trackId: '1',
    make_model: 'Silver Vehicle',
    license_plate: 'TN 09 CQ 1234',
    plate_confidence: 0.90,
    body_type: 'Hatchback',
    cropDataUrl: 'data:image/jpeg;base64,abc',
    histogram: hist,
    timestamp: '09:09:00',
    source: 'gemini-2.5-flash' as const,
  };
  const cam02 = {
    cameraId: 'cam-02' as const,
    cameraLabel: '02 // Exit / Highway Camera - CAM-W2',
    trackId: '1',
    make_model: 'Silver Vehicle',
    license_plate: 'TN 09 CQ 1234',
    plate_confidence: 0.90,
    body_type: 'Hatchback',
    cropDataUrl: 'data:image/jpeg;base64,def',
    histogram: hist,
    timestamp: '09:12:18',
    source: 'gemini-2.5-flash' as const,
  };

  const comp = computeCrossCameraAnprComparison(cam01, cam02);
  assert.equal(comp.detectedModel, 'Silver Vehicle');
  assert.equal(
    comp.anprPlateMatchText,
    'TN 09 CQ 1234 == TN 09 CQ 1234 (100% EXACT PLATE MATCH)'
  );
  assert.equal(comp.statusBadge, '✅ CONFIRMED MULTI-CAMERA RE-ID');
  // Identical histograms should produce cosine sim of 1.0
  assert.ok(comp.cosineSim >= 0.99);

  const report = buildDynamicForensicReportWithAnpr(
    DEFAULT_FORENSIC_REPORT,
    comp,
    'nvidia/Llama-3.1-Nemotron-70B-Instruct'
  );
  assert.ok(report.executiveSummary.includes('Silver Vehicle'));
  assert.ok(report.executiveSummary.includes('TN 09 CQ 1234'));
});

test('getComprehensiveVehicleInventory aggregates all detected vehicles across cameras with make, plate, and status', () => {
  const frame = getSimulationFrameAtProgress(52, true);
  const cam01 = {
    cameraId: 'cam-01' as const,
    cameraLabel: '01 // Entry',
    trackId: '8042',
    make_model: 'Silver Maruti Suzuki Swift',
    license_plate: 'TN 09 CQ 8042',
    plate_confidence: 0.97,
    body_type: 'Hatchback',
    cropDataUrl: 'data:image/jpeg;base64,123',
    histogram: [0.2, 0.2, 0.2],
    timestamp: '09:09:00',
    source: 'gemini-2.5-flash' as const,
  };
  const cam02 = { ...cam01, cameraId: 'cam-02' as const };
  const cam03 = { ...cam01, cameraId: 'cam-03' as const };

  const inventory = getComprehensiveVehicleInventory(frame.vehicles, {
    'cam-01': cam01,
    'cam-02': cam02,
    'cam-03': cam03,
  }, []);

  // Dynamic inventory should include all unique vehicles from the simulation frame
  assert.ok(inventory.length >= 1);

  // Vehicle 8042 exists in simulation and should be found with ANPR capture data
  const v8042 = inventory.find((v) => v.id === '8042');
  assert.ok(v8042);
  assert.equal(v8042?.makeModel, 'Silver Maruti Suzuki Swift');
  assert.equal(v8042?.licensePlate, 'TN 09 CQ 8042');
  assert.equal(v8042?.plateConfidence, 0.97);

  // Other simulation vehicles should also be included dynamically
  const uniqueIds = new Set(inventory.map((v) => v.id));
  assert.ok(uniqueIds.size === inventory.length); // no duplicates
});



