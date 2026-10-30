"""
EagleVision: Multi-Camera Vehicle Re-ID & Incident Agent
Nebius x NVIDIA Global AI Hackathon — Production FastAPI + YOLOv8 + ByteTrack Backend (main.py)
"""

import os
import math
import json
import base64
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

import numpy as np
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAI

try:
    import cv2  # type: ignore
    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    CV2_AVAILABLE = False

try:
    from ultralytics import YOLO  # type: ignore
    YOLO_AVAILABLE = True
except ImportError:
    YOLO = None
    YOLO_AVAILABLE = False


class IncidentReportRequest(BaseModel):
    vehicle_id: str = Field(default="8042")
    nebius_api_key: Optional[str] = Field(default=None)
    nebius_base_url: str = Field(default="https://api.studio.nebius.ai/v1")
    model: str = Field(default="nvidia/Llama-3.1-Nemotron-70B-Instruct")
    handover_timeline: List[Dict[str, Any]] = Field(default_factory=list)


class NaturalLanguageSearchRequest(BaseModel):
    query: str
    nebius_api_key: Optional[str] = None
    nebius_base_url: str = "https://api.studio.nebius.ai/v1"
    model: str = "nvidia/Llama-3.1-Nemotron-70B-Instruct"
    telemetry_context: List[Dict[str, Any]] = Field(default_factory=list)


class CrossCameraTracker:
    """
    Multi-camera YOLOv8 + ByteTrack + Appearance/Spatio-Temporal Vehicle Re-Identification Engine.
    Computes:
      S(v_a, v_b) = alpha * cos_sim(E_a, E_b) + (1 - alpha) * exp(-||d - v * dt||^2 / (2 * sigma^2))
    """

    def __init__(self, model_weights: str = "yolov8n.pt", alpha: float = 0.72, sigma_meters: float = 120.0):
        self.alpha = float(np.clip(alpha, 0.0, 1.0))
        self.sigma_meters = float(max(1.0, sigma_meters))
        self.model = None
        if YOLO_AVAILABLE and os.path.exists(model_weights):
            try:
                self.model = YOLO(model_weights)
            except Exception:
                self.model = None

    @staticmethod
    def compute_cosine_similarity(emb_a: np.ndarray, emb_b: np.ndarray) -> float:
        denom = float(np.linalg.norm(emb_a) * np.linalg.norm(emb_b))
        return float(np.clip(np.dot(emb_a, emb_b) / denom, -1.0, 1.0)) if denom > 0.0 else 0.0

    def compute_spatio_temporal_probability(self, distance_m: float, velocity_mps: float, dt_sec: float) -> float:
        residual = distance_m - (velocity_mps * dt_sec)
        return float(math.exp(-(residual ** 2) / (2.0 * (self.sigma_meters ** 2))))

    def extract_crop_and_histogram(self, frame_bgr: np.ndarray, bbox: List[int]) -> Dict[str, Any]:
        x1, y1, x2, y2 = [max(0, int(v)) for v in bbox]
        crop = frame_bgr[y1:max(y1 + 1, y2), x1:max(x1 + 1, x2)]
        if crop.size == 0 or not CV2_AVAILABLE:
            return {"histogram": [0.2] * 24, "base64_jpeg": None}
        hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1, 2], None, [8, 8, 8], [0, 180, 0, 256, 0, 256]).flatten()
        norm = np.linalg.norm(hist)
        norm_hist = [round(float(v / norm), 4) for v in hist[:24]] if norm > 0 else [0.0] * 24
        thumb = cv2.resize(crop, (68, 44))
        _, buf = cv2.imencode(".jpg", thumb, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
        b64 = "data:image/jpeg;base64," + base64.b64encode(buf).decode("utf-8")
        return {"histogram": norm_hist, "base64_jpeg": b64}

    def track_video_stream(self, video_path: str, camera_id: str = "cam-02") -> List[Dict[str, Any]]:
        if not self.model or not os.path.exists(video_path):
            return []
        results = self.model.track(
            source=video_path,
            tracker="bytetrack.yaml",
            classes=[2, 3, 5, 7],
            persist=True,
            stream=True,
        )
        tracks_out = []
        for frame_idx, r in enumerate(results):
            if r.boxes is None or r.boxes.id is None:
                continue
            boxes = r.boxes.xyxy.cpu().numpy()
            track_ids = r.boxes.id.int().cpu().tolist()
            for box, tid in zip(boxes, track_ids):
                feat = self.extract_crop_and_histogram(r.orig_img, box.tolist())
                tracks_out.append({
                    "frame": frame_idx,
                    "track_id": str(tid),
                    "camera_id": camera_id,
                    "bbox": [round(float(x), 1) for x in box],
                    "histogram": feat["histogram"],
                    "thumbnailDataUrl": feat["base64_jpeg"],
                })
        return tracks_out


app = FastAPI(title="EagleVision YOLOv8 + ByteTrack + Nebius Token Factory API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
tracker = CrossCameraTracker()


@app.post("/api/incident/report")
async def create_incident_report(req: IncidentReportRequest) -> Dict[str, Any]:
    api_key = (req.nebius_api_key or os.getenv("NEBIUS_API_KEY") or "").strip()
    if api_key:
        client = OpenAI(base_url=req.nebius_base_url, api_key=api_key)
        completion = client.chat.completions.create(
            model=req.model,
            messages=[
                {"role": "system", "content": "Return ONLY valid JSON matching the EagleVision ForensicReport schema."},
                {"role": "user", "content": json.dumps({"vehicle_id": req.vehicle_id, "timeline": req.handover_timeline})},
            ],
            temperature=0.15,
            max_tokens=1400,
        )
        raw = (completion.choices[0].message.content or "{}").strip().strip("`")
        return json.loads(raw)
    return {"status": "fallback_ready", "model": req.model}
