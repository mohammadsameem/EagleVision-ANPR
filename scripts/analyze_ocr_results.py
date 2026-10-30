"""Analyze OCR results from gemini video ANPR test."""
import json
from pathlib import Path
from collections import Counter

def analyze_ocr_results():
    """Analyze OCR results and print summary."""
    results_file = Path("data/gemini_anpr_test/anpr_results.json")
    
    if not results_file.exists():
        print(f"[ERROR] Results file not found: {results_file}")
        return
    
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    print("="*70)
    print("OCR RESULTS ANALYSIS")
    print("="*70)
    print()
    
    # Extract OCR results
    detections = data['detections']
    detections_with_ocr = [d for d in detections if 'ocr_results' in d and d['ocr_results']]
    
    print(f"Total detections: {len(detections)}")
    print(f"Detections with OCR attempted: {len(detections_with_ocr)}")
    print()
    
    # Analyze EasyOCR results
    easyocr_success = 0
    easyocr_texts = []
    
    for det in detections_with_ocr:
        if 'easyocr' in det['ocr_results']:
            ocr_data = det['ocr_results']['easyocr']
            if 'text' in ocr_data and 'error' not in ocr_data:
                easyocr_success += 1
                text = ocr_data['text'].strip()
                conf = ocr_data.get('confidence', 0)
                if text:
                    easyocr_texts.append((text, conf))
    
    print(f"EasyOCR:")
    print(f"  Available: {data['models']['easyocr_available']}")
    print(f"  Successful reads: {easyocr_success}")
    print(f"  Texts extracted: {len(easyocr_texts)}")
    print()
    
    if easyocr_texts:
        print("Sample EasyOCR results (first 10):")
        for i, (text, conf) in enumerate(easyocr_texts[:10], 1):
            print(f"  {i}. '{text}' (confidence: {conf:.3f})")
        print()
        
        # Analyze text patterns
        all_texts = [t[0] for t in easyocr_texts]
        text_counts = Counter(all_texts)
        most_common = text_counts.most_common(5)
        
        print("Most common OCR readings:")
        for text, count in most_common:
            print(f"  '{text}': {count} times")
        print()
        
        # Average confidence
        avg_conf = sum(t[1] for t in easyocr_texts) / len(easyocr_texts)
        print(f"Average confidence: {avg_conf:.3f}")
        print()
    
    # Analyze PaddleOCR results
    paddleocr_success = 0
    paddleocr_texts = []
    
    for det in detections_with_ocr:
        if 'paddleocr' in det['ocr_results']:
            ocr_data = det['ocr_results']['paddleocr']
            if 'text' in ocr_data and 'error' not in ocr_data:
                paddleocr_success += 1
                text = ocr_data['text'].strip()
                conf = ocr_data.get('confidence', 0)
                if text:
                    paddleocr_texts.append((text, conf))
    
    print(f"PaddleOCR:")
    print(f"  Available: {data['models']['paddleocr_available']}")
    print(f"  Successful reads: {paddleocr_success}")
    print(f"  Texts extracted: {len(paddleocr_texts)}")
    print()
    
    # Sample plate crop filenames
    print("Sample plate crop files:")
    crop_files = [d['plate_crop_file'] for d in detections[:10] if 'plate_crop_file' in d]
    for i, fname in enumerate(crop_files[:5], 1):
        print(f"  {i}. {fname}")
    print()
    
    print("="*70)
    print()
    
    # Validation notes
    print("VALIDATION NOTES:")
    print()
    print("1. This is AI-generated/synthetic video")
    print("   - Registration numbers may be artificial")
    print("   - Text may be inconsistent across frames")
    print("   - Do not treat as ground truth")
    print()
    print("2. OCR results show actual model output")
    print("   - No manual inference of characters")
    print("   - No fabrication of results")
    print("   - Low-confidence or incorrect reads preserved")
    print()
    print("3. Detection vs Recognition distinction:")
    print(f"   - Plates detected: {len(detections)}")
    print(f"   - OCR attempted: {len(detections_with_ocr)}")
    print(f"   - Successful reads: {easyocr_success}")
    print("   - Detection ≠ Recognition")
    print()

if __name__ == "__main__":
    analyze_ocr_results()
