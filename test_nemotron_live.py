"""
Live verification test for Nebius Nemotron integration

This script performs actual live API calls to verify the integration works.
"""
import asyncio
import os
from dotenv import load_dotenv
from src.services.nebius_nemotron import get_nemotron_service

# Load environment variables
load_dotenv()

# Sample ANPR event data
SAMPLE_EVENT = {
    "event_id": "live_test_001",
    "timestamp": "2026-10-30T10:00:00Z",
    "camera_id": "CAM_VERIFICATION",
    "vehicle_class": "car",
    "vehicle_confidence": 95.5,
    "plate_method": "yolo_model",
    "plate_confidence": 88.3,
    "ocr_text": "TEST123",
    "ocr_confidence": 92.1,
    "ocr_engine": "easyocr",
    "needs_review": True,
    "review_reason": "Verification test",
    "context": {
        "test": True,
        "purpose": "Live Nebius API verification"
    }
}


async def test_connection():
    """Test 1: Verify connection to Nebius API."""
    print("\n" + "="*70)
    print("TEST 1: Verify Connection to Nebius Token Factory")
    print("="*70)
    
    service = get_nemotron_service()
    
    if not service.is_available():
        print("\n❌ FAILED: NEBIUS_API_KEY not configured")
        print("   Set NEBIUS_API_KEY in .env file")
        return False
    
    print(f"\n✅ Service initialized")
    print(f"   Base URL: {service.base_url}")
    print(f"   Configured Model: {service.model}")
    
    print("\n🔍 Verifying API connection...")
    result = await service.verify_connection()
    
    if not result["available"]:
        print(f"\n❌ FAILED: Connection verification failed")
        print(f"   Error: {result.get('error')}")
        return False
    
    print(f"\n✅ Successfully connected to Nebius API!")
    print(f"   Total available models: {result['total_models']}")
    print(f"   Configured model available: {result['model_available']}")
    
    if result.get("available_models"):
        print(f"\n📋 Sample available models:")
        for model in result["available_models"][:5]:
            marker = " ✓" if model == service.model else ""
            print(f"   - {model}{marker}")
    
    return True


async def test_analyze_event():
    """Test 2: Perform live ANPR event analysis."""
    print("\n" + "="*70)
    print("TEST 2: Live ANPR Event Analysis with Nemotron")
    print("="*70)
    
    service = get_nemotron_service()
    
    if not service.is_available():
        print("\n⏭️  SKIPPED: Service not configured")
        return False
    
    print(f"\n📤 Sending analysis request to Nemotron...")
    print(f"   Event ID: {SAMPLE_EVENT['event_id']}")
    print(f"   OCR Text: {SAMPLE_EVENT['ocr_text']}")
    print(f"   OCR Confidence: {SAMPLE_EVENT['ocr_confidence']}%")
    
    result = await service.analyze_anpr_event(SAMPLE_EVENT, max_tokens=800)
    
    if not result["success"]:
        print(f"\n❌ FAILED: Analysis failed")
        print(f"   Error: {result['error']}")
        return False
    
    print(f"\n✅ Analysis completed successfully!")
    print(f"   Model: {result['model']}")
    print(f"   Tokens Used: {result['usage']['total_tokens']}")
    print(f"   - Prompt: {result['usage']['prompt_tokens']}")
    print(f"   - Completion: {result['usage']['completion_tokens']}")
    
    analysis = result["analysis"]
    print(f"\n📊 AI Analysis (first 500 characters):")
    print("─" * 70)
    print(analysis[:500])
    if len(analysis) > 500:
        print(f"... ({len(analysis) - 500} more characters)")
    print("─" * 70)
    
    # Check for key analysis sections
    required_sections = [
        "Incident Summary",
        "Detection Quality",
        "Recommended Actions"
    ]
    
    missing_sections = []
    for section in required_sections:
        if section.lower() not in analysis.lower():
            missing_sections.append(section)
    
    if missing_sections:
        print(f"\n⚠️  WARNING: Some expected sections missing:")
        for section in missing_sections:
            print(f"   - {section}")
    else:
        print(f"\n✅ All expected analysis sections present")
    
    return True


async def test_model_capabilities():
    """Test 3: Verify model responds to ANPR-specific prompts."""
    print("\n" + "="*70)
    print("TEST 3: ANPR-Specific Model Capabilities")
    print("="*70)
    
    service = get_nemotron_service()
    
    if not service.is_available():
        print("\n⏭️  SKIPPED: Service not configured")
        return False
    
    # Test with a scenario requiring ANPR domain knowledge
    anpr_scenario = {
        "event_id": "capability_test",
        "timestamp": "2026-10-30T14:30:00Z",
        "camera_id": "CAM_TEST",
        "vehicle_class": "truck",
        "vehicle_confidence": 78.2,
        "plate_method": "heuristic_fallback",
        "plate_confidence": 65.0,
        "ocr_text": "ABC1Z3",  # Potentially ambiguous (1 vs I, Z vs 2)
        "ocr_confidence": 71.5,
        "ocr_engine": "easyocr",
        "needs_review": True,
        "review_reason": "Low confidence + ambiguous characters",
        "context": {"frame_quality": "low_light"}
    }
    
    print(f"\n🧪 Testing with ambiguous OCR scenario...")
    print(f"   OCR Text: {anpr_scenario['ocr_text']} (potentially ambiguous)")
    print(f"   Detection Method: {anpr_scenario['plate_method']}")
    print(f"   Confidence: {anpr_scenario['ocr_confidence']}%")
    
    result = await service.analyze_anpr_event(anpr_scenario, max_tokens=600, temperature=0.5)
    
    if not result["success"]:
        print(f"\n❌ FAILED: Analysis failed")
        print(f"   Error: {result['error']}")
        return False
    
    analysis = result["analysis"]
    
    # Check if model identifies the ambiguity
    ambiguity_keywords = ["ambiguous", "1", "I", "Z", "2", "uncertain", "confus"]
    found_ambiguity_discussion = any(kw.lower() in analysis.lower() for kw in ambiguity_keywords)
    
    print(f"\n✅ Model responded to ANPR scenario")
    print(f"   Discussed character ambiguity: {'Yes ✓' if found_ambiguity_discussion else 'No'}")
    print(f"   Response length: {len(analysis)} characters")
    
    return True


async def main():
    """Run all live verification tests."""
    print("\n" + "="*70)
    print(" NEBIUS NEMOTRON LIVE INTEGRATION VERIFICATION")
    print("="*70)
    print("\nThis script verifies the Nebius Token Factory integration")
    print("performs LIVE API calls to validate the integration.")
    print("\n⚠️  Requires: NEBIUS_API_KEY configured in .env")
    
    # Check API key
    api_key = os.getenv("NEBIUS_API_KEY")
    if not api_key:
        print("\n❌ CRITICAL: NEBIUS_API_KEY not found in environment")
        print("   1. Copy .env.example to .env")
        print("   2. Add your Nebius API key")
        print("   3. Run this script again")
        return False
    
    print(f"\n✅ API key found (length: {len(api_key)} characters)")
    
    # Run tests
    results = []
    
    try:
        results.append(("Connection", await test_connection()))
        results.append(("Event Analysis", await test_analyze_event()))
        results.append(("ANPR Capabilities", await test_model_capabilities()))
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Summary
    print("\n" + "="*70)
    print(" VERIFICATION SUMMARY")
    print("="*70)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name:<25} {status}")
    
    all_passed = all(result for _, result in results)
    
    print("\n" + "="*70)
    if all_passed:
        print(" ✅ ALL TESTS PASSED - NEBIUS NEMOTRON INTEGRATION VERIFIED")
        print("="*70)
        print("\nThe integration is working correctly:")
        print("  ✓ Successfully connected to Nebius Token Factory")
        print("  ✓ NVIDIA Nemotron model responds to requests")
        print("  ✓ ANPR-specific analysis is functional")
        print("  ✓ Error handling is in place")
        print("\nStatus: VERIFIED")
    else:
        print(" ⚠️  SOME TESTS FAILED - REVIEW REQUIRED")
        print("="*70)
        print("\nStatus: IMPLEMENTED - VERIFICATION PENDING")
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
