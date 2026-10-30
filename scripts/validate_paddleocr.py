"""
Validate PaddleOCR on synthetic test plates with known ground truth.

Measures exact-match accuracy, character-level accuracy, and processing time.
"""
import cv2
import json
import time
import sys
from pathlib import Path
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.plate_validator import normalize_plate_text


def calculate_character_accuracy(expected: str, actual: str) -> dict:
    """
    Calculate character-level accuracy using simple comparison.
    
    Args:
        expected: Ground truth text
        actual: OCR output text
    
    Returns:
        dict with character_accuracy, correct_chars, total_chars
    """
    # Normalize for comparison (uppercase, single spaces)
    expected_norm = normalize_plate_text(expected)
    actual_norm = normalize_plate_text(actual)
    
    # For character accuracy, remove spaces from both
    expected_chars = expected_norm.replace(" ", "")
    actual_chars = actual_norm.replace(" ", "")
    
    if not expected_chars:
        return {
            "character_accuracy": 0.0,
            "correct_chars": 0,
            "total_chars": 0
        }
    
    # Simple character-by-character comparison
    correct = 0
    total = len(expected_chars)
    
    for i in range(min(len(expected_chars), len(actual_chars))):
        if expected_chars[i] == actual_chars[i]:
            correct += 1
    
    accuracy = correct / total if total > 0 else 0.0
    
    return {
        "character_accuracy": accuracy,
        "correct_chars": correct,
        "total_chars": total
    }


def validate_paddleocr_on_dataset(
    test_dir: str = "data/ocr_test",
    ground_truth_file: str = "data/ocr_test/ground_truth.json"
) -> dict:
    """
    Validate PaddleOCR on synthetic test dataset.
    
    Args:
        test_dir: Directory containing test images
        ground_truth_file: Path to ground truth JSON
    
    Returns:
        Complete validation results or None if PaddleOCR unavailable
    """
    print("="*70)
    print("PaddleOCR Validation on Synthetic Test Dataset")
    print("="*70)
    print()
    
    # Load ground truth
    with open(ground_truth_file, 'r') as f:
        ground_truth = json.load(f)
    
    print(f"Loaded ground truth: {len(ground_truth)} images")
    
    # Initialize PaddleOCR
    print("Initializing PaddleOCR...")
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_textline_orientation=True, lang='en')
        print("✅ PaddleOCR initialized (CPU mode)\n")
    except ImportError:
        print("❌ PaddleOCR not installed!")
        print("   Install with: pip install paddleocr")
        return None
    except Exception as e:
        print("X PaddleOCR initialization failed: {}".format(e))
        print("   This may be due to model download issues or missing paddlepaddle.")
        print("   Check network connection and ensure paddlepaddle is installed.")
        return None
    
    # Process each image
    results = {}
    exact_matches = 0
    total_images = 0
    total_char_accuracy = 0.0
    total_processing_time = 0.0
    
    variant_stats = {}
    
    test_path = Path(test_dir)
    
    for filename, gt_data in ground_truth.items():
        image_path = test_path / filename
        
        if not image_path.exists():
            print(f"⚠️  Image not found: {filename}")
            continue
        
        expected_text = gt_data["registration_number"]
        variant_type = gt_data["variant_type"]
        
        # Run OCR with timing
        start_time = time.time()
        try:
            ocr_results = ocr.ocr(str(image_path), cls=True)
        except Exception as e:
            print(f"❌ Error processing {filename}: {e}")
            continue
        processing_time = time.time() - start_time
        
        # Extract text and confidence
        if ocr_results and ocr_results[0]:
            # Combine all detected text
            texts = []
            confidences = []
            for line in ocr_results[0]:
                text, conf = line[1]
                texts.append(text)
                confidences.append(conf)
            
            raw_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        else:
            raw_text = ""
            avg_confidence = 0.0
        
        # Normalize for comparison
        expected_normalized = normalize_plate_text(expected_text)
        actual_normalized = normalize_plate_text(raw_text)
        
        # Check exact match
        exact_match = (expected_normalized == actual_normalized)
        if exact_match:
            exact_matches += 1
        
        # Calculate character-level accuracy
        char_acc_data = calculate_character_accuracy(expected_text, raw_text)
        
        # Store results
        results[filename] = {
            "expected": expected_text,
            "expected_normalized": expected_normalized,
            "raw_ocr": raw_text,
            "ocr_normalized": actual_normalized,
            "confidence": float(avg_confidence),
            "exact_match": exact_match,
            "character_accuracy": char_acc_data["character_accuracy"],
            "correct_chars": char_acc_data["correct_chars"],
            "total_chars": char_acc_data["total_chars"],
            "processing_time_ms": processing_time * 1000,
            "variant_type": variant_type,
            "num_detections": len(ocr_results[0]) if ocr_results and ocr_results[0] else 0
        }
        
        # Update stats
        total_images += 1
        total_char_accuracy += char_acc_data["character_accuracy"]
        total_processing_time += processing_time
        
        # Track by variant
        if variant_type not in variant_stats:
            variant_stats[variant_type] = {
                "count": 0,
                "exact_matches": 0,
                "total_char_accuracy": 0.0
            }
        variant_stats[variant_type]["count"] += 1
        if exact_match:
            variant_stats[variant_type]["exact_matches"] += 1
        variant_stats[variant_type]["total_char_accuracy"] += char_acc_data["character_accuracy"]
        
        # Print progress every 25 images
        if total_images % 25 == 0:
            print(f"  Processed {total_images}/{len(ground_truth)} images...")
    
    print(f"\n✅ Processed {total_images} images\n")
    
    # Calculate overall metrics
    exact_match_accuracy = exact_matches / total_images if total_images > 0 else 0.0
    avg_char_accuracy = total_char_accuracy / total_images if total_images > 0 else 0.0
    avg_processing_time = total_processing_time / total_images if total_images > 0 else 0.0
    
    # Calculate per-variant accuracy
    for variant_type, stats in variant_stats.items():
        stats["exact_match_accuracy"] = stats["exact_matches"] / stats["count"]
        stats["avg_char_accuracy"] = stats["total_char_accuracy"] / stats["count"]
    
    # Create summary
    summary = {
        "engine": "PaddleOCR",
        "total_images": total_images,
        "exact_matches": exact_matches,
        "exact_match_accuracy": exact_match_accuracy,
        "average_character_accuracy": avg_char_accuracy,
        "average_processing_time_ms": avg_processing_time * 1000,
        "total_processing_time_sec": total_processing_time,
        "variant_statistics": variant_stats
    }
    
    # Combine into full results
    full_results = {
        "summary": summary,
        "per_image_results": results
    }
    
    # Save results
    output_file = test_path / "paddleocr_results.json"
    with open(output_file, 'w') as f:
        json.dump(full_results, f, indent=2)
    
    print(f"{'='*70}")
    print("Validation Results Summary")
    print(f"{'='*70}")
    print(f"Total images processed: {total_images}")
    print(f"Exact matches: {exact_matches}/{total_images} ({exact_match_accuracy*100:.1f}%)")
    print(f"Average character accuracy: {avg_char_accuracy*100:.1f}%")
    print(f"Average processing time: {avg_processing_time*1000:.1f}ms per image")
    print(f"\nPer-variant accuracy:")
    for variant_type, stats in sorted(variant_stats.items()):
        print(f"  {variant_type:15s}: {stats['exact_match_accuracy']*100:5.1f}% exact, "
              f"{stats['avg_char_accuracy']*100:5.1f}% char ({stats['count']} images)")
    
    print(f"\n✅ Results saved to: {output_file}")
    
    return full_results


def main():
    """Run PaddleOCR validation"""
    results = validate_paddleocr_on_dataset()
    
    if results:
        print("\n" + "="*70)
        print("PaddleOCR validation complete!")
        print("="*70)
        
        summary = results["summary"]
        
        # Show some example failures if any
        failures = [
            (filename, data) 
            for filename, data in results["per_image_results"].items() 
            if not data["exact_match"]
        ]
        
        if failures:
            print(f"\nExample failures (showing first 5 of {len(failures)}):")
            for filename, data in failures[:5]:
                print(f"  {filename}:")
                print(f"    Expected: '{data['expected']}'")
                print(f"    Got:      '{data['raw_ocr']}'")
                print(f"    Conf:     {data['confidence']:.2f}")
                print(f"    Char acc: {data['character_accuracy']*100:.1f}%")
    else:
        print("X PaddleOCR validation skipped (engine unavailable)")
        print("   EasyOCR results are still valid.")


if __name__ == "__main__":
    main()
