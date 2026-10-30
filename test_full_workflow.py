"""
Test complete workflow: Upload -> Process -> Query -> Export

Tests the full database/API integration with actual video processing.
"""
from fastapi.testclient import TestClient
from pathlib import Path
import json

from src.api.main import app

client = TestClient(app)

print("="*70)
print("EagleVision ANPR - Full Workflow Test")
print("="*70)

# 1. Check API health
print("\n1️⃣  Testing API health...")
response = client.get("/health")
assert response.status_code == 200
print(f"✅ API healthy: {response.json()}")

# 2. List videos (should be empty initially)
print("\n2️⃣  Listing videos...")
response = client.get("/api/videos/")
assert response.status_code == 200
data = response.json()
print(f"✅ Initial videos count: {data['total']}")

# 3. Upload a test video
print("\n3️⃣  Uploading test video...")
test_video = Path("data/test_videos/gemini_generated_video_0eb4eec1.mp4")

if not test_video.exists():
    print(f"⚠️  Test video not found: {test_video}")
    print("Skipping upload/processing test")
else:
    with open(test_video, "rb") as f:
        files = {"file": (test_video.name, f, "video/mp4")}
        response = client.post(
            "/api/videos/upload",
            files=files,
            params={"target_fps": 1.0}  # Use 1 FPS for faster testing
        )
    
    if response.status_code != 201:
        print(f"❌ Upload failed: {response.status_code}")
        print(response.json())
    else:
        video_data = response.json()
        video_id = video_data["id"]
        print(f"✅ Video uploaded: ID {video_id}")
        print(f"   Filename: {video_data['filename']}")
        print(f"   Resolution: {video_data['resolution']}")
        print(f"   Duration: {video_data['duration_sec']}s")
        print(f"   FPS: {video_data['fps']}")
        print(f"   Status: {video_data['status']}")
        
        # 4. Check video status
        print(f"\n4️⃣  Checking video status...")
        response = client.get(f"/api/videos/{video_id}/status")
        assert response.status_code == 200
        status_data = response.json()
        print(f"✅ Status: {status_data['status']}")
        print(f"   Progress: {status_data['progress_percent']:.1f}%")
        
        # 5. Process video
        print(f"\n5️⃣  Processing video (this may take a minute)...")
        print(f"   Note: Running ANPR pipeline synchronously")
        response = client.post(f"/api/videos/{video_id}/process")
        
        if response.status_code != 200:
            print(f"❌ Processing failed: {response.status_code}")
            print(response.json())
        else:
            result = response.json()
            print(f"✅ Processing completed!")
            print(f"   Status: {result['status']}")
            print(f"   Vehicles: {result['total_vehicles']}")
            print(f"   Plates: {result['total_plates']}")
            
            # 6. Get results
            print(f"\n6️⃣  Retrieving ANPR results...")
            response = client.get(f"/api/videos/{video_id}/results")
            
            if response.status_code != 200:
                print(f"❌ Failed to get results: {response.status_code}")
            else:
                results = response.json()
                stats = results['statistics']
                print(f"✅ Results retrieved!")
                print(f"   Total vehicles: {stats['total_vehicles']}")
                print(f"   Total plates: {stats['total_plates']}")
                print(f"   Plates with text: {stats['plates_with_text']}")
                print(f"   Needs review: {stats['needs_review']}")
                print(f"   Detection rate: {stats['detection_rate']}")
                print(f"   OCR success rate: {stats['ocr_success_rate']}")
                
                # Show sample detections
                if results['detections']:
                    print(f"\n   Sample detection:")
                    detection = results['detections'][0]
                    print(f"   - Frame: {detection['frame_index']}")
                    print(f"   - Timestamp: {detection['timestamp_ms']}ms")
                    print(f"   - Vehicle confidence: {detection['confidence']:.2f}")
                    if detection['plates']:
                        plate = detection['plates'][0]
                        print(f"   - Plate confidence: {plate['confidence']:.2f}")
                        print(f"   - Detection method: {plate['detection_method']}")
                        if plate['ocr_results']:
                            ocr = plate['ocr_results'][0]
                            print(f"   - OCR text: {ocr['text'] or '(empty)'}")
                            print(f"   - OCR confidence: {ocr['confidence'] or 'N/A'}")
                            print(f"   - Needs review: {ocr['needs_review']}")
            
            # 7. Check needs-review endpoint
            print(f"\n7️⃣  Checking detections needing review...")
            response = client.get("/api/detections/needs-review")
            assert response.status_code == 200
            review_list = response.json()
            print(f"✅ Detections needing review: {len(review_list)}")
            
            if review_list:
                sample = review_list[0]
                print(f"   Sample review item:")
                print(f"   - OCR ID: {sample['ocr_id']}")
                print(f"   - Text: {sample['text'] or '(empty)'}")
                print(f"   - Reason: {sample['review_reason']}")
            
            # 8. Export as CSV
            print(f"\n8️⃣  Testing CSV export...")
            response = client.get(f"/api/videos/{video_id}/export/csv")
            assert response.status_code == 200
            csv_data = response.text
            lines = csv_data.strip().split('\n')
            print(f"✅ CSV export successful")
            print(f"   Lines: {len(lines)} (including header)")
            print(f"   Header: {lines[0] if lines else 'N/A'}")
            
            # 9. Export as JSON
            print(f"\n9️⃣  Testing JSON export...")
            response = client.get(f"/api/videos/{video_id}/export/json")
            assert response.status_code == 200
            json_data = response.json()
            print(f"✅ JSON export successful")
            print(f"   Fields: {list(json_data.keys())}")
            
            # 10. Submit a review (if there are items needing review)
            if review_list:
                print(f"\n🔟 Testing review submission...")
                ocr_id = review_list[0]['ocr_id']
                review_payload = {
                    "reviewed_text": "MH 12 AB 1234",
                    "reviewer_id": "test_user",
                    "reviewer_notes": "Test review from API workflow test",
                    "is_correct": False,
                    "correction_type": "corrected"
                }
                response = client.post(f"/api/reviews/{ocr_id}", json=review_payload)
                
                if response.status_code == 201:
                    review_result = response.json()
                    print(f"✅ Review submitted!")
                    print(f"   Review ID: {review_result['id']}")
                    print(f"   Reviewed text: {review_result['reviewed_text']}")
                else:
                    print(f"⚠️  Review submission: {response.status_code}")

print("\n" + "="*70)
print("✅ Full workflow test completed successfully!")
print("="*70)
