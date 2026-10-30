"""
Test OCR preprocessing techniques on small plate crops.

Compares multiple preprocessing approaches to determine if upscaling
and enhancement improve OCR recognition on small plate crops.
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


class OCRPreprocessor:
    """Test various preprocessing techniques for OCR."""
    
    @staticmethod
    def no_preprocessing(crop: np.ndarray) -> np.ndarray:
        """Baseline - no preprocessing."""
        return crop.copy()
    
    @staticmethod
    def upscale_cubic(crop: np.ndarray, target_height: int = 60) -> np.ndarray:
        """
        Upscale small crops using cubic interpolation.
        
        Args:
            crop: Input image
            target_height: Target height in pixels
        
        Returns:
            Upscaled image
        """
        h, w = crop.shape[:2]
        
        # Only upscale if smaller than target
        if h < target_height:
            scale = target_height / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        return crop.copy()
    
    @staticmethod
    def upscale_lanczos(crop: np.ndarray, target_height: int = 60) -> np.ndarray:
        """
        Upscale small crops using Lanczos interpolation.
        
        Args:
            crop: Input image
            target_height: Target height in pixels
        
        Returns:
            Upscaled image
        """
        h, w = crop.shape[:2]
        
        # Only upscale if smaller than target
        if h < target_height:
            scale = target_height / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            return cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_LANCZOS4)
        
        return crop.copy()
    
    @staticmethod
    def upscale_with_sharpening(crop: np.ndarray, target_height: int = 60) -> np.ndarray:
        """
        Upscale and sharpen.
        
        Args:
            crop: Input image
            target_height: Target height in pixels
        
        Returns:
            Upscaled and sharpened image
        """
        h, w = crop.shape[:2]
        
        # Upscale
        if h < target_height:
            scale = target_height / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Sharpen using unsharp mask
        gaussian = cv2.GaussianBlur(crop, (0, 0), 2.0)
        sharpened = cv2.addWeighted(crop, 1.5, gaussian, -0.5, 0)
        
        return sharpened
    
    @staticmethod
    def upscale_with_contrast(crop: np.ndarray, target_height: int = 60) -> np.ndarray:
        """
        Upscale and enhance contrast using CLAHE.
        
        Args:
            crop: Input image
            target_height: Target height in pixels
        
        Returns:
            Upscaled and contrast-enhanced image
        """
        h, w = crop.shape[:2]
        
        # Upscale
        if h < target_height:
            scale = target_height / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Convert to LAB color space
        if len(crop.shape) == 3:
            lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # Apply CLAHE to L channel
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            l = clahe.apply(l)
            
            # Merge and convert back
            lab = cv2.merge([l, a, b])
            crop = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
        else:
            # Grayscale
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            crop = clahe.apply(crop)
        
        return crop
    
    @staticmethod
    def upscale_with_denoising(crop: np.ndarray, target_height: int = 60) -> np.ndarray:
        """
        Upscale and denoise.
        
        Args:
            crop: Input image
            target_height: Target height in pixels
        
        Returns:
            Upscaled and denoised image
        """
        h, w = crop.shape[:2]
        
        # Upscale
        if h < target_height:
            scale = target_height / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Denoise
        if len(crop.shape) == 3:
            denoised = cv2.fastNlMeansDenoisingColored(crop, None, 10, 10, 7, 21)
        else:
            denoised = cv2.fastNlMeansDenoising(crop, None, 10, 7, 21)
        
        return denoised
    
    @staticmethod
    def adaptive_preprocessing(crop: np.ndarray) -> np.ndarray:
        """
        Adaptive preprocessing based on crop characteristics.
        
        Args:
            crop: Input image
        
        Returns:
            Preprocessed image
        """
        h, w = crop.shape[:2]
        original = crop.copy()
        
        # Always upscale if very small
        if h < 40 or w < 120:
            target_height = 60
            scale = target_height / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            crop = cv2.resize(crop, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        
        # Assess image quality
        if len(crop.shape) == 3:
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        else:
            gray = crop
        
        # Check contrast
        contrast = gray.std()
        
        # Enhance contrast if low
        if contrast < 30:
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            if len(crop.shape) == 3:
                lab = cv2.cvtColor(crop, cv2.COLOR_BGR2LAB)
                l, a, b = cv2.split(lab)
                l = clahe.apply(l)
                lab = cv2.merge([l, a, b])
                crop = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
            else:
                crop = clahe.apply(crop)
        
        return crop


def test_preprocessing_methods(
    crops_dir: Path,
    output_dir: Path,
    ground_truth: Dict = None,
    max_crops: int = 20
) -> Dict:
    """
    Test multiple preprocessing methods on plate crops.
    
    Args:
        crops_dir: Directory containing plate crop images
        output_dir: Directory to save results
        ground_truth: Optional ground truth dict {filename: registration_number}
        max_crops: Maximum number of crops to test
    
    Returns:
        Results dictionary
    """
    logger.info("Initializing EasyOCR...")
    reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    
    # Preprocessing methods to test
    preprocessor = OCRPreprocessor()
    methods = {
        'none': preprocessor.no_preprocessing,
        'cubic_upscale': preprocessor.upscale_cubic,
        'lanczos_upscale': preprocessor.upscale_lanczos,
        'upscale_sharpen': preprocessor.upscale_with_sharpening,
        'upscale_contrast': preprocessor.upscale_with_contrast,
        'upscale_denoise': preprocessor.upscale_with_denoising,
        'adaptive': preprocessor.adaptive_preprocessing
    }
    
    # Find crop files
    crop_files = sorted(list(crops_dir.glob("plate_*.jpg")) + list(crops_dir.glob("plate_*.png")))
    
    if not crop_files:
        logger.error(f"No plate crops found in {crops_dir}")
        return {'error': 'No crops found'}
    
    # Limit number of crops
    crop_files = crop_files[:max_crops]
    logger.info(f"Testing {len(crop_files)} crops with {len(methods)} methods...")
    
    # Results structure
    results = {
        'metadata': {
            'timestamp': datetime.now().isoformat(),
            'crops_dir': str(crops_dir),
            'total_crops_tested': len(crop_files),
            'methods_tested': list(methods.keys()),
            'has_ground_truth': ground_truth is not None
        },
        'by_method': {},
        'by_crop': {}
    }
    
    # Initialize method results
    for method_name in methods.keys():
        results['by_method'][method_name] = {
            'total_crops': 0,
            'successful_reads': 0,
            'empty_reads': 0,
            'total_processing_time': 0.0,
            'ocr_texts': [],
            'confidences': []
        }
        
        if ground_truth:
            results['by_method'][method_name]['exact_matches'] = 0
            results['by_method'][method_name]['character_accuracies'] = []
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Test each crop with each method
    for crop_idx, crop_file in enumerate(crop_files):
        logger.info(f"Processing {crop_file.name} ({crop_idx + 1}/{len(crop_files)})...")
        
        # Load original crop
        original = cv2.imread(str(crop_file))
        if original is None:
            logger.warning(f"Could not read {crop_file}")
            continue
        
        crop_results = {
            'filename': crop_file.name,
            'original_size': (original.shape[1], original.shape[0]),
            'original_area': original.shape[0] * original.shape[1],
            'methods': {}
        }
        
        # Test each preprocessing method
        for method_name, method_func in methods.items():
            start_time = time.time()
            
            # Apply preprocessing
            processed = method_func(original)
            
            # Run OCR
            try:
                ocr_results = reader.readtext(processed)
                processing_time = time.time() - start_time
                
                # Extract text and confidence
                if ocr_results:
                    texts = [text for (bbox, text, conf) in ocr_results]
                    confidences = [conf for (bbox, text, conf) in ocr_results]
                    combined_text = " ".join(texts)
                    avg_confidence = sum(confidences) / len(confidences)
                else:
                    combined_text = ""
                    avg_confidence = 0.0
                
                # Record results
                method_results = {
                    'text': combined_text,
                    'confidence': float(avg_confidence),
                    'processing_time': processing_time,
                    'preprocessed_size': (processed.shape[1], processed.shape[0]),
                    'num_detections': len(ocr_results)
                }
                
                # Update method statistics
                results['by_method'][method_name]['total_crops'] += 1
                results['by_method'][method_name]['total_processing_time'] += processing_time
                results['by_method'][method_name]['ocr_texts'].append(combined_text)
                results['by_method'][method_name]['confidences'].append(avg_confidence)
                
                if combined_text:
                    results['by_method'][method_name]['successful_reads'] += 1
                else:
                    results['by_method'][method_name]['empty_reads'] += 1
                
                # Check against ground truth if available
                if ground_truth and crop_file.name in ground_truth:
                    gt_text = ground_truth[crop_file.name].upper().replace(" ", "")
                    ocr_normalized = combined_text.upper().replace(" ", "")
                    
                    if gt_text == ocr_normalized:
                        results['by_method'][method_name]['exact_matches'] += 1
                        method_results['exact_match'] = True
                    else:
                        method_results['exact_match'] = False
                    
                    # Calculate character accuracy (Levenshtein)
                    char_accuracy = calculate_character_accuracy(ocr_normalized, gt_text)
                    results['by_method'][method_name]['character_accuracies'].append(char_accuracy)
                    method_results['character_accuracy'] = char_accuracy
                    method_results['ground_truth'] = ground_truth[crop_file.name]
                
                crop_results['methods'][method_name] = method_results
                
                # Save preprocessed image for visual inspection (first 5 crops only)
                if crop_idx < 5:
                    output_file = output_dir / f"{crop_file.stem}_{method_name}.jpg"
                    cv2.imwrite(str(output_file), processed)
            
            except Exception as e:
                logger.error(f"Error processing {crop_file.name} with {method_name}: {e}")
                crop_results['methods'][method_name] = {'error': str(e)}
        
        results['by_crop'][crop_file.name] = crop_results
    
    # Calculate summary statistics
    for method_name in methods.keys():
        method_stats = results['by_method'][method_name]
        
        if method_stats['total_crops'] > 0:
            method_stats['success_rate'] = method_stats['successful_reads'] / method_stats['total_crops']
            method_stats['avg_processing_time'] = method_stats['total_processing_time'] / method_stats['total_crops']
            method_stats['avg_confidence'] = (
                sum(method_stats['confidences']) / len(method_stats['confidences'])
                if method_stats['confidences'] else 0.0
            )
            
            if ground_truth:
                method_stats['exact_match_rate'] = (
                    method_stats['exact_matches'] / method_stats['total_crops']
                    if method_stats['total_crops'] > 0 else 0.0
                )
                method_stats['avg_character_accuracy'] = (
                    sum(method_stats['character_accuracies']) / len(method_stats['character_accuracies'])
                    if method_stats['character_accuracies'] else 0.0
                )
    
    # Save results
    results_file = output_dir / 'preprocessing_test_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {results_file}")
    
    return results


def calculate_character_accuracy(pred: str, truth: str) -> float:
    """Calculate character accuracy using Levenshtein distance."""
    if not truth:
        return 0.0 if pred else 100.0
    
    # Calculate Levenshtein distance
    if len(pred) < len(truth):
        pred, truth = truth, pred
    
    if len(truth) == 0:
        return 0.0 if pred else 100.0
    
    previous_row = range(len(truth) + 1)
    for i, c1 in enumerate(pred):
        current_row = [i + 1]
        for j, c2 in enumerate(truth):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    distance = previous_row[-1]
    max_len = max(len(pred), len(truth))
    
    if max_len == 0:
        return 100.0
    
    accuracy = (1 - distance / max_len) * 100
    return max(0.0, accuracy)


def print_summary(results: Dict):
    """Print summary of preprocessing test results."""
    print("\n" + "="*80)
    print("OCR PREPROCESSING TEST RESULTS")
    print("="*80)
    
    print(f"\nCrops tested: {results['metadata']['total_crops_tested']}")
    print(f"Methods tested: {len(results['metadata']['methods_tested'])}")
    print(f"Has ground truth: {results['metadata']['has_ground_truth']}")
    
    print("\n" + "-"*80)
    print("RESULTS BY METHOD")
    print("-"*80)
    
    # Sort methods by success rate
    methods = results['by_method'].items()
    methods = sorted(methods, key=lambda x: x[1].get('success_rate', 0), reverse=True)
    
    for method_name, stats in methods:
        print(f"\n{method_name.upper()}:")
        print(f"  Success rate: {stats.get('success_rate', 0):.1%} ({stats['successful_reads']}/{stats['total_crops']})")
        print(f"  Avg confidence: {stats.get('avg_confidence', 0):.3f}")
        print(f"  Avg processing time: {stats.get('avg_processing_time', 0):.3f}s")
        
        if results['metadata']['has_ground_truth']:
            print(f"  Exact match rate: {stats.get('exact_match_rate', 0):.1%}")
            print(f"  Avg character accuracy: {stats.get('avg_character_accuracy', 0):.1f}%")


def main():
    parser = argparse.ArgumentParser(description='Test OCR preprocessing methods')
    parser.add_argument('--crops-dir', type=str, required=True,
                       help='Directory containing plate crop images')
    parser.add_argument('--output-dir', type=str, default='ocr_preprocessing_results',
                       help='Directory to save results')
    parser.add_argument('--ground-truth', type=str,
                       help='Path to ground truth JSON file')
    parser.add_argument('--max-crops', type=int, default=20,
                       help='Maximum number of crops to test')
    
    args = parser.parse_args()
    
    crops_dir = Path(args.crops_dir)
    output_dir = Path(args.output_dir)
    
    # Load ground truth if provided
    ground_truth = None
    if args.ground_truth:
        with open(args.ground_truth, 'r') as f:
            ground_truth = json.load(f)
    
    # Run tests
    results = test_preprocessing_methods(
        crops_dir,
        output_dir,
        ground_truth,
        max_crops=args.max_crops
    )
    
    # Print summary
    print_summary(results)


if __name__ == '__main__':
    main()
