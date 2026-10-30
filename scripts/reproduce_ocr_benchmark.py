"""
Reproduce OCR preprocessing benchmark with integrated engine.

Compares original OCR path vs preprocessing-enabled path using identical
source images and ground truth labels. Measures actual accuracy improvement.
"""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List
import time
from datetime import datetime
import sys

import cv2
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ocr_engine import HybridOCREngine
from scripts.benchmark_ocr_preprocessing import (
    calculate_levenshtein_distance,
    calculate_character_accuracy,
    normalize_text,
    downsample_image
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntegratedOCRBenchmark:
    """Benchmark integrated OCR engine with and without preprocessing."""
    
    def __init__(self, ground_truth_file: Path, images_dir: Path):
        """
        Initialize benchmark.
        
        Args:
            ground_truth_file: Path to ground truth JSON
            images_dir: Directory containing synthetic plates
        """
        self.images_dir = images_dir
        
        # Load ground truth
        with open(ground_truth_file, 'r') as f:
            self.ground_truth = json.load(f)
        
        logger.info(f"Loaded {len(self.ground_truth)} ground truth entries")
    
    def test_configuration(
        self,
        test_name: str,
        description: str,
        downsample_size: tuple = None,
        enable_preprocessing: bool = True,
        sample_size: int = 50
    ) -> Dict:
        """
        Test a specific configuration.
        
        Args:
            test_name: Name of test
            description: Description of test
            downsample_size: Optional (width, height) to downsample to, or None for original
            enable_preprocessing: Whether to enable OCR preprocessing
            sample_size: Number of images to test
        
        Returns:
            Results dict
        """
        logger.info(f"Testing: {test_name}")
        
        # Initialize OCR engine
        engine = HybridOCREngine(
            use_gpu=False,
            enable_preprocessing=enable_preprocessing
        )
        
        results = {
            'test_name': test_name,
            'description': description,
            'downsample_size': downsample_size,
            'preprocessing_enabled': enable_preprocessing,
            'images_tested': [],
            'summary': {
                'total_images': 0,
                'exact_matches': 0,
                'empty_outputs': 0,
                'total_processing_time': 0.0,
                'preprocessing_applied_count': 0
            },
            'character_accuracies': [],
            'confidences': []
        }
        
        # Test only clean variants
        test_files = [f for f in self.ground_truth.keys() if '_clean.png' in f]
        
        if sample_size and sample_size < len(test_files):
            test_files = test_files[:sample_size]
        
        for filename in test_files:
            image_path = self.images_dir / filename
            
            if not image_path.exists():
                logger.warning(f"Image not found: {filename}")
                continue
            
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            
            # Apply downsampling if specified
            if downsample_size:
                image = downsample_image(image, downsample_size)
            
            # Get ground truth
            gt_data = self.ground_truth[filename]
            gt_text = gt_data['registration_number']
            
            # Run OCR
            start_time = time.time()
            ocr_result = engine.recognize(image, confidence_threshold=0.70)
            proc_time = time.time() - start_time
            
            # Extract text and confidence (prefer final_text over engine-specific)
            ocr_text = ocr_result.get('final_text', 'UNREADABLE')
            
            # Get confidence from whichever engine was used
            if ocr_result['final_engine'] == 'easyocr':
                confidence = ocr_result.get('easyocr_conf', 0.0)
            elif ocr_result['final_engine'] == 'paddleocr':
                confidence = ocr_result.get('paddleocr_conf', 0.0)
            else:
                confidence = 0.0
            
            # Normalize for comparison
            gt_normalized = normalize_text(gt_text)
            ocr_normalized = normalize_text(ocr_text)
            
            # Calculate metrics
            exact_match = (gt_normalized == ocr_normalized)
            char_accuracy = calculate_character_accuracy(ocr_normalized, gt_normalized)
            
            # Track preprocessing
            preprocessing_applied = ocr_result.get('preprocessing', {}).get('preprocessed', False)
            
            # Record results
            result_entry = {
                'filename': filename,
                'ground_truth': gt_text,
                'ocr_text': ocr_text,
                'ocr_normalized': ocr_normalized,
                'confidence': confidence,
                'processing_time': proc_time,
                'exact_match': exact_match,
                'character_accuracy': char_accuracy,
                'empty_output': (ocr_text == "" or ocr_text == "UNREADABLE"),
                'preprocessing': ocr_result.get('preprocessing', {})
            }
            
            results['images_tested'].append(result_entry)
            
            # Update summary
            results['summary']['total_images'] += 1
            if exact_match:
                results['summary']['exact_matches'] += 1
            if ocr_text == "" or ocr_text == "UNREADABLE":
                results['summary']['empty_outputs'] += 1
            if preprocessing_applied:
                results['summary']['preprocessing_applied_count'] += 1
            results['summary']['total_processing_time'] += proc_time
            results['character_accuracies'].append(char_accuracy)
            results['confidences'].append(confidence)
        
        # Calculate summary statistics
        if results['summary']['total_images'] > 0:
            results['summary']['exact_match_rate'] = (
                results['summary']['exact_matches'] / results['summary']['total_images']
            )
            results['summary']['empty_output_rate'] = (
                results['summary']['empty_outputs'] / results['summary']['total_images']
            )
            results['summary']['mean_character_accuracy'] = (
                sum(results['character_accuracies']) / len(results['character_accuracies'])
            )
            results['summary']['mean_confidence'] = (
                sum(results['confidences']) / len(results['confidences']) if results['confidences'] else 0.0
            )
            results['summary']['avg_processing_time'] = (
                results['summary']['total_processing_time'] / results['summary']['total_images']
            )
        
        logger.info(
            f"{test_name}: {results['summary']['exact_match_rate']:.1%} exact "
            f"({results['summary']['exact_matches']}/{results['summary']['total_images']}), "
            f"{results['summary']['mean_character_accuracy']:.1f}% char accuracy"
        )
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Reproduce OCR preprocessing benchmark')
    parser.add_argument('--images-dir', type=str, default='data/ocr_test',
                       help='Directory containing synthetic plates')
    parser.add_argument('--ground-truth', type=str, default='data/ocr_test/ground_truth.json',
                       help='Path to ground truth JSON')
    parser.add_argument('--output-dir', type=str, default='ocr_benchmark_results',
                       help='Directory to save results')
    parser.add_argument('--sample-size', type=int, default=25,
                       help='Number of images to test per condition')
    
    args = parser.parse_args()
    
    images_dir = Path(args.images_dir)
    gt_file = Path(args.ground_truth)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize benchmark
    benchmark = IntegratedOCRBenchmark(gt_file, images_dir)
    
    # Run tests
    all_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'images_dir': str(images_dir),
            'ground_truth_file': str(gt_file),
            'sample_size': args.sample_size,
            'engine': 'HybridOCREngine (EasyOCR)',
            'description': 'Integrated OCR engine with configurable preprocessing'
        },
        'tests': []
    }
    
    # Test 1: Baseline - Original size, no preprocessing
    baseline = benchmark.test_configuration(
        test_name='baseline_original_no_preproc',
        description='Original 440×110 plates, preprocessing disabled',
        downsample_size=None,
        enable_preprocessing=False,
        sample_size=args.sample_size
    )
    all_results['tests'].append(baseline)
    
    # Test 2: Baseline - Original size, with preprocessing (should not trigger)
    baseline_with_preproc = benchmark.test_configuration(
        test_name='baseline_original_with_preproc',
        description='Original 440×110 plates, preprocessing enabled (but not triggered)',
        downsample_size=None,
        enable_preprocessing=True,
        sample_size=args.sample_size
    )
    all_results['tests'].append(baseline_with_preproc)
    
    # Test 3: Downsampled 80×20, no preprocessing
    down_80x20_no_preproc = benchmark.test_configuration(
        test_name='downsampled_80x20_no_preproc',
        description='Downsampled to 80×20, preprocessing disabled',
        downsample_size=(80, 20),
        enable_preprocessing=False,
        sample_size=args.sample_size
    )
    all_results['tests'].append(down_80x20_no_preproc)
    
    # Test 4: Downsampled 80×20, WITH preprocessing (key test!)
    down_80x20_with_preproc = benchmark.test_configuration(
        test_name='downsampled_80x20_with_preproc',
        description='Downsampled to 80×20, preprocessing enabled (Lanczos upscaling)',
        downsample_size=(80, 20),
        enable_preprocessing=True,
        sample_size=args.sample_size
    )
    all_results['tests'].append(down_80x20_with_preproc)
    
    # Test 5: Downsampled 40×10, no preprocessing
    down_40x10_no_preproc = benchmark.test_configuration(
        test_name='downsampled_40x10_no_preproc',
        description='Downsampled to 40×10, preprocessing disabled',
        downsample_size=(40, 10),
        enable_preprocessing=False,
        sample_size=args.sample_size
    )
    all_results['tests'].append(down_40x10_no_preproc)
    
    # Test 6: Downsampled 40×10, WITH preprocessing (should help but limited)
    down_40x10_with_preproc = benchmark.test_configuration(
        test_name='downsampled_40x10_with_preproc',
        description='Downsampled to 40×10, preprocessing enabled (below threshold)',
        downsample_size=(40, 10),
        enable_preprocessing=True,
        sample_size=args.sample_size
    )
    all_results['tests'].append(down_40x10_with_preproc)
    
    # Save results
    results_file = output_dir / 'integrated_benchmark_results.json'
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"\nResults saved to {results_file}")
    
    # Print comparison table
    print("\n" + "="*120)
    print("OCR PREPROCESSING BENCHMARK - INTEGRATED ENGINE")
    print("="*120)
    print(f"\nSample size: {args.sample_size} clean synthetic plates per condition")
    print(f"Engine: HybridOCREngine with EasyOCR backend")
    print(f"Original size: 440×110 pixels\n")
    print("-"*120)
    print(f"{'Test Name':<55} {'Exact Match':<15} {'Char Acc':<12} {'Empty':<10} {'Time (s)':<10}")
    print("-"*120)
    
    for test in all_results['tests']:
        name = test['test_name']
        exact = test['summary'].get('exact_match_rate', 0)
        exact_count = test['summary'].get('exact_matches', 0)
        total_count = test['summary'].get('total_images', 0)
        char_acc = test['summary'].get('mean_character_accuracy', 0)
        empty = test['summary'].get('empty_output_rate', 0)
        time_avg = test['summary'].get('avg_processing_time', 0)
        
        print(f"{name:<55} {exact:>6.1%} ({exact_count:>2}/{total_count:<2}) {char_acc:>10.1f}% {empty:>8.1%} {time_avg:>9.3f}")
    
    print("="*120)
    
    # Print key comparison
    print("\n" + "="*120)
    print("KEY COMPARISON: Impact of Preprocessing on 80×20 Crops")
    print("="*120)
    
    test_without = next(t for t in all_results['tests'] if t['test_name'] == 'downsampled_80x20_no_preproc')
    test_with = next(t for t in all_results['tests'] if t['test_name'] == 'downsampled_80x20_with_preproc')
    
    exact_without = test_without['summary']['exact_match_rate']
    exact_with = test_with['summary']['exact_match_rate']
    improvement = exact_with - exact_without
    
    char_without = test_without['summary']['mean_character_accuracy']
    char_with = test_with['summary']['mean_character_accuracy']
    char_improvement = char_with - char_without
    
    print(f"\nWithout preprocessing: {exact_without:.1%} exact match, {char_without:.1f}% char accuracy")
    print(f"With preprocessing:    {exact_with:.1%} exact match, {char_with:.1f}% char accuracy")
    print(f"Improvement:           {improvement:+.1%} exact match, {char_improvement:+.1f}% char accuracy")
    print(f"\nExact counts: {test_without['summary']['exact_matches']}/{test_without['summary']['total_images']} → " \
          f"{test_with['summary']['exact_matches']}/{test_with['summary']['total_images']}")
    print("="*120)


if __name__ == '__main__':
    main()

