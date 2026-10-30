"""
Test integrated OCR preprocessing on real plate crops from video.

Compares original vs preprocessed OCR results on existing detected plates.
Does not claim accuracy without verified ground truth.
"""
import argparse
import json
import logging
from pathlib import Path
import sys

import cv2
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ocr_engine import HybridOCREngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_on_real_crops(crops_dir: Path, output_file: Path, sample_size: int = None):
    """
    Test OCR with and without preprocessing on real detected crops.
    
    Args:
        crops_dir: Directory containing plate crop images
        output_file: Path to save results JSON
        sample_size: Optional limit on number of crops to test
    """
    logger.info(f"Testing on real crops from: {crops_dir}")
    
    # Find all plate crops
    crop_files = sorted(list(crops_dir.glob("plate_*.jpg")))
    
    if not crop_files:
        logger.error(f"No plate crops found in {crops_dir}")
        return
    
    if sample_size:
        crop_files = crop_files[:sample_size]
    
    logger.info(f"Found {len(crop_files)} plate crops")
    
    # Initialize OCR engines
    logger.info("Initializing OCR engine WITHOUT preprocessing...")
    engine_no_preproc = HybridOCREngine(use_gpu=False, enable_preprocessing=False)
    
    logger.info("Initializing OCR engine WITH preprocessing...")
    engine_with_preproc = HybridOCREngine(use_gpu=False, enable_preprocessing=True)
    
    results = {
        'metadata': {
            'crops_dir': str(crops_dir),
            'total_crops': len(crop_files),
            'sample_tested': len(crop_files)
        },
        'crop_results': []
    }
    
    readable_count_no_preproc = 0
    readable_count_with_preproc = 0
    empty_count_no_preproc = 0
    empty_count_with_preproc = 0
    
    for crop_file in crop_files:
        # Load crop
        crop = cv2.imread(str(crop_file))
        if crop is None:
            logger.warning(f"Failed to load: {crop_file.name}")
            continue
        
        h, w = crop.shape[:2]
        
        # Run OCR without preprocessing
        result_no_preproc = engine_no_preproc.recognize(crop, preserve_original=False)
        
        # Run OCR with preprocessing
        result_with_preproc = engine_with_preproc.recognize(crop, preserve_original=False)
        
        # Determine if output is readable (not empty/unreadable)
        text_no_preproc = result_no_preproc.get('final_text', 'UNREADABLE')
        text_with_preproc = result_with_preproc.get('final_text', 'UNREADABLE')
        
        is_readable_no_preproc = (text_no_preproc not in ['', 'UNREADABLE'] and 
                                   len(text_no_preproc.strip()) > 0)
        is_readable_with_preproc = (text_with_preproc not in ['', 'UNREADABLE'] and 
                                     len(text_with_preproc.strip()) > 0)
        
        if is_readable_no_preproc:
            readable_count_no_preproc += 1
        else:
            empty_count_no_preproc += 1
        
        if is_readable_with_preproc:
            readable_count_with_preproc += 1
        else:
            empty_count_with_preproc += 1
        
        # Record result
        crop_result = {
            'filename': crop_file.name,
            'dimensions': {'width': w, 'height': h, 'area': w * h},
            'without_preprocessing': {
                'text': text_no_preproc,
                'confidence': result_no_preproc.get('easyocr_conf', 0.0),
                'readable': is_readable_no_preproc,
                'needs_review': result_no_preproc.get('needs_review', True)
            },
            'with_preprocessing': {
                'text': text_with_preproc,
                'confidence': result_with_preproc.get('easyocr_conf', 0.0),
                'readable': is_readable_with_preproc,
                'needs_review': result_with_preproc.get('needs_review', True),
                'preprocessing_applied': result_with_preproc.get('preprocessing', {}).get('preprocessed', False),
                'preprocessing_method': result_with_preproc.get('preprocessing', {}).get('method'),
                'likely_unreadable': result_with_preproc.get('preprocessing', {}).get('likely_unreadable', False)
            },
            'texts_match': (text_no_preproc == text_with_preproc),
            'improvement': (is_readable_with_preproc and not is_readable_no_preproc)
        }
        
        results['crop_results'].append(crop_result)
    
    # Calculate summary statistics
    results['summary'] = {
        'without_preprocessing': {
            'readable_count': readable_count_no_preproc,
            'empty_count': empty_count_no_preproc,
            'readable_rate': readable_count_no_preproc / len(crop_files) if crop_files else 0
        },
        'with_preprocessing': {
            'readable_count': readable_count_with_preproc,
            'empty_count': empty_count_with_preproc,
            'readable_rate': readable_count_with_preproc / len(crop_files) if crop_files else 0
        },
        'improvement': {
            'additional_readable': readable_count_with_preproc - readable_count_no_preproc,
            'improvement_rate': (readable_count_with_preproc - readable_count_no_preproc) / len(crop_files) if crop_files else 0
        }
    }
    
    # Save results
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nResults saved to {output_file}")
    
    # Print summary
    print("\n" + "="*100)
    print("OCR PREPROCESSING TEST ON REAL VIDEO CROPS")
    print("="*100)
    print(f"\nDataset: {crops_dir}")
    print(f"Total crops tested: {len(crop_files)}")
    print("\n" + "-"*100)
    print(f"{'Metric':<50} {'Without Preprocessing':<25} {'With Preprocessing':<25}")
    print("-"*100)
    print(f"{'Readable output count':<50} {readable_count_no_preproc:<25} {readable_count_with_preproc:<25}")
    print(f"{'Empty/UNREADABLE count':<50} {empty_count_no_preproc:<25} {empty_count_with_preproc:<25}")
    rate_without = results['summary']['without_preprocessing']['readable_rate']
    rate_with = results['summary']['with_preprocessing']['readable_rate']
    print(f"{'Readable rate':<50} {rate_without:<24.1%} {rate_with:.1%}")
    print("="*100)
    
    improvement = results['summary']['improvement']['additional_readable']
    print(f"\nImprovement: {improvement:+d} additional readable outputs")
    
    if improvement > 0:
        print(f"Preprocessing enabled reading of {improvement} previously unreadable crops")
    elif improvement == 0:
        print("No improvement observed (crops may be too small or degraded)")
    else:
        print(f"WARNING: {abs(improvement)} fewer readable outputs with preprocessing")
    
    print("\n" + "="*100)
    print("IMPORTANT: Without verified ground truth, these are READABLE OUTPUT COUNTS only.")
    print("Text correctness cannot be determined without manual annotation.")
    print("="*100)
    
    # Show sample outputs
    print("\nSample outputs (first 10 crops):")
    print("-"*100)
    for i, result in enumerate(results['crop_results'][:10]):
        print(f"\n{result['filename']} ({result['dimensions']['width']}×{result['dimensions']['height']}px):")
        print(f"  Without preprocessing: '{result['without_preprocessing']['text']}'")
        print(f"  With preprocessing:    '{result['with_preprocessing']['text']}'")
        if result['with_preprocessing']['preprocessing_applied']:
            print(f"  Preprocessing:         Applied ({result['with_preprocessing']['preprocessing_method']})")
        if result['with_preprocessing']['likely_unreadable']:
            print(f"  Warning:              Crop flagged as likely unreadable")


def main():
    parser = argparse.ArgumentParser(description='Test OCR preprocessing on real crops')
    parser.add_argument('--crops-dir', type=str, 
                       default='data/gemini_anpr_test',
                       help='Directory containing plate crops')
    parser.add_argument('--output', type=str,
                       default='ocr_benchmark_results/real_crops_comparison.json',
                       help='Output JSON file')
    parser.add_argument('--sample-size', type=int, default=None,
                       help='Optional limit on number of crops to test')
    
    args = parser.parse_args()
    
    crops_dir = Path(args.crops_dir)
    output_file = Path(args.output)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    test_on_real_crops(crops_dir, output_file, args.sample_size)


if __name__ == '__main__':
    main()

