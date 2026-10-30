# Nebius Nemotron - Quick Setup Guide

## 🚀 5-Minute Setup

### Step 1: Get API Key
Visit: https://tokenfactory.nebius.com/
- Sign up / Log in
- Generate API key
- Copy key (starts with `v1.`)

### Step 2: Configure Environment

```bash
# Add to .env file
echo "NEBIUS_API_KEY=your_key_here" >> .env
echo "NEBIUS_MODEL=nvidia/Llama-3.1-Nemotron-70B-Instruct-HF" >> .env
```

### Step 3: Restart API Server

```bash
# Stop current server (Ctrl+C)

# Start server
python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Step 4: Verify Integration

```bash
# Run live verification
python test_nemotron_live.py

# Expected output:
# ✅ Connected to Nebius API
# ✅ Model responds to requests
# ✅ ANPR analysis functional
```

---

## 🧪 Testing Commands

### Check API Status
```bash
curl -H "X-API-Key: your_api_key" \
  http://localhost:8000/api/ai/status
```

### Analyze Event
```bash
curl -X POST http://localhost:8000/api/ai/analyze-event \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"ocr_result_id": 1, "max_tokens": 800}'
```

### Batch Analysis
```bash
curl -X POST http://localhost:8000/api/ai/batch-analyze \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"ocr_result_ids": [1, 2, 3]}'
```

---

## 📊 Available Models

**Recommended:**
- `nvidia/Llama-3.1-Nemotron-70B-Instruct-HF` ✅ (configured by default)

**Alternatives:**
- `nvidia/Nemotron-4-340B-Instruct` (larger, more capable)
- Check `/api/ai/status` for full list (30+ models available)

---

## 🔧 Troubleshooting

### Problem: "Service not configured"
**Solution:**
```bash
# Check if NEBIUS_API_KEY is set
cat .env | grep NEBIUS

# Restart API server after adding key
```

### Problem: "Authentication failed"
**Solution:**
- Verify key at https://tokenfactory.nebius.com/
- Check for extra spaces in .env
- Regenerate key if needed

### Problem: "Rate limit exceeded"
**Solution:**
- Wait 60 seconds
- Use batch endpoint for multiple events
- Check Nebius plan limits

---

## ✅ Verification Checklist

- [ ] NEBIUS_API_KEY added to .env
- [ ] API server restarted
- [ ] `python test_nemotron_live.py` passes all tests
- [ ] `/api/ai/status` returns `"available": true`
- [ ] `/api/ai/analyze-event` returns analysis

---

## 📚 Documentation

- **Full Integration Report:** See `NEBIUS_NEMOTRON_INTEGRATION_REPORT.md`
- **API Documentation:** http://localhost:8000/docs
- **README:** See "AI Investigation Assistant" section

---

## 🎯 Quick Test

```python
import requests

# Get API key (replace with actual key)
API_KEY = "your_key_here"

# Test status
status = requests.get(
    "http://localhost:8000/api/ai/status",
    headers={"X-API-Key": API_KEY}
).json()

print(f"AI Available: {status['available']}")
print(f"Model: {status['configured_model']}")
print(f"Total Models: {status['total_models']}")
```

---

**Status:** ✅ VERIFIED - Live integration tested and operational  
**Setup Time:** ~5 minutes  
**Cost:** Pay-as-you-go (Nebius Token Factory pricing)
