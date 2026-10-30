"""
Run EasyOCR on all saved plate crop images from gemini video test.

This script:
1. Loads all plate crop images from data/gemini_anpr_test/
2. Runs EasyOCR on each image
3. Preserves raw OCR output and confidence scores
4. Saves results to JSON file
5. Reports statistics on text extraction success

Reports actual results without fabrication.
"""
import json
import cv2
from pathlib import Path
from datetime import datetime
import sys

# Try to import EasyOCR
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("[ERROR] EasyOCR not installed")
    print("Install with: pip install easyocr")
    sys.exit(1)

def run_ocr_on_crops(input_dir: str = "data/gemini_anpr_test", output_file: str = "data/gemini_anpr_test/ocr_results.json"):
    """
    Run EasyOCR on all plate crop images.
    
    Args:
        input_dir: Directory containing plate crop images
        output_file: Path to save OCR results JSON
    """
    print("="*80)
    print("EASYOCR TEXT RECOGNITION ON SAVED PLATE CROPS")
    print("="*80)
    print(f"Input directory: {input_dir}")
    print(f"Output file: {output_file}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Initialize EasyOCR
    print("Initializing EasyOCR...")
    print("Note: First run may take time to download language models")
    try:
        reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        print("[OK] EasyOCR initialized (CPU mode)")
    except Exception as e:
        print(f"[ERROR] Failed to initialize EasyOCR: {e}")
        return
    print()
    
    # Find all plate crop files
    input_path = Path(input_dir)
    plate_files = sorted(input_path.glob("plate_f*.jpg"))
    
    if not plate_files:
        print(f"[ERROR] No plate crop files found in {input_dir}")
        return
    
    print(f"Found {len(plate_files)} plate crop images")
    print()
    
    # Process each crop
    results = []
    successful_reads = 0
    empty_reads = 0
    errors = 0
    
    print("Processing crops...")
    for i, plate_file in enumerate(plate_files):
        # Read image
        try:
            img = cv2.imread(str(plate_file))
            
            if img is None:
                print(f"[{i+1}/{len(plate_files)}] {plate_file.name}: ERROR - Cannot read image")
                errors += 1
                results.append({
                    "file": plate_file.name,
                    "status": "error",
                    "error": "Cannot read image"
                })
                continue
            
            # Run OCR
            ocr_result = reader.readtext(img)
            
            # Extract text and confidence
            if ocr_result:
                texts = [detection[1] for detection in ocr_result]
                confidences = [float(detection[2]) for detection in ocr_result]
                combined_text = " ".join(texts)
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                results.append({
                    "file": plate_file.name,
                    "status": "success",
                    "text": combined_text,
                    "confidence": avg_confidence,
                    "raw_detections": [
                        {
                            "text": det[1],
                            "confidence": float(det[2]),
                            "bbox": [[float(x), float(y)] for x, y in det[0]]
                        } for det in ocr_result
                    ],
                    "num_detections": len(ocr_result)
                })
                
                successful_reads += 1
                
                # Print sample results (first 10 and every 20th)
                if i < 10 or (i+1) % 20 == 0:
                    print(f"[{i+1}/{len(plate_files)}] {plate_file.name}: '{combined_text}' (conf: {avg_confidence:.3f})")
            else:
                results.append({
                    "file": plate_file.name,
                    "status": "empty",
                    "text": "",
                    "confidence": 0.0,
                    "raw_detections": [],
                    "num_detections": 0
                })
                empty_reads += 1
                
                if i < 10:
                    print(f"[{i+1}/{len(plate_files)}] {plate_file.name}: (no text detected)")
                    
        except Exception as e:
            print(f"[{i+1}/{len(plate_files)}] {plate_file.name}: ERROR - {e}")
            errors += 1
            results.append({
                "file": plate_file.name,
                "status": "error",
                "error": str(e)
            })
    
    print()
    print("="*80)
    print("OCR PROCESSING COMPLETE")
    print("="*80)
    print(f"Total crops processed:   {len(plate_files)}")
    print(f"Successful reads:        {successful_reads} ({successful_reads/len(plate_files)*100:.1f}%)")
    print(f"Empty reads (no text):   {empty_reads} ({empty_reads/len(plate_files)*100:.1f}%)")
    print(f"Errors:                  {errors}")
    print()
    
    # Save results to JSON
    output_data = {
        "timestamp": datetime.now().isoformat(),
        "input_directory": input_dir,
        "ocr_engine": "EasyOCR",
        "language": "en",
        "gpu_mode": False,
        "summary": {
            "total_crops": len(plate_files),
            "successful_reads": successful_reads,
            "empty_reads": empty_reads,
            "errors": errors,
            "success_rate": f"{successful_reads/len(plate_files)*100:.1f}%"
        },
        "results": results
    }
    
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    print(f"Results saved to: {output_file}")
    print()
    
    # Show sample successful reads
    successful_results = [r for r in results if r.get("status") == "success" and r.get("text")]
    
    if successful_results:
        print("Sample OCR results (first 10 successful reads):")
        for i, result in enumerate(successful_results[:10], 1):
            text = result["text"]
            conf = result["confidence"]
            file = result["file"]
            print(f"  {i}. {file}: '{text}' (confidence: {conf:.3f})")
        print()
    else:
        print("[!] No text was successfully extracted from any crops")
        print()
    
    # Important notes
    print("="*80)
    print("IMPORTANT NOTES")
    print("="*80)
    print()
    print("1. Test video is AI-generated/synthetic")
    print("   - Registration numbers may be artificial or unreadable")
    print("   - OCR results may be gibberish or inconsistent")
    print("   - This tests OCR functionality, not accuracy")
    print()
    print("2. Success rate is TEXT DETECTION, not recognition accuracy")
    print("   - 'Successful read' = text extracted, not 'correct read'")
    print("   - Cannot measure accuracy without ground truth labels")
    print()
    print("3. Low success rate may indicate:")
    print("   - Plates too small/blurred in synthetic video")
    print("   - AI-generated text not recognizable as characters")
    print("   - OCR model trained on different plate styles")
    print()
    print("4. Next steps:")
    print("   - Manually inspect sample crops to verify visibility")
    print("   - Test on real CCTV footage with actual plates")
    print("   - Install PaddleOCR for dual-engine comparison")
    print()
    
    return {
        "total_crops": len(plate_files),
        "successful_reads": successful_reads,
        "success_rate": successful_reads/len(plate_files)*100 if plate_files else 0
    }

if __name__ == "__main__":
    import sys
    
    # Check if input directory exists
    input_dir = "data/gemini_anpr_test"
    if not Path(input_dir).exists():
        print(f"[ERROR] Input directory not found: {input_dir}")
        print("Expected plate crops in: data/gemini_anpr_test/plate_f*.jpg")
        sys.exit(1)
    
    # Run OCR
    stats = run_ocr_on_crops(input_dir)
    
    if stats:
        if stats["successful_reads"] > 0:
            print(f"\n[SUCCESS] OCR completed: {stats['successful_reads']}/{stats['total_crops']} crops had readable text ({stats['success_rate']:.1f}%)")
        else:
            print("\n[WARNING] OCR completed but NO text was extracted from any crops")
            print("This may be expected for synthetic/AI-generated plate images")
    else:
        print("\n[FAILURE] OCR processing failed")
        sys.exit(1)
