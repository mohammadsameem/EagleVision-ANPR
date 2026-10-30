"""
Demonstration script for ANPR pipeline.

This script tests the complete pipeline on sample videos and reports
actual capabilities and results without fabrication.
"""
import sys
import os
import logging
from pathlib import Path
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Run ANPR pipeline demonstration"""
    
    print("="*60)
    print("EagleVision ANPR Pipeline Demonstration")
    print("="*60)
    
    # Check for sample video
    sample_videos = [
        "public/videos/cam-n4.mp4",
        "public/videos/cam-w2.mp4",
        "public/videos/cam-s1.mp4"
    ]
    
    available_videos = [v for v in sample_videos if Path(v).exists()]
    
    if not available_videos:
        print("\n❌ No sample videos found!")
        print("   Expected videos in: public/videos/")
        return 1
    
    print(f"\n[OK] Found {len(available_videos)} sample videos:")
    for video in available_videos:
        size_mb = Path(video).stat().st_size / (1024*1024)
        print(f"   - {video} ({size_mb:.2f} MB)")
    
    # Import pipeline
    try:
        from src.anpr_pipeline import ANPRPipeline
        print("\n[OK] ANPR Pipeline module imported")
    except ImportError as e:
        print(f"\n❌ Failed to import ANPR pipeline: {e}")
        return 1
    
    # Initialize pipeline
    print("\nInitializing pipeline...")
    try:
        pipeline = ANPRPipeline(config={
            "use_gpu": False,
            "confidence_threshold": 0.70
        })
    except Exception as e:
        print(f"❌ Failed to initialize pipeline: {e}")
        return 1
    
    # Check capabilities
    capabilities = pipeline.get_capabilities()
    print("\n📊 Pipeline Capabilities:")
    print(json.dumps(capabilities, indent=2))
    
    if not capabilities["vehicle_detection"]:
        print("\n[!] Vehicle detection not available")
        print("   Install ultralytics with: pip install ultralytics")
        print("   First run will download YOLOv8 model (~6MB)")
    
    if not capabilities["ocr"]:
        print("\n[!] OCR not available")
        print("   Install PaddleOCR with: pip install paddleocr")
        print("   Install EasyOCR with: pip install easyocr")
    
    # Process first video (limit to 30 frames for demo)
    test_video = available_videos[0]
    print(f"\n{'='*60}")
    print(f"Testing pipeline on: {test_video}")
    print(f"Processing at 5 FPS (sampling every ~6th frame)")
    print(f"{'='*60}")
    
    try:
        results = pipeline.process_video(test_video, fps=5)
        
        print(f"\n{'='*60}")
        print(f"Results Summary")
        print(f"{'='*60}")
        print(f"Total detections: {len(results)}")
        
        if results:
            # Count detections with plates
            with_plates = sum(1 for r in results if r["plate_bbox"] is not None)
            with_ocr = sum(1 for r in results if r["ocr_result"] is not None)
            
            print(f"With plate detected: {with_plates}")
            print(f"With OCR result: {with_ocr}")
            
            # Show sample results
            print(f"\nSample Detections (first 3):")
            for i, result in enumerate(results[:3]):
                print(f"\n  Detection {i+1}:")
                print(f"    Frame: {result['frame_index']}")
                print(f"    Timestamp: {result['timestamp_ms']}ms")
                print(f"    Vehicle confidence: {result['vehicle_confidence']:.2f}")
                
                if result['plate_bbox']:
                    print(f"    Plate detected: {result['plate_method']}")
                    print(f"    Plate confidence: {result['plate_confidence']:.2f}")
                
                if result['ocr_result']:
                    ocr = result['ocr_result']
                    print(f"    OCR final: {ocr['final_text']}")
                    print(f"    OCR engine: {ocr['final_engine']}")
                    print(f"    Format valid: {ocr['format_valid']}")
                    print(f"    Needs review: {ocr['needs_review']}")
                    if ocr['paddleocr_text']:
                        print(f"    PaddleOCR: '{ocr['paddleocr_text']}' (conf: {ocr['paddleocr_conf']:.2f})")
                    if ocr['easyocr_text']:
                        print(f"    EasyOCR: '{ocr['easyocr_text']}' (conf: {ocr['easyocr_conf']:.2f})")
        
        # Save results
        output_file = "demo_results.json"
        with open(output_file, 'w') as f:
            json.dump({
                "video": test_video,
                "capabilities": capabilities,
                "total_detections": len(results),
                "sample_results": results[:5]  # First 5 for inspection
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {output_file}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Pipeline processing failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
