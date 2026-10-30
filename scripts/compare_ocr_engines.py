"""
Compare EasyOCR and PaddleOCR results on identical test images.

Analyzes agreement, disagreement, confidence differences, and per-variant performance.
"""
import json
from pathlib import Path


def load_results(results_path: Path) -> dict:
    """Load OCR results JSON"""
    if not results_path.exists():
        return None
    
    with open(results_path, 'r') as f:
        return json.load(f)


def compare_ocr_engines(
    easyocr_file: str = "data/ocr_test/easyocr_results.json",
    paddleocr_file: str = "data/ocr_test/paddleocr_results.json"
):
    """
    Compare EasyOCR and PaddleOCR results.
    
    Args:
        easyocr_file: Path to EasyOCR results JSON
        paddleocr_file: Path to PaddleOCR results JSON
    """
    print("="*70)
    print("OCR Engine Comparison")
    print("="*70)
    print()
    
    # Load results
    easyocr_data = load_results(Path(easyocr_file))
    paddleocr_data = load_results(Path(paddleocr_file))
    
    if not easyocr_data:
        print("X EasyOCR results not found!")
        print("   Run: python scripts/validate_easyocr.py")
        return
    
    if not paddleocr_data:
        print("! PaddleOCR results not found (engine may be unavailable)")
        print("  Showing EasyOCR results only\n")
        
        # Show EasyOCR summary
        easy_summary = easyocr_data["summary"]
        print("EasyOCR Results:")
        print(f"  Exact match accuracy: {easy_summary['exact_match_accuracy']*100:.1f}%")
        print(f"  Character accuracy: {easy_summary['average_character_accuracy']*100:.1f}%")
        print(f"  Processing time: {easy_summary['average_processing_time_ms']:.1f}ms/image")
        print()
        print("Recommendation: Install paddlepaddle to enable dual-engine comparison")
        print("  Installation: pip install paddlepaddle (or paddlepaddle-gpu)")
        return
    
    # Both engines available - perform comparison
    easy_summary = easyocr_data["summary"]
    paddle_summary = paddleocr_data["summary"]
    easy_results = easyocr_data["per_image_results"]
    paddle_results = paddleocr_data["per_image_results"]
    
    print("Engine Performance Comparison\n")
    
    # Overall accuracy
    print("Overall Accuracy:")
    print(f"  {'Engine':<15} {'Exact Match':<15} {'Char Accuracy':<20} {'Avg Time':<15}")
    print(f"  {'-'*65}")
    print(f"  {'EasyOCR':<15} {easy_summary['exact_match_accuracy']*100:6.1f}%        "
          f"{easy_summary['average_character_accuracy']*100:6.1f}%            "
          f"{easy_summary['average_processing_time_ms']:6.1f}ms")
    print(f"  {'PaddleOCR':<15} {paddle_summary['exact_match_accuracy']*100:6.1f}%        "
          f"{paddle_summary['average_character_accuracy']*100:6.1f}%            "
          f"{paddle_summary['average_processing_time_ms']:6.1f}ms")
    print()
    
    # Agreement analysis
    agreements = 0
    disagreements = 0
    both_correct = 0
    easy_correct_only = 0
    paddle_correct_only = 0
    both_incorrect = 0
    
    disagreement_examples = []
    
    for filename in easy_results:
        if filename not in paddle_results:
            continue
        
        easy_result = easy_results[filename]
        paddle_result = paddle_results[filename]
        
        easy_match = easy_result["exact_match"]
        paddle_match = paddle_result["exact_match"]
        
        easy_text = easy_result["ocr_normalized"]
        paddle_text = paddle_result["ocr_normalized"]
        
        # Check agreement
        if easy_text == paddle_text:
            agreements += 1
        else:
            disagreements += 1
            if len(disagreement_examples) < 5:
                disagreement_examples.append({
                    "filename": filename,
                    "expected": easy_result["expected"],
                    "easyocr": easy_text,
                    "paddleocr": paddle_text,
                    "easy_conf": easy_result["confidence"],
                    "paddle_conf": paddle_result["confidence"]
                })
        
        # Track correctness
        if easy_match and paddle_match:
            both_correct += 1
        elif easy_match and not paddle_match:
            easy_correct_only += 1
        elif not easy_match and paddle_match:
            paddle_correct_only += 1
        else:
            both_incorrect += 1
    
    total_compared = agreements + disagreements
    
    print("Agreement Analysis:")
    print(f"  Images compared: {total_compared}")
    print(f"  Agreements: {agreements} ({agreements/total_compared*100:.1f}%)")
    print(f"  Disagreements: {disagreements} ({disagreements/total_compared*100:.1f}%)")
    print()
    
    print("Correctness Analysis:")
    print(f"  Both correct: {both_correct} ({both_correct/total_compared*100:.1f}%)")
    print(f"  EasyOCR only correct: {easy_correct_only} ({easy_correct_only/total_compared*100:.1f}%)")
    print(f"  PaddleOCR only correct: {paddle_correct_only} ({paddle_correct_only/total_compared*100:.1f}%)")
    print(f"  Both incorrect: {both_incorrect} ({both_incorrect/total_compared*100:.1f}%)")
    print()
    
    # Show example disagreements
    if disagreement_examples:
        print(f"Example Disagreements (showing {len(disagreement_examples)}):")
        for ex in disagreement_examples:
            print(f"  {ex['filename']}:")
            print(f"    Expected:   '{ex['expected']}'")
            print(f"    EasyOCR:    '{ex['easyocr']}' (conf: {ex['easy_conf']:.2f})")
            print(f"    PaddleOCR:  '{ex['paddleocr']}' (conf: {ex['paddle_conf']:.2f})")
        print()
    
    # Per-variant comparison
    print("Per-Variant Performance:")
    print(f"  {'Variant':<15} {'EasyOCR':<15} {'PaddleOCR':<15} {'Difference'}")
    print(f"  {'-'*60}")
    
    easy_variants = easy_summary["variant_statistics"]
    paddle_variants = paddle_summary["variant_statistics"]
    
    for variant in sorted(easy_variants.keys()):
        easy_acc = easy_variants[variant]["exact_match_accuracy"]
        paddle_acc = paddle_variants[variant]["exact_match_accuracy"]
        diff = paddle_acc - easy_acc
        diff_sign = "+" if diff > 0 else ""
        
        print(f"  {variant:<15} {easy_acc*100:5.1f}%         {paddle_acc*100:5.1f}%         "
              f"{diff_sign}{diff*100:5.1f}%")
    
    print()
    print("="*70)
    print("Comparison complete!")
    print("="*70)
    
    # Recommendations
    print("\nRecommendations:")
    if disagreements > 0:
        print(f"  - {disagreements} disagreements found - these should be flagged for human review")
    if easy_correct_only > paddle_correct_only:
        print(f"  - EasyOCR performed better ({easy_correct_only} vs {paddle_correct_only} unique correct)")
    elif paddle_correct_only > easy_correct_only:
        print(f"  - PaddleOCR performed better ({paddle_correct_only} vs {easy_correct_only} unique correct)")
    else:
        print(f"  - Both engines performed similarly")
    
    print("\nNote: Confidence scores from different engines are not directly comparable.")


def main():
    """Run OCR engine comparison"""
    compare_ocr_engines()


if __name__ == "__main__":
    main()
