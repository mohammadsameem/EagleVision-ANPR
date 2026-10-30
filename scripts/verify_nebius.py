"""
Verify Nebius Token Factory API access and available NVIDIA models.
Reports actual endpoint, model IDs, and licenses without assumptions.
"""
import os
import sys
import json
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def verify_nebius_api():
    """Verify Nebius Token Factory API and document findings"""
    
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        print("❌ NEBIUS_API_KEY not found in environment")
        print("   Set it with: export NEBIUS_API_KEY='your-key-here'")
        print("   Or add to .env file")
        return False
    
    # Test primary endpoint
    base_url = "https://api.tokenfactory.nebius.com/v1/"
    print(f"\n🔍 Testing endpoint: {base_url}")
    print(f"   API key: {api_key[:10]}...{api_key[-4:]}")
    
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        
        # Try to list models (if supported)
        print("\n📋 Attempting to list models...")
        try:
            models = client.models.list()
            print(f"✅ Models endpoint available")
            print(f"   Found {len(models.data)} models:")
            for model in models.data:
                print(f"   - {model.id}")
        except Exception as e:
            print(f"ℹ️  Models listing not supported or requires different method")
            print(f"   Error: {str(e)[:100]}")
        
        # Test completion with known model
        test_model = "nvidia/Llama-3.1-Nemotron-70B-Instruct"
        print(f"\n🧪 Testing completion with: {test_model}")
        
        import time
        start_time = time.time()
        
        response = client.chat.completions.create(
            model=test_model,
            messages=[{"role": "user", "content": "Reply with just 'OK'"}],
            max_tokens=10,
            temperature=0.1
        )
        
        latency_ms = int((time.time() - start_time) * 1000)
        
        print(f"✅ Completion successful ({latency_ms}ms)")
        print(f"   Response: {response.choices[0].message.content}")
        print(f"   Model: {response.model}")
        
        # Document findings
        report = {
            "endpoint": base_url,
            "model_tested": test_model,
            "model_responded": response.model,
            "status": "verified",
            "latency_ms": latency_ms,
            "note": "License verification requires checking NVIDIA documentation and Llama 3.1 Community License"
        }
        
        print(f"\n📝 Verification Report:")
        print(json.dumps(report, indent=2))
        
        # Save report
        with open("scripts/nebius_verification_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n💾 Report saved to: scripts/nebius_verification_report.json")
        
        return True
        
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        print(f"\nFull error details:")
        print(f"  Type: {type(e).__name__}")
        print(f"  Message: {str(e)}")
        
        # Document failure
        report = {
            "endpoint": base_url,
            "status": "failed",
            "error": str(e),
            "note": "API credentials may be invalid or endpoint may have changed"
        }
        
        with open("scripts/nebius_verification_report.json", "w") as f:
            json.dump(report, f, indent=2)
        
        return False

if __name__ == "__main__":
    print("="*60)
    print("Nebius Token Factory API Verification")
    print("="*60)
    
    success = verify_nebius_api()
    
    print("\n" + "="*60)
    if success:
        print("✅ Verification PASSED")
    else:
        print("❌ Verification FAILED")
    print("="*60)
    
    sys.exit(0 if success else 1)
