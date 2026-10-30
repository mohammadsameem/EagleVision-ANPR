"""
ANPR Accuracy Validation Script

Measures vehicle detection, plate detection, and OCR accuracy against ground truth.
Generates detailed metrics and validation reports.
"""
import argparse
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime
import sys

import cv2
import numpy as np

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Note: Import models only when needed for actual processing
# from src.video_processor import VideoProcessor
# from src.vehicle_detector import VehicleDetector
# from src.plate_detector import PlateDetector
# from src.ocr_engine import OCREngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def calculate_iou(box1: List[int], box2: List[int]) -> float:
    """
    Calculate Intersection over Union between two bounding boxes.
    
    Args:
        box1: [x, y, w, h]
        box2: [x, y, w, h]
    
    Returns:
        IoU score (0.0 to 1.0)
    """
    x1, y1, w1, h1 = box1
    x2, y2, w2, h2 = box2
    
    # Convert to x1, y1, x2, y2 format
    box1_x2 = x1 + w1
    box1_y2 = y1 + h1
    box2_x2 = x2 + w2
    box2_y2 = y2 + h2
    
    # Calculate intersection
    inter_x1 = max(x1, x2)
    inter_y1 = max(y1, y2)
    inter_x2 = min(box1_x2, box2_x2)
    inter_y2 = min(box1_y2, box2_y2)
    
    if inter_x2 < inter_x1 or inter_y2 < inter_y1:
        return 0.0
    
    inter_area = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    
    # Calculate union
    box1_area = w1 * h1
    box2_area = w2 * h2
    union_area = box1_area + box2_area - inter_area
    
    if union_area == 0:
        return 0.0
    
    return inter_area / union_area


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
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def calculate_character_accuracy(pred: str, truth: str) -> float:
    """
    Calculate character-level accuracy using Levenshtein distance.
    
    Returns:
        Accuracy as percentage (0.0 to 100.0)
    """
    if not truth:
        return 0.0 if pred else 100.0
    
    distance = calculate_levenshtein_distance(pred, truth)
    max_len = max(len(pred), len(truth))
    
    if max_len == 0:
        return 100.0
    
    accuracy = (1 - distance / max_len) * 100
    return max(0.0, accuracy)


def normalize_plate_text(text: str) -> str:
    """Normalize plate text for comparison."""
    # Remove extra spaces, convert to uppercase
    return ' '.join(text.upper().split())


def match_detections_to_ground_truth(
    detections: List[Dict],
    ground_truth: List[Dict],
    iou_threshold: float = 0.5
) -> Tuple[List[Tuple[int, int, float]], List[int], List[int]]:
    """
    Match detected bounding boxes to ground truth using IoU.
    
    Args:
        detections: List of detection dicts with 'bbox' key
        ground_truth: List of ground truth dicts with 'bbox' key
        iou_threshold: Minimum IoU for a match
    
    Returns:
        matches: List of (det_idx, gt_idx, iou) tuples
        unmatched_detections: List of detection indices
        unmatched_ground_truth: List of ground truth indices
    """
    n_det = len(detections)
    n_gt = len(ground_truth)
    
    if n_det == 0 or n_gt == 0:
        return [], list(range(n_det)), list(range(n_gt))
    
    # Calculate IoU matrix
    iou_matrix = np.zeros((n_det, n_gt))
    for i, det in enumerate(detections):
        for j, gt in enumerate(ground_truth):
            iou_matrix[i, j] = calculate_iou(det['bbox'], gt['bbox'])
    
    # Greedy matching: highest IoU first
    matches = []
    matched_dets = set()
    matched_gts = set()
    
    while True:
        max_iou = 0
        max_pos = None
        
        for i in range(n_det):
            if i in matched_dets:
                continue
            for j in range(n_gt):
                if j in matched_gts:
                    continue
                if iou_matrix[i, j] > max_iou and iou_matrix[i, j] >= iou_threshold:
                    max_iou = iou_matrix[i, j]
                    max_pos = (i, j)
        
        if max_pos is None:
            break
        
        i, j = max_pos
        matches.append((i, j, max_iou))
        matched_dets.add(i)
        matched_gts.add(j)
    
    unmatched_dets = [i for i in range(n_det) if i not in matched_dets]
    unmatched_gts = [i for i in range(n_gt) if i not in matched_gts]
    
    return matches, unmatched_dets, unmatched_gts


def calculate_precision_recall_f1(tp: int, fp: int, fn: int) -> Dict[str, float]:
    """Calculate precision, recall, and F1 score."""
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    
    return {
        'precision': precision,
        'recall': recall,
        'f1': f1,
        'true_positives': tp,
        'false_positives': fp,
        'false_negatives': fn
    }


def validate_vehicle_detection(
    detections: List[Dict],
    ground_truth: Dict,
    iou_threshold: float = 0.5
) -> Dict:
    """
    Validate vehicle detection accuracy.
    
    Args:
        detections: List of vehicle detections
        ground_truth: Ground truth data with 'vehicles' key
        iou_threshold: IoU threshold for matching
    
    Returns:
        Validation metrics dict
    """
    logger.info("Validating vehicle detection...")
    
    gt_vehicles = ground_truth.get('vehicles', [])
    
    matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
        detections, gt_vehicles, iou_threshold
    )
    
    tp = len(matches)
    fp = len(unmatched_dets)
    fn = len(unmatched_gts)
    
    metrics = calculate_precision_recall_f1(tp, fp, fn)
    
    # Calculate mean IoU for matches
    if matches:
        mean_iou = np.mean([m[2] for m in matches])
    else:
        mean_iou = 0.0
    
    metrics.update({
        'mean_iou': mean_iou,
        'iou_threshold': iou_threshold,
        'total_detections': len(detections),
        'total_ground_truth': len(gt_vehicles),
        'matches': len(matches)
    })
    
    logger.info(f"Vehicle Detection: P={metrics['precision']:.3f}, R={metrics['recall']:.3f}, F1={metrics['f1']:.3f}")
    
    return metrics


def validate_plate_detection(
    detections: List[Dict],
    ground_truth: Dict,
    iou_threshold: float = 0.5
) -> Dict:
    """
    Validate plate detection accuracy.
    
    Args:
        detections: List of detections with plates
        ground_truth: Ground truth data with 'plates' key
        iou_threshold: IoU threshold for matching
    
    Returns:
        Validation metrics dict
    """
    logger.info("Validating plate detection...")
    
    # Extract plates from detections
    detected_plates = []
    for det in detections:
        if det.get('plate_bbox_absolute'):
            detected_plates.append({
                'bbox': det['plate_bbox_absolute']
            })
    
    gt_plates = ground_truth.get('plates', [])
    
    matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
        detected_plates, gt_plates, iou_threshold
    )
    
    tp = len(matches)
    fp = len(unmatched_dets)
    fn = len(unmatched_gts)
    
    metrics = calculate_precision_recall_f1(tp, fp, fn)
    
    # Calculate mean IoU and analyze by size
    if matches:
        mean_iou = np.mean([m[2] for m in matches])
        
        # Analyze by plate size
        small_plates = []  # < 1000 pixels
        medium_plates = []  # 1000-5000 pixels
        large_plates = []  # > 5000 pixels
        
        for det_idx, gt_idx, iou in matches:
            bbox = gt_plates[gt_idx]['bbox']
            area = bbox[2] * bbox[3]
            
            if area < 1000:
                small_plates.append(iou)
            elif area < 5000:
                medium_plates.append(iou)
            else:
                large_plates.append(iou)
        
        metrics['mean_iou_by_size'] = {
            'small': np.mean(small_plates) if small_plates else 0.0,
            'medium': np.mean(medium_plates) if medium_plates else 0.0,
            'large': np.mean(large_plates) if large_plates else 0.0
        }
    else:
        mean_iou = 0.0
        metrics['mean_iou_by_size'] = {'small': 0.0, 'medium': 0.0, 'large': 0.0}
    
    metrics.update({
        'mean_iou': mean_iou,
        'iou_threshold': iou_threshold,
        'total_detections': len(detected_plates),
        'total_ground_truth': len(gt_plates),
        'matches': len(matches)
    })
    
    logger.info(f"Plate Detection: P={metrics['precision']:.3f}, R={metrics['recall']:.3f}, F1={metrics['f1']:.3f}")
    
    return metrics


def validate_ocr_accuracy(
    detections: List[Dict],
    ground_truth: Dict,
    min_plate_size: int = 400
) -> Dict:
    """
    Validate OCR accuracy.
    
    Args:
        detections: List of detections with OCR results
        ground_truth: Ground truth data with 'plates' and registration numbers
        min_plate_size: Minimum plate area (width * height) for OCR evaluation
    
    Returns:
        Validation metrics dict
    """
    logger.info("Validating OCR accuracy...")
    
    exact_matches = 0
    character_accuracies = []
    empty_outputs = 0
    low_confidence = 0
    small_crops = 0
    total_evaluated = 0
    
    results_by_quality = {
        'small_crop': [],  # < min_plate_size
        'adequate_crop': []  # >= min_plate_size
    }
    
    # Match detections to ground truth plates
    gt_plates = ground_truth.get('plates', [])
    
    for det in detections:
        if not det.get('plate_bbox_absolute'):
            continue
        
        # Check plate size
        plate_bbox = det.get('plate_bbox_absolute') or det.get('plate_bbox_relative')
        if plate_bbox:
            plate_area = plate_bbox[2] * plate_bbox[3]
            if plate_area < min_plate_size:
                small_crops += 1
                quality_category = 'small_crop'
            else:
                quality_category = 'adequate_crop'
        else:
            quality_category = 'adequate_crop'
        
        # Find matching ground truth
        det_bbox = det['plate_bbox_absolute']
        best_match = None
        best_iou = 0.0
        
        for gt_plate in gt_plates:
            iou = calculate_iou(det_bbox, gt_plate['bbox'])
            if iou > best_iou and iou >= 0.5:
                best_iou = iou
                best_match = gt_plate
        
        if not best_match:
            continue
        
        total_evaluated += 1
        
        # Get OCR result
        ocr_text = det.get('ocr_text', '')
        ocr_confidence = det.get('ocr_confidence', 0.0)
        gt_text = best_match.get('registration_number', '')
        
        # Normalize texts
        ocr_normalized = normalize_plate_text(ocr_text)
        gt_normalized = normalize_plate_text(gt_text)
        
        # Track empty outputs
        if not ocr_normalized:
            empty_outputs += 1
        
        # Track low confidence
        if ocr_confidence < 0.5:
            low_confidence += 1
        
        # Calculate metrics
        exact_match = (ocr_normalized == gt_normalized)
        if exact_match:
            exact_matches += 1
        
        char_accuracy = calculate_character_accuracy(ocr_normalized, gt_normalized)
        character_accuracies.append(char_accuracy)
        
        results_by_quality[quality_category].append({
            'exact_match': exact_match,
            'char_accuracy': char_accuracy,
            'predicted': ocr_normalized,
            'ground_truth': gt_normalized,
            'confidence': ocr_confidence,
            'plate_area': plate_area if plate_bbox else 0
        })
    
    # Calculate overall metrics
    exact_match_rate = exact_matches / total_evaluated if total_evaluated > 0 else 0.0
    mean_char_accuracy = np.mean(character_accuracies) if character_accuracies else 0.0
    empty_rate = empty_outputs / total_evaluated if total_evaluated > 0 else 0.0
    
    metrics = {
        'exact_match_accuracy': exact_match_rate,
        'character_accuracy': mean_char_accuracy,
        'exact_matches': exact_matches,
        'total_evaluated': total_evaluated,
        'empty_outputs': empty_outputs,
        'empty_output_rate': empty_rate,
        'low_confidence_count': low_confidence,
        'small_crops_excluded': small_crops,
        'min_plate_size_threshold': min_plate_size,
        'results_by_quality': {
            'small_crop': {
                'count': len(results_by_quality['small_crop']),
                'mean_char_accuracy': np.mean([r['char_accuracy'] for r in results_by_quality['small_crop']]) if results_by_quality['small_crop'] else 0.0
            },
            'adequate_crop': {
                'count': len(results_by_quality['adequate_crop']),
                'mean_char_accuracy': np.mean([r['char_accuracy'] for r in results_by_quality['adequate_crop']]) if results_by_quality['adequate_crop'] else 0.0
            }
        }
    }
    
    logger.info(f"OCR: Exact={exact_match_rate:.1%}, Char={mean_char_accuracy:.1f}%, Empty={empty_rate:.1%}")
    
    return metrics


def diagnose_ocr_failures(crops_dir: Path, output_file: Path) -> Dict:
    """
    Diagnose why OCR is failing on plate crops.
    
    Args:
        crops_dir: Directory containing plate crop images
        output_file: Path to save diagnosis results
    
    Returns:
        Diagnosis results dict
    """
    logger.info(f"Diagnosing OCR failures in {crops_dir}...")
    
    crop_files = list(crops_dir.glob("plate_*.jpg")) + list(crops_dir.glob("plate_*.png"))
    
    if not crop_files:
        logger.warning(f"No plate crops found in {crops_dir}")
        return {'error': 'No plate crops found'}
    
    # Analyze crop dimensions
    dimensions = []
    areas = []
    aspect_ratios = []
    
    for crop_file in crop_files[:50]:  # Sample first 50
        img = cv2.imread(str(crop_file))
        if img is not None:
            h, w = img.shape[:2]
            dimensions.append((w, h))
            areas.append(w * h)
            aspect_ratios.append(w / h if h > 0 else 0)
    
    if not dimensions:
        return {'error': 'Could not read crop images'}
    
    diagnosis = {
        'total_crops_sampled': len(dimensions),
        'dimensions': {
            'min_width': min(d[0] for d in dimensions),
            'max_width': max(d[0] for d in dimensions),
            'mean_width': np.mean([d[0] for d in dimensions]),
            'min_height': min(d[1] for d in dimensions),
            'max_height': max(d[1] for d in dimensions),
            'mean_height': np.mean([d[1] for d in dimensions])
        },
        'areas': {
            'min': min(areas),
            'max': max(areas),
            'mean': np.mean(areas),
            'below_400px': sum(1 for a in areas if a < 400),
            'below_1000px': sum(1 for a in areas if a < 1000)
        },
        'aspect_ratios': {
            'min': min(aspect_ratios),
            'max': max(aspect_ratios),
            'mean': np.mean(aspect_ratios)
        },
        'recommendations': []
    }
    
    # Generate recommendations
    if diagnosis['dimensions']['mean_width'] < 50:
        diagnosis['recommendations'].append(
            "CRITICAL: Plate crops are too small (mean width < 50px). OCR will fail. "
            "Increase detection resolution or use larger source images."
        )
    elif diagnosis['dimensions']['mean_width'] < 100:
        diagnosis['recommendations'].append(
            "WARNING: Plate crops are very small (mean width < 100px). OCR accuracy will be poor. "
            "Consider upscaling crops before OCR."
        )
    
    if diagnosis['areas']['mean'] < 1000:
        diagnosis['recommendations'].append(
            f"Plate crop area is small (mean {diagnosis['areas']['mean']:.0f}px). "
            "Minimum recommended area is 1000px (e.g., 100x10 or 50x20)."
        )
    
    # Save diagnosis
    with open(output_file, 'w') as f:
        json.dump(diagnosis, f, indent=2)
    
    logger.info(f"Diagnosis saved to {output_file}")
    
    return diagnosis


def load_ground_truth(gt_file: Path) -> Dict:
    """Load ground truth annotations from JSON file."""
    if not gt_file.exists():
        raise FileNotFoundError(f"Ground truth file not found: {gt_file}")
    
    with open(gt_file, 'r') as f:
        return json.load(f)


def run_validation(
    video_path: Path,
    ground_truth_file: Path,
    output_dir: Path,
    target_fps: int = 5,
    iou_threshold: float = 0.5
) -> Dict:
    """
    Run complete ANPR validation pipeline.
    
    Args:
        video_path: Path to video file
        ground_truth_file: Path to ground truth JSON
        output_dir: Directory to save results
        target_fps: Target FPS for processing
        iou_threshold: IoU threshold for matching
    
    Returns:
        Complete validation results dict
    """
    logger.info(f"Running validation on {video_path}")
    
    # Load ground truth
    ground_truth = load_ground_truth(ground_truth_file)
    
    # Process video (mock for now - would use actual ANPR pipeline)
    # TODO: Integrate with actual ANPRPipeline
    logger.warning("Video processing not yet integrated - using mock detections")
    detections = []
    
    # Validate each component
    results = {
        'metadata': {
            'video': str(video_path),
            'ground_truth_file': str(ground_truth_file),
            'timestamp': datetime.now().isoformat(),
            'target_fps': target_fps,
            'iou_threshold': iou_threshold
        },
        'dataset': {
            'total_frames_annotated': ground_truth.get('total_frames', 0),
            'total_vehicles': len(ground_truth.get('vehicles', [])),
            'total_plates': len(ground_truth.get('plates', []))
        },
        'vehicle_detection': validate_vehicle_detection(detections, ground_truth, iou_threshold),
        'plate_detection': validate_plate_detection(detections, ground_truth, iou_threshold),
        'ocr_accuracy': validate_ocr_accuracy(detections, ground_truth),
        'limitations': [
            "Video processing pipeline not yet integrated",
            "Using mock detections for validation framework testing"
        ]
    }
    
    # Save results
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results_file = output_dir / 'validation_results.json'
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"Results saved to {results_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description='Validate ANPR accuracy against ground truth')
    parser.add_argument('--video', type=str, help='Path to video file')
    parser.add_argument('--ground-truth', type=str, help='Path to ground truth JSON file')
    parser.add_argument('--output-dir', type=str, default='validation_results',
                       help='Directory to save validation results')
    parser.add_argument('--diagnose-crops', type=str,
                       help='Diagnose OCR failures in directory of plate crops')
    parser.add_argument('--target-fps', type=int, default=5,
                       help='Target FPS for video processing')
    parser.add_argument('--iou-threshold', type=float, default=0.5,
                       help='IoU threshold for detection matching')
    
    args = parser.parse_args()
    
    if args.diagnose_crops:
        # Run diagnosis mode
        crops_dir = Path(args.diagnose_crops)
        output_file = Path(args.output_dir) / 'ocr_diagnosis.json'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        diagnosis = diagnose_ocr_failures(crops_dir, output_file)
        
        print("\n=== OCR Crop Diagnosis ===")
        print(f"Crops sampled: {diagnosis.get('total_crops_sampled', 0)}")
        print(f"Mean dimensions: {diagnosis['dimensions']['mean_width']:.1f}x{diagnosis['dimensions']['mean_height']:.1f}")
        print(f"Mean area: {diagnosis['areas']['mean']:.0f} pixels")
        print(f"Crops < 400px: {diagnosis['areas']['below_400px']}")
        print(f"Crops < 1000px: {diagnosis['areas']['below_1000px']}")
        
        if diagnosis.get('recommendations'):
            print("\nRecommendations:")
            for i, rec in enumerate(diagnosis['recommendations'], 1):
                print(f"{i}. {rec}")
    
    elif args.video and args.ground_truth:
        # Run full validation
        video_path = Path(args.video)
        gt_file = Path(args.ground_truth)
        output_dir = Path(args.output_dir)
        
        results = run_validation(
            video_path, gt_file, output_dir,
            target_fps=args.target_fps,
            iou_threshold=args.iou_threshold
        )
        
        print("\n=== Validation Results ===")
        print(f"Vehicle Detection F1: {results['vehicle_detection']['f1']:.3f}")
        print(f"Plate Detection F1: {results['plate_detection']['f1']:.3f}")
        print(f"OCR Exact Match: {results['ocr_accuracy']['exact_match_accuracy']:.1%}")
        print(f"OCR Character Accuracy: {results['ocr_accuracy']['character_accuracy']:.1f}%")
    
    else:
        parser.print_help()
        print("\nExample usage:")
        print("  # Diagnose plate crop issues:")
        print("  python scripts/validate_anpr_accuracy.py --diagnose-crops data/gemini_anpr_test")
        print("\n  # Run full validation (when ground truth available):")
        print("  python scripts/validate_anpr_accuracy.py --video data/test.mp4 --ground-truth data/test_gt.json")


if __name__ == '__main__':
    main()
