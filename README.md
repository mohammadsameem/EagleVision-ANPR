# EagleVision ANPR – Automatic Number Plate Recognition System

<p align="center">
  <img
    width="290"
    height="290"
    alt="logo"
    src="https://github.com/user-attachments/assets/b6fab35f-9636-41e4-b224-c4ca26064b1a"
  />
</p>

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.14.0-blue.svg)
![Tests](https://img.shields.io/badge/tests-184%2F199%20passing-green.svg)

**EagleVision** is an intelligent vehicle license plate recognition system built with YOLOv8, EasyOCR, and FastAPI. It processes CCTV footage to detect vehicles, locate license plates, and extract registration numbers with confidence scoring and human review workflow.

---

## ✨ Features

- **🚗 Vehicle Detection:** YOLOv8n model detects cars, trucks, buses, motorcycles
- **🔖 License Plate Detection:** Dedicated YOLOv8n model for accurate plate localization
- **📝 OCR Recognition:** EasyOCR with Lanczos4 preprocessing for small plates
- **🔄 Video Processing:** Time-based FPS sampling with timestamp preservation
- **🗄️ Database Persistence:** SQLAlchemy + SQLite for result storage
- **🔐 API Security:** API key authentication with resource ownership authorization
- **📊 Export Options:** CSV and JSON export for analysis
- **👤 Review Workflow:** Flag low-confidence detections for human verification
- **📈 Comprehensive Testing:** 184/199 tests passing (92.5%)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.14.0 or higher
- 4GB+ RAM
- 2GB+ disk space for models
- Windows/Linux/macOS

### Installation

```bash
# Clone repository
git clone <repository-url>
cd EagleVision

# Install dependencies
pip install -r requirements.txt

# Models download automatically on first run:
# - yolov8n.pt (6.25 MB) - vehicle detection
# - models/plate_detector.pt (5.96 MB) - plate detection
# - EasyOCR language models (~140 MB)
```

### Quick Test

```bash
# Test ANPR pipeline (30 seconds)
python -c "
from src.anpr_pipeline import ANPRPipeline
config = {'vehicle_model': 'yolov8n.pt', 'use_gpu': False}
pipeline = ANPRPipeline(config=config)
results = pipeline.process_video('data/test_videos/<your_video>.mp4', fps=5)
print(f'Detected: {len(results)} plates')
"
```

---

## 📖 Usage

### 1. Start API Server

```bash
# Development mode
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload

# Production mode
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2. Create User and API Key

```bash
# Create admin user
python scripts/manage_users.py create-user \
  --username admin \
  --email admin@example.com \
  --password your_secure_password \
  --admin

# Generate API key
python scripts/manage_users.py create-api-key --username admin

# Save the generated API key (format: prefix_secret)
```

### 3. Upload Video

```bash
curl -X POST http://localhost:8000/api/videos/upload \
  -H "X-API-Key: your_api_key_here" \
  -F "file=@path/to/video.mp4"

# Response: {"id": 1, "filename": "video.mp4", "status": "pending", ...}
```

### 4. Process Video

```bash
# Trigger ANPR processing
curl -X POST http://localhost:8000/api/videos/1/process \
  -H "X-API-Key: your_api_key_here"

# Check status
curl http://localhost:8000/api/videos/1/status \
  -H "X-API-Key: your_api_key_here"

# Wait until status: "completed"
```

### 5. Get Results

```bash
# Get complete results (JSON)
curl http://localhost:8000/api/videos/1/results \
  -H "X-API-Key: your_api_key_here"

# Export as CSV
curl http://localhost:8000/api/videos/1/export/csv \
  -H "X-API-Key: your_api_key_here" \
  -o results.csv

# Export as JSON
curl http://localhost:8000/api/videos/1/export/json \
  -H "X-API-Key: your_api_key_here" \
  -o results.json
```

### 6. Review Low-Confidence Detections

```bash
# Get items needing review
curl http://localhost:8000/api/detections/needs-review \
  -H "X-API-Key: your_api_key_here"

# Submit corrected text
curl -X POST http://localhost:8000/api/reviews/1 \
  -H "X-API-Key: your_api_key_here" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewed_text": "MH 12 AB 1234",
    "reviewer_id": "admin@example.com",
    "reviewer_notes": "Corrected OCR misread",
    "is_correct": false,
    "correction_type": "corrected"
  }'
```

---

## 🏗️ Architecture

```
EagleVision ANPR System
│
├── Video Processing
│   ├── Time-based FPS sampling
│   └── Timestamp preservation
│
├── Computer Vision
│   ├── YOLOv8n vehicle detection
│   ├── YOLOv8n plate detection (Koushim model)
│   └── Bounding box validation
│
├── OCR Engine
│   ├── EasyOCR (primary)
│   ├── PaddleOCR (fallback, partial support)
│   └── Lanczos4 preprocessing for small plates
│
├── FastAPI REST API
│   ├── Video upload and processing
│   ├── API key authentication
│   ├── Resource ownership authorization
│   └── CORS security
│
├── Database (SQLAlchemy + SQLite)
│   ├── Videos, Vehicles, Plates, OCR Results
│   ├── User management
│   └── API key management
│
└── Export & Review
    ├── CSV/JSON export
    └── Human review workflow
```

---

## 📁 Project Structure

```
EagleVision/
├── src/
│   ├── api/              # FastAPI REST API
│   ├── auth/             # Authentication and authorization
│   ├── database/         # SQLAlchemy models and CRUD
│   ├── anpr_pipeline.py  # Complete ANPR pipeline
│   ├── video_processor.py # Frame extraction
│   ├── plate_detector.py  # License plate detection
│   └── ocr_engine.py      # Hybrid OCR engine
├── tests/                 # Test suite (184/199 passing)
├── scripts/               # Utility scripts
├── data/
│   ├── test_videos/       # Sample CCTV footage
│   └── annotations/       # Ground truth (preparation ready)
├── models/
│   └── plate_detector.pt  # YOLOv8 plate detection model
├── validation_results/    # CCTV validation results
├── requirements.txt       # Python dependencies
├── .env.example           # Environment configuration template
└── README.md              # This file
```

---

## ⚙️ Configuration

### Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
```

**Required Configuration:**

```env
# CORS Security
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# Database (optional, defaults to SQLite)
DATABASE_URL=sqlite:///./eaglevision_anpr.db

# OCR Preprocessing
OCR_PREPROCESS_ENABLED=true
OCR_PREPROCESS_MIN_WIDTH=60
OCR_PREPROCESS_MIN_HEIGHT=15
OCR_PREPROCESS_TARGET_HEIGHT=60
OCR_PREPROCESS_METHOD=lanczos

# Background Processing (optional, requires Redis)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

### API Configuration

**Endpoints:** See auto-generated documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

---

## 🧪 Testing

### Run Test Suite

```bash
# All tests
python -m pytest tests/ -v

# Specific test categories
python -m pytest tests/test_fps_sampler.py -v      # FPS sampling (13/13)
python -m pytest tests/test_plate_detector.py -v   # Plate detection (17/17)
python -m pytest tests/test_security.py -v         # Security (19/19)
python -m pytest tests/test_ocr_preprocessing.py -v # OCR preprocessing (26/26)

# With coverage
python -m pytest tests/ --cov=src --cov-report=html
```

### Test Results Summary

```
✅ PASSED: 184 tests (92.5%)
⚠️  SKIPPED: 7 tests (3.5%) - Require Redis/Docker
❌ FAILED: 8 tests (4.0%) - Celery mocking issues (non-critical)
```

---

## 📊 Performance

### Processing Speed

- **Frame Sampling:** ~200 frames/second
- **Vehicle Detection:** ~15-20 FPS (CPU), ~60-80 FPS (GPU)
- **Plate Detection:** ~30-40 FPS (CPU), ~100+ FPS (GPU)
- **OCR:** ~5-10 plates/second per engine

### Detection Performance (Real CCTV Footage)

**Rear-Facing Cameras:**
- Plate Detection Rate: 84.2%
- Non-Empty OCR Rate: 82.6%

**Front-Facing Cameras:**
- Plate Detection Rate: 19.6% (lower due to angle)
- Non-Empty OCR Rate: 88.7%

**Note:** "Non-empty OCR rate" means plates with text output, not verified accuracy. Actual accuracy requires ground truth annotation (workflow prepared, annotation pending).

---

## 🔐 Security

### Implemented Controls

- ✅ **API Key Authentication:** SHA-256 hashed keys
- ✅ **Resource Ownership:** Users see only their videos
- ✅ **CORS Protection:** Explicit origin allowlist
- ✅ **Input Validation:** Filename sanitization, path traversal prevention
- ✅ **Rate Limiting:** Per-user request throttling
- ✅ **Error Sanitization:** No stack traces leaked to clients

### Security Best Practices

```bash
# 1. Set strong CORS origins in production
ALLOWED_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# 2. Use PostgreSQL for production (not SQLite)
DATABASE_URL=postgresql://user:pass@host:5432/eaglevision

# 3. Enable HTTPS with reverse proxy (nginx, Caddy)
# 4. Rotate API keys every 90 days
# 5. Monitor authentication failures
```

---

## 📚 Documentation

### Available Reports

- **FINAL_SUBMISSION_AUDIT.md** - Comprehensive audit report
- **PROJECT_STATUS.md** - Overall project status
- **TEST_REPORT.md** - Detailed test results
- **IMPLEMENTATION_LOG.md** - Development history
- **GROUND_TRUTH_ANNOTATION_GUIDE.md** - Accuracy measurement workflow
- **REAL_CCTV_COMBINED_REPORT.md** - CCTV validation results

### API Documentation

Auto-generated documentation available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🚧 Known Limitations

### Accuracy Measurement

- **83.8% non-empty OCR rate** reported on real CCTV footage
- **Actual accuracy UNMEASURED** (requires ground truth annotation)
- Ground truth annotation workflow prepared (74 frames selected)
- Manual annotation pending (estimated 8-11 hours)

### Implementation Gaps

1. **ByteTrack Not Implemented:** Vehicle tracking across frames missing
2. **Celery/Redis Unverified:** Background processing code complete but untested (Docker unavailable)
3. **PaddleOCR Partial:** Python 3.14 compatibility issues, fallback to EasyOCR only
4. **Limited Test Dataset:** Validated on 3 CCTV videos only (same location/lighting)
5. **Frontend Minimal:** API-first design, admin UI not implemented

### Production Requirements

Before production deployment:
- [ ] Complete ground truth annotation and measure actual accuracy
- [ ] Test Celery/Redis with Docker
- [ ] Expand test dataset (night, weather, multi-camera)
- [ ] Migrate to PostgreSQL
- [ ] Implement monitoring and alerts
- [ ] Perform load testing
- [ ] Build admin frontend UI

---

## 🤝 Contributing

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests in watch mode
python -m pytest tests/ -v --tb=short

# Check code style
flake8 src/ tests/
black src/ tests/ --check

# Type checking
mypy src/
```

### Adding New Features

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Write tests first (TDD approach)
4. Implement feature
5. Ensure all tests pass (`pytest tests/ -v`)
6. Update documentation
7. Commit changes (`git commit -m 'Add amazing feature'`)
8. Push to branch (`git push origin feature/amazing-feature`)
9. Open Pull Request

---

## 📝 License

This project uses multiple open-source components:

- **EagleVision Code:** MIT License (check LICENSE file)
- **YOLOv8:** AGPL-3.0 (Ultralytics)
- **Plate Detection Model:** MIT (Koushim/yolov8-license-plate-detection)
- **EasyOCR:** Apache 2.0
- **PaddleOCR:** Apache 2.0
- **FastAPI:** MIT

---

## 👏 Acknowledgments

- **Ultralytics YOLOv8** - Vehicle and plate detection models
- **Koushim** - License plate detection model (Hugging Face)
- **EasyOCR** - Primary OCR engine
- **PaddleOCR** - Fallback OCR engine
- **FastAPI** - Modern web framework for APIs

---

## 📞 Support

### Issues and Questions

- **Bug Reports:** Open an issue on GitHub
- **Feature Requests:** Open an issue with `enhancement` label
- **Security Issues:** Email security@example.com (private disclosure)

### Documentation

- **API Docs:** `http://localhost:8000/docs` (after starting server)
- **User Guide:** See `GROUND_TRUTH_ANNOTATION_GUIDE.md`
- **Deployment Guide:** See `FINAL_SUBMISSION_AUDIT.md` section 7

---

## 🗺️ Roadmap

### Phase 1: Complete Current Features
- [x] Core ANPR pipeline
- [x] API with security
- [x] Database persistence
- [ ] Ground truth annotation
- [ ] Verify Celery/Redis

### Phase 2: Accuracy Improvements
- [ ] ByteTrack vehicle tracking
- [ ] Multi-camera vehicle re-identification
- [ ] OCR confidence voting
- [ ] Advanced preprocessing techniques

### Phase 3: Production Features
- [ ] PostgreSQL migration
- [ ] Admin web interface
- [ ] Real-time monitoring dashboard
- [ ] Automated alerts and notifications
- [ ] LLM-powered incident summarization

### Phase 4: Advanced Features
- [ ] Multi-camera synchronization
- [ ] Vehicle behavior analysis
- [ ] Incident detection and classification
- [ ] Integration with traffic management systems

---

## 📈 Project Status

**Current Phase:** Core Pipeline Complete (92.5% tests passing)

**Verified Components:**
- ✅ Video processing and frame extraction
- ✅ Vehicle detection (YOLOv8n)
- ✅ License plate detection (YOLOv8n dedicated model)
- ✅ OCR with preprocessing (EasyOCR + Lanczos4)
- ✅ API with authentication and authorization
- ✅ Database persistence (SQLite)
- ✅ CSV/JSON export functionality

**Pending Verification:**
- ⏳ Actual OCR accuracy (ground truth annotation pending)
- ⏳ Celery/Redis background processing (Docker unavailable)

**Not Implemented:**
- ❌ ByteTrack vehicle tracking
- ❌ Multi-camera fusion
- ❌ LLM integration

---

**Last Updated:** 2026-10-28  
**Version:** 1.0.0  
**Status:** Functional - Ready for Demonstration

For detailed audit results, see `FINAL_SUBMISSION_AUDIT.md`


---

## AI Investigation Assistant (NVIDIA Nemotron)

EagleVision now includes an optional AI-powered investigation assistant using **NVIDIA Nemotron** through the **Nebius Token Factory** API.

### Features

The AI assistant provides:
- **Incident summaries** - Concise descriptions of detection events
- **Detection quality assessment** - Analysis of vehicle, plate, and OCR confidence
- **Pattern detection** - Identification of recurring issues or anomalies
- **OCR uncertainty analysis** - Explanation of why OCR results may need review
- **Recommended actions** - Prioritized review suggestions for human operators

**Important:** The AI assistant is an additional intelligence layer. It does NOT:
- Replace vehicle detection (YOLOv8)
- Replace plate detection
- Replace OCR engines (EasyOCR)
- Make criminality judgments
- Override security rules or watchlists

### Configuration

1. Get an API key from [Nebius Token Factory](https://tokenfactory.nebius.com/)

2. Add to `.env`:
```bash
NEBIUS_API_KEY=your_api_key_here
NEBIUS_MODEL=nvidia/Llama-3.1-Nemotron-70B-Instruct-HF
```

3. Restart the API server

### API Endpoints

#### Get AI Service Status
```bash
GET /api/ai/status
```

Returns Nebius connection status and available models.

#### Analyze ANPR Event
```bash
POST /api/ai/analyze-event
Content-Type: application/json
X-API-Key: your_api_key

{
  "ocr_result_id": 123,
  "max_tokens": 1000,
  "temperature": 0.7
}
```

Analyzes an OCR result and provides AI-powered investigation assistance.

#### Batch Analysis
```bash
POST /api/ai/batch-analyze
Content-Type: application/json
X-API-Key: your_api_key

{
  "ocr_result_ids": [123, 124, 125]
}
```

Analyzes multiple events concurrently (max 10 per request).

### Testing

Verify the integration:
```bash
python test_nemotron_live.py
```

This runs live API calls to Nebius Token Factory and verifies:
- API connectivity
- Model availability
- ANPR-specific analysis capabilities

### Status

✅ **VERIFIED** - Live integration tested and operational

**Live Test Results:**
- Successfully connected to Nebius Token Factory
- 30 models available
- NVIDIA Nemotron responds to ANPR-specific prompts
- End-to-end analysis workflow functional

**Model Used:** `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF`

See `test_nemotron_live.py` for detailed verification evidence.

---
