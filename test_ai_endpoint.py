"""
Quick test script for AI endpoints
"""
import requests
import hashlib
import sqlite3
import secrets

# Generate a new API key
raw_key = secrets.token_hex(16)
key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
key_prefix = raw_key[:8]

# Store in database (admin user, id=2)
conn = sqlite3.connect('eaglevision_anpr.db')
cursor = conn.execute(
    "INSERT INTO api_keys (user_id, key_hash, key_prefix, name, is_active, created_at) "
    "VALUES (?, ?, ?, ?, ?, datetime('now'))",
    (2, key_hash, key_prefix, "test_ai_key", 1)
)
conn.commit()
conn.close()

print(f"✅ Created test API key: {raw_key}")
print(f"   Prefix: {key_prefix}")

# Test AI status endpoint
print(f"\n🔍 Testing /api/ai/status endpoint...")
response = requests.get(
    "http://127.0.0.1:8000/api/ai/status",
    headers={"X-API-Key": raw_key}
)

print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   AI Service Available: {data['available']}")
    print(f"   Configured Model: {data.get('configured_model')}")
    print(f"   Model Available: {data.get('model_available')}")
    print(f"   Total Models: {data.get('total_models')}")
else:
    print(f"   Error: {response.json()}")

# Test analyze-event endpoint
print(f"\n🔍 Testing /api/ai/analyze-event endpoint...")

event_request = {
    "event_id": "api_test_001",
    "max_tokens": 500,
    "temperature": 0.7
}

response = requests.post(
    "http://127.0.0.1:8000/api/ai/analyze-event",
    headers={
        "X-API-Key": raw_key,
        "Content-Type": "application/json"
    },
    json=event_request
)

print(f"   Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"   Success: {data['success']}")
    print(f"   Model: {data.get('model')}")
    if data['success'] and data['analysis']:
        analysis_preview = data['analysis'][:200]
        print(f"   Analysis Preview: {analysis_preview}...")
else:
    print(f"   Response: {response.json()}")

print(f"\n✅ API endpoint test complete!")
