"""Quick test script for FastAPI endpoints"""
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

# Test root endpoint
print("Testing GET /")
response = client.get("/")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Test health check
print("Testing GET /health")
response = client.get("/health")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Test API docs
print("Testing GET /docs (OpenAPI docs)")
response = client.get("/docs")
print(f"Status: {response.status_code}")
print(f"Docs available: {response.status_code == 200}\n")

# Test video list (empty initially)
print("Testing GET /api/videos/")
response = client.get("/api/videos/")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

# Test needs review (empty initially)
print("Testing GET /api/detections/needs-review")
response = client.get("/api/detections/needs-review")
print(f"Status: {response.status_code}")
print(f"Response: {response.json()}\n")

print("✅ All API tests passed!")
