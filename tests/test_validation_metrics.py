"""
Tests for ANPR validation metrics and calculations.
"""
import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from validate_anpr_accuracy import (
    calculate_iou,
    calculate_levenshtein_distance,
    calculate_character_accuracy,
    normalize_plate_text,
    match_detections_to_ground_truth,
    calculate_precision_recall_f1
)


class TestIoUCalculation:
    """Test Intersection over Union calculation."""
    
    def test_perfect_overlap(self):
        """Test IoU with identical boxes."""
        box1 = [100, 100, 50, 50]
        box2 = [100, 100, 50, 50]
        iou = calculate_iou(box1, box2)
        assert iou == 1.0
    
    def test_no_overlap(self):
        """Test IoU with non-overlapping boxes."""
        box1 = [100, 100, 50, 50]
        box2 = [200, 200, 50, 50]
        iou = calculate_iou(box1, box2)
        assert iou == 0.0
    
    def test_partial_overlap(self):
        """Test IoU with partial overlap."""
        box1 = [100, 100, 100, 100]  # Area = 10000
        box2 = [150, 150, 100, 100]  # Area = 10000
        # Intersection = 50x50 = 2500
        # Union = 10000 + 10000 - 2500 = 17500
        # IoU = 2500 / 17500 = 0.14285...
        iou = calculate_iou(box1, box2)
        assert abs(iou - 0.14285) < 0.001
    
    def test_one_inside_other(self):
        """Test IoU when one box is inside another."""
        box1 = [100, 100, 200, 200]  # Area = 40000
        box2 = [150, 150, 100, 100]  # Area = 10000 (inside box1)
        # Intersection = 10000
        # Union = 40000
        # IoU = 10000 / 40000 = 0.25
        iou = calculate_iou(box1, box2)
        assert abs(iou - 0.25) < 0.001
    
    def test_adjacent_boxes(self):
        """Test IoU with adjacent but non-overlapping boxes."""
        box1 = [100, 100, 50, 50]
        box2 = [150, 100, 50, 50]  # Right next to box1
        iou = calculate_iou(box1, box2)
        assert iou == 0.0


class TestLevenshteinDistance:
    """Test edit distance calculation."""
    
    def test_identical_strings(self):
        """Test distance with identical strings."""
        dist = calculate_levenshtein_distance("hello", "hello")
        assert dist == 0
    
    def test_empty_strings(self):
        """Test distance with empty strings."""
        assert calculate_levenshtein_distance("", "") == 0
        assert calculate_levenshtein_distance("hello", "") == 5
        assert calculate_levenshtein_distance("", "hello") == 5
    
    def test_single_insertion(self):
        """Test distance with one character insertion."""
        dist = calculate_levenshtein_distance("hello", "helo")
        assert dist == 1
    
    def test_single_deletion(self):
        """Test distance with one character deletion."""
        dist = calculate_levenshtein_distance("helo", "hello")
        assert dist == 1
    
    def test_single_substitution(self):
        """Test distance with one character substitution."""
        dist = calculate_levenshtein_distance("hello", "hallo")
        assert dist == 1
    
    def test_multiple_edits(self):
        """Test distance with multiple edits."""
        dist = calculate_levenshtein_distance("kitten", "sitting")
        assert dist == 3  # k->s, e->i, insert g
    
    def test_plate_numbers(self):
        """Test distance with plate numbers."""
        assert calculate_levenshtein_distance("MH12AB1234", "MH12AB1234") == 0
        assert calculate_levenshtein_distance("MH12AB1234", "MH12AB1235") == 1
        assert calculate_levenshtein_distance("MH12AB1234", "NH12AB1234") == 1


class TestCharacterAccuracy:
    """Test character-level accuracy calculation."""
    
    def test_exact_match(self):
        """Test accuracy with exact match."""
        acc = calculate_character_accuracy("MH12AB1234", "MH12AB1234")
        assert acc == 100.0
    
    def test_empty_strings(self):
        """Test accuracy with empty strings."""
        assert calculate_character_accuracy("", "") == 100.0
        assert calculate_character_accuracy("hello", "") == 0.0
        assert calculate_character_accuracy("", "hello") == 0.0
    
    def test_single_error(self):
        """Test accuracy with one character error."""
        # "MH12AB1234" vs "MH12AB1235" - 1 error in 10 chars = 90%
        acc = calculate_character_accuracy("MH12AB1235", "MH12AB1234")
        assert acc == 90.0
    
    def test_multiple_errors(self):
        """Test accuracy with multiple errors."""
        # "MH12AB1234" vs "NH12AC1235" - 3 errors in 10 chars = 70%
        acc = calculate_character_accuracy("NH12AC1235", "MH12AB1234")
        assert acc == 70.0
    
    def test_completely_different(self):
        """Test accuracy with completely different strings."""
        acc = calculate_character_accuracy("AAAAAAAAAA", "BBBBBBBBBB")
        assert acc == 0.0
    
    def test_partial_match(self):
        """Test accuracy with partial match."""
        # "MH 12 AB 1234" vs "IMH 12 AB 1234" - 1 extra char at start
        # Distance = 1, max_len = 14, accuracy = (1 - 1/14) * 100 = 92.86%
        acc = calculate_character_accuracy("IMH 12 AB 1234", "MH 12 AB 1234")
        assert abs(acc - 92.857) < 0.01


class TestPlateTextNormalization:
    """Test plate text normalization."""
    
    def test_case_normalization(self):
        """Test uppercase conversion."""
        assert normalize_plate_text("mh12ab1234") == "MH12AB1234"
        assert normalize_plate_text("Mh12Ab1234") == "MH12AB1234"
    
    def test_space_normalization(self):
        """Test space normalization."""
        assert normalize_plate_text("MH  12  AB  1234") == "MH 12 AB 1234"
        assert normalize_plate_text("MH   12   AB   1234") == "MH 12 AB 1234"
        assert normalize_plate_text("  MH 12 AB 1234  ") == "MH 12 AB 1234"
    
    def test_combined_normalization(self):
        """Test combined case and space normalization."""
        assert normalize_plate_text("  mh  12  ab  1234  ") == "MH 12 AB 1234"


class TestDetectionMatching:
    """Test detection to ground truth matching."""
    
    def test_perfect_matches(self):
        """Test matching with perfect overlaps."""
        detections = [
            {'bbox': [100, 100, 50, 50]},
            {'bbox': [200, 200, 50, 50]}
        ]
        ground_truth = [
            {'bbox': [100, 100, 50, 50]},
            {'bbox': [200, 200, 50, 50]}
        ]
        
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            detections, ground_truth, iou_threshold=0.5
        )
        
        assert len(matches) == 2
        assert len(unmatched_dets) == 0
        assert len(unmatched_gts) == 0
        assert all(iou >= 0.5 for _, _, iou in matches)
    
    def test_no_matches(self):
        """Test matching with no overlaps."""
        detections = [
            {'bbox': [100, 100, 50, 50]},
        ]
        ground_truth = [
            {'bbox': [500, 500, 50, 50]},
        ]
        
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            detections, ground_truth, iou_threshold=0.5
        )
        
        assert len(matches) == 0
        assert len(unmatched_dets) == 1
        assert len(unmatched_gts) == 1
    
    def test_partial_matches(self):
        """Test matching with some overlaps."""
        detections = [
            {'bbox': [100, 100, 50, 50]},  # Will match gt[0]
            {'bbox': [200, 200, 50, 50]},  # Will match gt[1]
            {'bbox': [300, 300, 50, 50]}   # No match
        ]
        ground_truth = [
            {'bbox': [100, 100, 50, 50]},
            {'bbox': [200, 200, 50, 50]}
        ]
        
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            detections, ground_truth, iou_threshold=0.5
        )
        
        assert len(matches) == 2
        assert len(unmatched_dets) == 1
        assert len(unmatched_gts) == 0
        assert unmatched_dets[0] == 2  # Third detection
    
    def test_threshold_filtering(self):
        """Test that low IoU matches are filtered."""
        detections = [
            {'bbox': [100, 100, 100, 100]},
        ]
        ground_truth = [
            {'bbox': [150, 150, 100, 100]},  # Partial overlap, IoU ~0.14
        ]
        
        # With high threshold, no match
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            detections, ground_truth, iou_threshold=0.5
        )
        assert len(matches) == 0
        assert len(unmatched_dets) == 1
        assert len(unmatched_gts) == 1
        
        # With low threshold, match
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            detections, ground_truth, iou_threshold=0.1
        )
        assert len(matches) == 1
        assert len(unmatched_dets) == 0
        assert len(unmatched_gts) == 0
    
    def test_empty_inputs(self):
        """Test matching with empty inputs."""
        # Empty detections
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            [], [{'bbox': [100, 100, 50, 50]}], iou_threshold=0.5
        )
        assert len(matches) == 0
        assert len(unmatched_dets) == 0
        assert len(unmatched_gts) == 1
        
        # Empty ground truth
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            [{'bbox': [100, 100, 50, 50]}], [], iou_threshold=0.5
        )
        assert len(matches) == 0
        assert len(unmatched_dets) == 1
        assert len(unmatched_gts) == 0
        
        # Both empty
        matches, unmatched_dets, unmatched_gts = match_detections_to_ground_truth(
            [], [], iou_threshold=0.5
        )
        assert len(matches) == 0
        assert len(unmatched_dets) == 0
        assert len(unmatched_gts) == 0


class TestPrecisionRecallF1:
    """Test precision, recall, and F1 calculation."""
    
    def test_perfect_scores(self):
        """Test with perfect detection (no errors)."""
        metrics = calculate_precision_recall_f1(tp=10, fp=0, fn=0)
        assert metrics['precision'] == 1.0
        assert metrics['recall'] == 1.0
        assert metrics['f1'] == 1.0
    
    def test_no_detections(self):
        """Test with no detections (all false negatives)."""
        metrics = calculate_precision_recall_f1(tp=0, fp=0, fn=10)
        assert metrics['precision'] == 0.0
        assert metrics['recall'] == 0.0
        assert metrics['f1'] == 0.0
    
    def test_all_false_positives(self):
        """Test with only false positives."""
        metrics = calculate_precision_recall_f1(tp=0, fp=10, fn=0)
        assert metrics['precision'] == 0.0
        assert metrics['recall'] == 0.0
        assert metrics['f1'] == 0.0
    
    def test_balanced_errors(self):
        """Test with balanced false positives and negatives."""
        # TP=5, FP=5, FN=5
        # Precision = 5/10 = 0.5
        # Recall = 5/10 = 0.5
        # F1 = 2*0.5*0.5/(0.5+0.5) = 0.5
        metrics = calculate_precision_recall_f1(tp=5, fp=5, fn=5)
        assert metrics['precision'] == 0.5
        assert metrics['recall'] == 0.5
        assert metrics['f1'] == 0.5
    
    def test_high_precision_low_recall(self):
        """Test with high precision but low recall."""
        # TP=9, FP=1, FN=10
        # Precision = 9/10 = 0.9
        # Recall = 9/19 ≈ 0.474
        # F1 = 2*0.9*0.474/(0.9+0.474) ≈ 0.621
        metrics = calculate_precision_recall_f1(tp=9, fp=1, fn=10)
        assert abs(metrics['precision'] - 0.9) < 0.001
        assert abs(metrics['recall'] - 0.474) < 0.001
        assert abs(metrics['f1'] - 0.621) < 0.001
    
    def test_low_precision_high_recall(self):
        """Test with low precision but high recall."""
        # TP=9, FP=10, FN=1
        # Precision = 9/19 ≈ 0.474
        # Recall = 9/10 = 0.9
        # F1 ≈ 0.621
        metrics = calculate_precision_recall_f1(tp=9, fp=10, fn=1)
        assert abs(metrics['precision'] - 0.474) < 0.001
        assert abs(metrics['recall'] - 0.9) < 0.001
        assert abs(metrics['f1'] - 0.621) < 0.001


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
