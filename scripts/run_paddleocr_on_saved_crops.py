"""
Test PaddleOCR on saved plate crops from Gemini synthetic video.
Compares performance with EasyOCR results.
"""

import os
import json
from pathlib import Path
from paddleocr import PaddleOCR
import time

def main():
    # Initialize PaddleOCR (English model)
    print("Initializing PaddleOCR...")
    ocr = PaddleOCR(use_textline_orientation=True, lang='en')
    
    # Path to saved crops
    crops_dir = Path("data/gemini_anpr_test")
    
    # Get all plate crop images
    crop_files = sorted(crops_dir.glob("plate_*.png"))
    
    if not crop_files:
        print(f"No plate crops found in {crops_dir}")
        return
    
    print(f"\nFound {len(crop_files)} plate crops")
    print("Running PaddleOCR on all crops...\n")
    
    results = []
    successful_reads = 0
    start_time = time.time()
    
    for i, crop_path in enumerate(crop_files, 1):
        try:
            # Run OCR
            result = ocr.ocr(str(crop_path), cls=True)
            
            # Extract text and confidence
            if result and result[0]:
                # PaddleOCR returns list of [bbox, (text, confidence)] pairs
                texts = []
                confidences = []
                for line in result[0]:
                    text, conf = line[1]
                    texts.append(text)
                    confidences.append(conf)
                
                extracted_text = ' '.join(texts) if texts else ""
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
                
                if extracted_text:
                    successful_reads += 1
                    print(f"[{i}/{len(crop_files)}] {crop_path.name}: '{extracted_text}' (conf: {avg_confidence:.2f})")
                else:
                    print(f"[{i}/{len(crop_files)}] {crop_path.name}: No text detected")
            else:
                extracted_text = ""
                avg_confidence = 0.0
                print(f"[{i}/{len(crop_files)}] {crop_path.name}: No text detected")
            
            results.append({
                "filename": crop_path.name,
                "text": extracted_text,
                "confidence": avg_confidence,
                "raw_result": str(result)  # Store raw result for debugging
            })
            
        except Exception as e:
            print(f"[{i}/{len(crop_files)}] {crop_path.name}: Error - {e}")
            results.append({
                "filename": crop_path.name,
                "text": "",
                "confidence": 0.0,
                "error": str(e)
            })
    
    elapsed_time = time.time() - start_time
    
    # Save results
    output_path = crops_dir / "paddleocr_results.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    # Print summary
    print(f"\n{'='*60}")
    print("PaddleOCR Test Results Summary")
    print(f"{'='*60}")
    print(f"Total crops processed: {len(crop_files)}")
    print(f"Successful text extractions: {successful_reads}")
    print(f"Success rate: {successful_reads/len(crop_files)*100:.1f}%")
    print(f"Processing time: {elapsed_time:.1f}s ({elapsed_time/len(crop_files):.2f}s per crop)")
    print(f"\nResults saved to: {output_path}")
    
    # Compare with EasyOCR if available
    easyocr_path = crops_dir / "ocr_results.json"
    if easyocr_path.exists():
        with open(easyocr_path, 'r') as f:
            easyocr_results = json.load(f)
        easyocr_success = sum(1 for r in easyocr_results if r.get('text', ''))
        print(f"\nComparison with EasyOCR:")
        print(f"  EasyOCR successful reads: {easyocr_success}/{len(easyocr_results)} ({easyocr_success/len(easyocr_results)*100:.1f}%)")
        print(f"  PaddleOCR successful reads: {successful_reads}/{len(crop_files)} ({successful_reads/len(crop_files)*100:.1f}%)")

if __name__ == "__main__":
    main()
