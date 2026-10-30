"""
Controlled OCR Preprocessing Benchmark

Tests preprocessing methods on synthetic plates with known ground truth.
Measures actual accuracy improvement under controlled conditions.
"""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple
import time
from datetime import datetime

import cv2
import numpy as np
import easyocr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate edit distance between two strings."""
    if len(s1) < len(s2):
        return calculate_levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def calculate_character_accuracy(pred: str, truth: str) -> float:
    """
    Calculate character-level accuracy using Levenshtein distance.
    Returns accuracy as percentage (0.0 to 100.0).
    """
    if not truth:
        return 100.0 if not pred else 0.0
    
    distance = calculate_levenshtein_distance(pred, truth)
    max_len = max(len(pred), len(truth))
    
    if max_len == 0:
        return 100.0
    
    accuracy = (1 - distance / max_len) * 100
    return max(0.0, accuracy)


def normalize_text(text: str) -> str:
    """Normalize text for comparison: uppercase, single spaces."""
    return ' '.join(text.upper().split())


def downsample_image(image: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    """
    Downsample image to target size using area interpolation.
    
    Args:
        image: Source image
        target_size: (width, height) tuple
    
    Returns:
        Downsampled image
    """
    return cv2.resize(image, target_size, interpolation=cv2.INTER_AREA)


def upsample_cubic(image: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    """Upsample using cubic interpolation."""
    return cv2.resize(image, target_size, interpolation=cv2.INTER_CUBIC)


def upsample_lanczos(image: np.ndarray, target_size: Tuple[int, int]) -> np.ndarray:
    """Upsample using Lanczos4 interpolation."""
    return cv2.resize(image, target_size, interpolation=cv2.INTER_LANCZOS4)


def enhance_contrast(image: np.ndarray) -> np.ndarray:
    """Enhance contrast using CLAHE."""
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l = clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        return clahe.apply(image)


def sharpen_image(image: np.ndarray) -> np.ndarray:
    """Sharpen using unsharp mask."""
    gaussian = cv2.GaussianBlur(image, (0, 0), 2.0)
    return cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)


class OCRBenchmark:
    """OCR preprocessing benchmark with controlled conditions."""
    
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
        
        # Initialize EasyOCR
        logger.info("Initializing EasyOCR...")
        self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)
        logger.info("EasyOCR ready")
    
    def run_ocr(self, image: np.ndarray) -> Tuple[str, float, float]:
        """
        Run OCR on image.
        
        Returns:
            (text, confidence, processing_time)
        """
        start_time = time.time()
        
        try:
            results = self.reader.readtext(image)
            processing_time = time.time() - start_time
            
            if results:
                texts = [text for (bbox, text, conf) in results]
                confidences = [conf for (bbox, text, conf) in results]
                combined_text = " ".join(texts)
                avg_confidence = sum(confidences) / len(confidences)
            else:
                combined_text = ""
                avg_confidence = 0.0
            
            return combined_text, float(avg_confidence), processing_time
        
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return "", 0.0, time.time() - start_time
    
    def test_baseline(self, sample_size: int = 50) -> Dict:
        """
        Test baseline OCR on original synthetic plates.
        
        Args:
            sample_size: Number of images to test (or 'all')
        
        Returns:
            Results dict
        """
        logger.info("Testing baseline OCR on original plates...")
        
        results = {
            'test_name': 'baseline_original',
            'description': 'Original 440x110 synthetic plates, no preprocessing',
            'images_tested': [],
            'summary': {
                'total_images': 0,
                'exact_matches': 0,
                'empty_outputs': 0,
                'total_processing_time': 0.0
            },
            'character_accuracies': [],
            'confidences': []
        }
        
        # Test only clean variants to get baseline
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
            
            # Get ground truth
            gt_data = self.ground_truth[filename]
            gt_text = gt_data['registration_number']
            
            # Run OCR
            ocr_text, confidence, proc_time = self.run_ocr(image)
            
            # Normalize for comparison
            gt_normalized = normalize_text(gt_text)
            ocr_normalized = normalize_text(ocr_text)
            
            # Calculate metrics
            exact_match = (gt_normalized == ocr_normalized)
            char_accuracy = calculate_character_accuracy(ocr_normalized, gt_normalized)
            
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
                'empty_output': (ocr_text == "")
            }
            
            results['images_tested'].append(result_entry)
            
            # Update summary
            results['summary']['total_images'] += 1
            if exact_match:
                results['summary']['exact_matches'] += 1
            if ocr_text == "":
                results['summary']['empty_outputs'] += 1
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
                sum(results['confidences']) / len(results['confidences'])
            )
            results['summary']['avg_processing_time'] = (
                results['summary']['total_processing_time'] / results['summary']['total_images']
            )
        
        logger.info(
            f"Baseline: {results['summary']['exact_match_rate']:.1%} exact, "
            f"{results['summary']['mean_character_accuracy']:.1f}% char accuracy"
        )
        
        return results
    
    def test_downsampled(self, target_size: Tuple[int, int], sample_size: int = 50) -> Dict:
        """
        Test OCR on downsampled plates (no upscaling back).
        
        Args:
            target_size: (width, height) to downsample to
            sample_size: Number of images to test
        
        Returns:
            Results dict
        """
        logger.info(f"Testing downsampled plates ({target_size[0]}x{target_size[1]})...")
        
        results = {
            'test_name': f'downsampled_{target_size[0]}x{target_size[1]}',
            'description': f'Plates downsampled to {target_size[0]}x{target_size[1]}, no upscaling',
            'target_size': target_size,
            'images_tested': [],
            'summary': {
                'total_images': 0,
                'exact_matches': 0,
                'empty_outputs': 0,
                'total_processing_time': 0.0
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
                continue
            
            # Load and downsample
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            
            downsampled = downsample_image(image, target_size)
            
            # Get ground truth
            gt_data = self.ground_truth[filename]
            gt_text = gt_data['registration_number']
            
            # Run OCR on downsampled (not upscaled back)
            ocr_text, confidence, proc_time = self.run_ocr(downsampled)
            
            # Normalize for comparison
            gt_normalized = normalize_text(gt_text)
            ocr_normalized = normalize_text(ocr_text)
            
            # Calculate metrics
            exact_match = (gt_normalized == ocr_normalized)
            char_accuracy = calculate_character_accuracy(ocr_normalized, gt_normalized)
            
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
                'empty_output': (ocr_text == "")
            }
            
            results['images_tested'].append(result_entry)
            
            # Update summary
            results['summary']['total_images'] += 1
            if exact_match:
                results['summary']['exact_matches'] += 1
            if ocr_text == "":
                results['summary']['empty_outputs'] += 1
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
                sum(results['confidences']) / len(results['confidences'])
            )
            results['summary']['avg_processing_time'] = (
                results['summary']['total_processing_time'] / results['summary']['total_images']
            )
        
        logger.info(
            f"Downsampled: {results['summary']['exact_match_rate']:.1%} exact, "
            f"{results['summary']['mean_character_accuracy']:.1f}% char accuracy"
        )
        
        return results
    
    def test_downsampled_upscaled(
        self,
        downsample_size: Tuple[int, int],
        upsample_method: str = 'cubic',
        enhance: bool = False,
        sample_size: int = 50
    ) -> Dict:
        """
        Test OCR on downsampled then upscaled plates.
        
        Args:
            downsample_size: Size to downsample to
            upsample_method: 'cubic' or 'lanczos'
            enhance: Whether to apply contrast enhancement
            sample_size: Number of images to test
        
        Returns:
            Results dict
        """
        method_name = f"downsampled_{downsample_size[0]}x{downsample_size[1]}_then_{upsample_method}"
        if enhance:
            method_name += "_enhanced"
        
        logger.info(f"Testing {method_name}...")
        
        results = {
            'test_name': method_name,
            'description': f'Downsample to {downsample_size[0]}x{downsample_size[1]}, '
                          f'upscale with {upsample_method}' + (' + enhance' if enhance else ''),
            'downsample_size': downsample_size,
            'upsample_method': upsample_method,
            'enhance': enhance,
            'images_tested': [],
            'summary': {
                'total_images': 0,
                'exact_matches': 0,
                'empty_outputs': 0,
                'total_processing_time': 0.0
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
                continue
            
            # Load image
            image = cv2.imread(str(image_path))
            if image is None:
                continue
            
            original_size = (image.shape[1], image.shape[0])
            
            # Downsample
            downsampled = downsample_image(image, downsample_size)
            
            # Upscale back
            if upsample_method == 'cubic':
                upscaled = upsample_cubic(downsampled, original_size)
            elif upsample_method == 'lanczos':
                upscaled = upsample_lanczos(downsampled, original_size)
            else:
                raise ValueError(f"Unknown upsample method: {upsample_method}")
            
            # Enhance if requested
            if enhance:
                upscaled = enhance_contrast(upscaled)
            
            # Get ground truth
            gt_data = self.ground_truth[filename]
            gt_text = gt_data['registration_number']
            
            # Run OCR
            ocr_text, confidence, proc_time = self.run_ocr(upscaled)
            
            # Normalize for comparison
            gt_normalized = normalize_text(gt_text)
            ocr_normalized = normalize_text(ocr_text)
            
            # Calculate metrics
            exact_match = (gt_normalized == ocr_normalized)
            char_accuracy = calculate_character_accuracy(ocr_normalized, gt_normalized)
            
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
                'empty_output': (ocr_text == "")
            }
            
            results['images_tested'].append(result_entry)
            
            # Update summary
            results['summary']['total_images'] += 1
            if exact_match:
                results['summary']['exact_matches'] += 1
            if ocr_text == "":
                results['summary']['empty_outputs'] += 1
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
                sum(results['confidences']) / len(results['confidences'])
            )
            results['summary']['avg_processing_time'] = (
                results['summary']['total_processing_time'] / results['summary']['total_images']
            )
        
        logger.info(
            f"{method_name}: {results['summary']['exact_match_rate']:.1%} exact, "
            f"{results['summary']['mean_character_accuracy']:.1f}% char accuracy"
        )
        
        return results


def main():
    parser = argparse.ArgumentParser(description='Benchmark OCR preprocessing methods')
    parser.add_argument('--images-dir', type=str, default='data/ocr_test',
                       help='Directory containing synthetic plates')
    parser.add_argument('--ground-truth', type=str, default='data/ocr_test/ground_truth.json',
                       help='Path to ground truth JSON')
    parser.add_argument('--output-dir', type=str, default='ocr_benchmark_results',
                       help='Directory to save results')
    parser.add_argument('--sample-size', type=int, default=25,
                       help='Number of images to test per condition (0 for all clean variants)')
    
    args = parser.parse_args()
    
    images_dir = Path(args.images_dir)
    gt_file = Path(args.ground_truth)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Initialize benchmark
    benchmark = OCRBenchmark(gt_file, images_dir)
    
    # Run tests
    all_results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'images_dir': str(images_dir),
            'ground_truth_file': str(gt_file),
            'sample_size': args.sample_size
        },
        'tests': []
    }
    
    # Test 1: Baseline (original plates)
    baseline = benchmark.test_baseline(sample_size=args.sample_size)
    all_results['tests'].append(baseline)
    
    # Test 2: Downsampled to 80x20 (comparable to real crops)
    downsampled_80x20 = benchmark.test_downsampled((80, 20), sample_size=args.sample_size)
    all_results['tests'].append(downsampled_80x20)
    
    # Test 3: Downsampled to 40x10 (worst case)
    downsampled_40x10 = benchmark.test_downsampled((40, 10), sample_size=args.sample_size)
    all_results['tests'].append(downsampled_40x10)
    
    # Test 4: Downsample + cubic upscale (80x20)
    down_up_cubic_80 = benchmark.test_downsampled_upscaled(
        (80, 20), 'cubic', enhance=False, sample_size=args.sample_size
    )
    all_results['tests'].append(down_up_cubic_80)
    
    # Test 5: Downsample + lanczos upscale (80x20)
    down_up_lanczos_80 = benchmark.test_downsampled_upscaled(
        (80, 20), 'lanczos', enhance=False, sample_size=args.sample_size
    )
    all_results['tests'].append(down_up_lanczos_80)
    
    # Test 6: Downsample + cubic upscale + enhance (80x20)
    down_up_cubic_enh_80 = benchmark.test_downsampled_upscaled(
        (80, 20), 'cubic', enhance=True, sample_size=args.sample_size
    )
    all_results['tests'].append(down_up_cubic_enh_80)
    
    # Test 7: Downsample + cubic upscale (40x10)
    down_up_cubic_40 = benchmark.test_downsampled_upscaled(
        (40, 10), 'cubic', enhance=False, sample_size=args.sample_size
    )
    all_results['tests'].append(down_up_cubic_40)
    
    # Test 8: Downsample + cubic upscale + enhance (40x10)
    down_up_cubic_enh_40 = benchmark.test_downsampled_upscaled(
        (40, 10), 'cubic', enhance=True, sample_size=args.sample_size
    )
    all_results['tests'].append(down_up_cubic_enh_40)
    
    # Save results
    results_file = output_dir / 'benchmark_results.json'
    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)
    
    logger.info(f"\nResults saved to {results_file}")
    
    # Print summary table
    print("\n" + "="*100)
    print("OCR PREPROCESSING BENCHMARK RESULTS")
    print("="*100)
    print(f"\nSample size: {args.sample_size} clean synthetic plates per condition")
    print(f"Original size: 440x110 pixels")
    print("\n" + "-"*100)
    print(f"{'Test Name':<50} {'Exact':<10} {'Char Acc':<12} {'Empty':<10} {'Time (s)':<10}")
    print("-"*100)
    
    for test in all_results['tests']:
        name = test['test_name']
        exact = test['summary'].get('exact_match_rate', 0)
        char_acc = test['summary'].get('mean_character_accuracy', 0)
        empty = test['summary'].get('empty_output_rate', 0)
        time_avg = test['summary'].get('avg_processing_time', 0)
        
        print(f"{name:<50} {exact:>8.1%} {char_acc:>10.1f}% {empty:>8.1%} {time_avg:>9.3f}")
    
    print("="*100)


if __name__ == '__main__':
    main()
