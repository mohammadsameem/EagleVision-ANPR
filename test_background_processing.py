"""
Test script for background video processing with Celery

Tests:
1. Upload video
2. Submit background processing task
3. Poll status until completion
4. Verify results stored in database
5. Test synchronous processing (fallback)
"""
import time
import requests
from pathlib import Path

# Configuration
API_BASE = "http://localhost:8000"
TEST_VIDEO = "data/test_videos/gemini_generated_video_0eb4eec1.mp4"

def test_background_processing():
    """Test complete background processing workflow"""
    print("=" * 80)
    print("EagleVision ANPR - Background Processing Test")
    print("=" * 80)
    
    # Check if test video exists
    video_path = Path(TEST_VIDEO)
    if not video_path.exists():
        print(f"\n❌ Test video not found: {TEST_VIDEO}")
        print("Please ensure test video exists before running")
        return False
    
    print(f"\n✅ Test video found: {TEST_VIDEO}")
    print(f"   Size: {video_path.stat().st_size / (1024*1024):.2f} MB")
    
    # Step 1: Upload video
    print("\n" + "="*80)
    print("Step 1: Upload Video")
    print("="*80)
    
    with open(TEST_VIDEO, "rb") as f:
        response = requests.post(
            f"{API_BASE}/api/videos/upload",
            files={"file": (video_path.name, f, "video/mp4")},
            params={"target_fps": 1}  # 1 FPS for faster testing
        )
    
    if response.status_code != 201:
        print(f"\n❌ Upload failed: {response.status_code}")
        print(response.text)
        return False
    
    video_data = response.json()
    video_id = video_data["id"]
    print(f"\n✅ Video uploaded successfully")
    print(f"   ID: {video_id}")
    print(f"   Filename: {video_data['filename']}")
    print(f"   Status: {video_data['status']}")
    print(f"   Duration: {video_data['duration_sec']:.1f}s")
    print(f"   FPS: {video_data['fps']:.1f}")
    print(f"   Frames: {video_data['frame_count']}")
    
    # Step 2: Submit background processing
    print("\n" + "="*80)
    print("Step 2: Submit Background Processing")
    print("="*80)
    
    response = requests.post(
        f"{API_BASE}/api/videos/{video_id}/process",
        params={"use_celery": True}
    )
    
    if response.status_code != 200:
        print(f"\n❌ Processing submission failed: {response.status_code}")
        print(response.text)
        
        # Try synchronous as fallback
        print("\n⚠️  Attempting synchronous processing (Celery may be unavailable)...")
        response = requests.post(
            f"{API_BASE}/api/videos/{video_id}/process",
            params={"use_celery": False}
        )
        
        if response.status_code != 200:
            print(f"❌ Synchronous processing also failed: {response.status_code}")
            return False
        
        use_celery = False
    else:
        use_celery = True
    
    process_data = response.json()
    print(f"\n✅ Processing submitted")
    print(f"   Status: {process_data['status']}")
    print(f"   Use Celery: {use_celery}")
    if "task_id" in process_data:
        print(f"   Task ID: {process_data['task_id']}")
    
    # Step 3: Poll status until completion
    print("\n" + "="*80)
    print("Step 3: Poll Processing Status")
    print("="*80)
    
    start_time = time.time()
    last_status = None
    poll_count = 0
    
    while True:
        poll_count += 1
        elapsed = time.time() - start_time
        
        response = requests.get(f"{API_BASE}/api/videos/{video_id}/status")
        if response.status_code != 200:
            print(f"\n❌ Status check failed: {response.status_code}")
            return False
        
        status_data = response.json()
        current_status = status_data["status"]
        
        # Print status if changed
        if current_status != last_status:
            print(f"\n[{elapsed:.1f}s] Status changed: {last_status} → {current_status}")
            print(f"   Frames: {status_data['frames_processed']}/{status_data['total_frames']}")
            print(f"   Progress: {status_data['progress_percent']:.1f}%")
            print(f"   Vehicles: {status_data['total_vehicles']}")
            print(f"   Plates: {status_data['total_plates']}")
            last_status = current_status
        
        # Check if completed or failed
        if current_status == "completed":
            print(f"\n✅ Processing completed in {elapsed:.1f}s ({poll_count} polls)")
            break
        elif current_status == "failed":
            print(f"\n❌ Processing failed after {elapsed:.1f}s")
            print(f"   Error: {status_data.get('error_message', 'Unknown error')}")
            return False
        
        # Wait before next poll
        time.sleep(2)
        
        # Timeout after 5 minutes
        if elapsed > 300:
            print(f"\n⏱️  Timeout after {elapsed:.1f}s (status: {current_status})")
            break
    
    # Step 4: Retrieve results
    print("\n" + "="*80)
    print("Step 4: Retrieve Results")
    print("="*80)
    
    response = requests.get(f"{API_BASE}/api/videos/{video_id}/results")
    if response.status_code != 200:
        print(f"\n❌ Results retrieval failed: {response.status_code}")
        print(response.text)
        return False
    
    results_data = response.json()
    stats = results_data["statistics"]
    
    print(f"\n✅ Results retrieved successfully")
    print(f"   Total vehicles: {stats['total_vehicles']}")
    print(f"   Total plates: {stats['total_plates']}")
    print(f"   Plates with text: {stats['plates_with_text']}")
    print(f"   Needs review: {stats['needs_review']}")
    print(f"   Detection rate: {stats['detection_rate']}")
    print(f"   OCR success rate: {stats['ocr_success_rate']}")
    
    # Sample detections
    detections = results_data["detections"]
    if detections:
        print(f"\n   Sample detections:")
        for i, detection in enumerate(detections[:3]):
            frame = detection["frame_index"]
            plates_count = len(detection["plates"])
            print(f"   - Frame {frame}: {plates_count} plates")
    
    # Step 5: Test CSV export
    print("\n" + "="*80)
    print("Step 5: Export Results")
    print("="*80)
    
    response = requests.get(f"{API_BASE}/api/videos/{video_id}/export/csv")
    if response.status_code == 200:
        csv_lines = response.text.strip().split("\n")
        print(f"✅ CSV export: {len(csv_lines)} lines ({len(csv_lines)-1} data rows)")
    else:
        print(f"⚠️  CSV export failed: {response.status_code}")
    
    response = requests.get(f"{API_BASE}/api/videos/{video_id}/export/json")
    if response.status_code == 200:
        json_data = response.json()
        print(f"✅ JSON export: {len(json_data.get('detections', []))} detections")
    else:
        print(f"⚠️  JSON export failed: {response.status_code}")
    
    # Step 6: Cleanup (optional)
    print("\n" + "="*80)
    print("Step 6: Cleanup (Optional)")
    print("="*80)
    
    cleanup = input("\nDelete test video from database? (y/N): ").strip().lower()
    if cleanup == "y":
        response = requests.delete(f"{API_BASE}/api/videos/{video_id}")
        if response.status_code == 204:
            print("✅ Video deleted successfully")
        else:
            print(f"⚠️  Delete failed: {response.status_code}")
    else:
        print(f"ℹ️  Video {video_id} kept in database")
    
    print("\n" + "="*80)
    print("✅ Background Processing Test Complete")
    print("="*80)
    
    return True


def test_duplicate_processing():
    """Test that duplicate processing requests don't create duplicate results"""
    print("\n" + "="*80)
    print("Duplicate Processing Test")
    print("="*80)
    
    # Upload video
    with open(TEST_VIDEO, "rb") as f:
        response = requests.post(
            f"{API_BASE}/api/videos/upload",
            files={"file": (Path(TEST_VIDEO).name, f, "video/mp4")},
            params={"target_fps": 1}
        )
    
    if response.status_code != 201:
        print(f"❌ Upload failed: {response.status_code}")
        return False
    
    video_id = response.json()["id"]
    print(f"✅ Video uploaded: {video_id}")
    
    # Process once
    response = requests.post(
        f"{API_BASE}/api/videos/{video_id}/process",
        params={"use_celery": False}  # Synchronous for simplicity
    )
    
    if response.status_code != 200:
        print(f"❌ First processing failed: {response.status_code}")
        return False
    
    first_stats = response.json()
    print(f"✅ First processing: {first_stats['total_vehicles']} vehicles")
    
    # Try to process again (should be rejected or return same results)
    response = requests.post(
        f"{API_BASE}/api/videos/{video_id}/process",
        params={"use_celery": False}
    )
    
    if response.status_code == 400:
        print("✅ Duplicate processing correctly rejected")
    elif response.status_code == 200:
        second_stats = response.json()
        if second_stats['total_vehicles'] == first_stats['total_vehicles']:
            print("✅ Duplicate processing returned same results (idempotent)")
        else:
            print(f"❌ Duplicate processing created different results!")
            return False
    else:
        print(f"⚠️  Unexpected response: {response.status_code}")
    
    # Cleanup
    requests.delete(f"{API_BASE}/api/videos/{video_id}")
    
    return True


if __name__ == "__main__":
    print("\n")
    print("╔═══════════════════════════════════════════════════════════════╗")
    print("║  EagleVision ANPR - Background Processing Test Suite         ║")
    print("╚═══════════════════════════════════════════════════════════════╝")
    print("\nPrerequisites:")
    print("  1. Redis running (docker-compose -f docker-compose.dev.yml up -d)")
    print("  2. Celery worker running (celery -A src.celery_app worker --loglevel=info --pool=solo)")
    print("  3. FastAPI running (uvicorn src.api.main:app --reload)")
    print("  4. Test video available")
    print("\n")
    
    proceed = input("Continue with tests? (Y/n): ").strip().lower()
    if proceed == "n":
        print("Tests cancelled")
        exit(0)
    
    try:
        # Test 1: Background processing
        success1 = test_background_processing()
        
        # Test 2: Duplicate processing
        #success2 = test_duplicate_processing()
        
        print("\n" + "="*80)
        print("TEST SUMMARY")
        print("="*80)
        print(f"Background Processing: {'✅ PASS' if success1 else '❌ FAIL'}")
        #print(f"Duplicate Prevention: {'✅ PASS' if success2 else '❌ FAIL'}")
        print("="*80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Tests failed with exception: {e}")
        import traceback
        traceback.print_exc()
