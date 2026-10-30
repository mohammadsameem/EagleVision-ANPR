"""
Unit tests for character accuracy calculation using Levenshtein distance.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Import the validation script functions
import importlib.util
spec = importlib.util.spec_from_file_location(
    "validate_easyocr",
    "scripts/validate_easyocr.py"
)
validate_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validate_module)

calculate_character_accuracy = validate_module.calculate_character_accuracy
levenshtein_distance = validate_module.levenshtein_distance


class TestLevenshteinDistance:
    """Test Levenshtein edit distance calculation"""
    
    def test_identical_strings(self):
        """Identical strings have distance 0"""
        assert levenshtein_distance("ABC", "ABC") == 0
        assert levenshtein_distance("MH12AB1234", "MH12AB1234") == 0
    
    def test_empty_strings(self):
        """Empty string vs non-empty"""
        assert levenshtein_distance("", "ABC") == 3
        assert levenshtein_distance("ABC", "") == 3
        assert levenshtein_distance("", "") == 0
    
    def test_single_substitution(self):
        """One character substitution"""
        assert levenshtein_distance("ABC", "AXC") == 1
        assert levenshtein_distance("MH12AB1234", "MH12AB1235") == 1
    
    def test_single_insertion(self):
        """One character insertion"""
        assert levenshtein_distance("ABC", "ABXC") == 1
        assert levenshtein_distance("MH12AB1234", "IMH12AB1234") == 1
    
    def test_single_deletion(self):
        """One character deletion"""
        assert levenshtein_distance("ABXC", "ABC") == 1
        assert levenshtein_distance("MH12AB1234", "MH2AB1234") == 1
    
    def test_multiple_edits(self):
        """Multiple edits required"""
        assert levenshtein_distance("ABC", "XYZ") == 3
        # "MH12AB1234" vs "DL01CA5678": both length 10, but some alignment possible
        result = levenshtein_distance("MH12AB1234", "DL01CA5678")
        assert result == 9  # Levenshtein finds optimal path


class TestCharacterAccuracy:
    """Test character accuracy calculation"""
    
    def test_exact_match(self):
        """Exact match should give 100% accuracy"""
        result = calculate_character_accuracy("MH 12 AB 1234", "MH 12 AB 1234")
        assert result["character_accuracy"] == 1.0
        assert result["edit_distance"] == 0
        assert result["cer"] == 0.0
    
    def test_case_insensitive(self):
        """Should be case insensitive after normalization"""
        result = calculate_character_accuracy("MH 12 AB 1234", "mh 12 ab 1234")
        assert result["character_accuracy"] == 1.0
        assert result["edit_distance"] == 0
    
    def test_whitespace_normalization(self):
        """Should normalize whitespace"""
        result = calculate_character_accuracy("MH 12 AB 1234", "MH  12  AB  1234")
        assert result["character_accuracy"] == 1.0
        assert result["edit_distance"] == 0
    
    def test_single_character_insertion(self):
        """Single extra character at start (like 'IMH' instead of 'MH')"""
        result = calculate_character_accuracy("MH 12 AB 1234", "IMH 12 AB 1234")
        # Expected: "MH12AB1234" (10 chars)
        # Actual: "IMH12AB1234" (11 chars)
        # Edit distance: 1 (insertion of 'I')
        # CER = 1/10 = 0.10
        # Accuracy = 1 - 0.10 = 0.90 = 90%
        assert result["edit_distance"] == 1
        assert result["expected_length"] == 10
        assert result["cer"] == 0.1
        assert result["character_accuracy"] == 0.9
    
    def test_single_character_substitution(self):
        """Single character substitution"""
        result = calculate_character_accuracy("MH 12 AB 1234", "MH 12 AB 1235")
        # Edit distance: 1 (substitution)
        # CER = 1/10 = 0.10
        # Accuracy = 90%
        assert result["edit_distance"] == 1
        assert result["character_accuracy"] == 0.9
    
    def test_single_character_deletion(self):
        """Single character deletion"""
        result = calculate_character_accuracy("MH 12 AB 1234", "MH 2 AB 1234")
        # Missing '1' from '12'
        # Edit distance: 1 (deletion)
        assert result["edit_distance"] == 1
        assert result["character_accuracy"] == 0.9
    
    def test_multiple_errors(self):
        """Multiple character errors"""
        result = calculate_character_accuracy("MH 12 AB 1234", "MH 12 AB 123X")
        # One substitution (4 -> X)
        assert result["edit_distance"] == 1
        assert result["character_accuracy"] == 0.9
    
    def test_empty_prediction(self):
        """Empty OCR output"""
        result = calculate_character_accuracy("MH 12 AB 1234", "")
        # All characters wrong
        assert result["edit_distance"] == 10
        assert result["cer"] == 1.0
        assert result["character_accuracy"] == 0.0
    
    def test_completely_wrong(self):
        """Completely different plate"""
        result = calculate_character_accuracy("MH 12 AB 1234", "DL 01 CA 5678")
        # Expected: "MH12AB1234" (10 chars)
        # Actual: "DL01CA5678" (10 chars)
        # Levenshtein finds optimal alignment: 9 edits
        assert result["edit_distance"] == 9
        assert result["cer"] == 0.9
        assert abs(result["character_accuracy"] - 0.1) < 0.001  # Float precision
    
    def test_extra_characters_at_end(self):
        """Extra characters/punctuation at end"""
        result = calculate_character_accuracy("MH 12 AB 1234", "MH 12 AB 1234/")
        # One extra character
        assert result["edit_distance"] == 1
        assert result["character_accuracy"] == 0.9
    
    def test_partial_match(self):
        """Partial plate read"""
        result = calculate_character_accuracy("MH 12 AB 1234", "MH 12 AB")
        # Missing "1234" (4 characters)
        # Edit distance: 4 (deletions)
        assert result["edit_distance"] == 4
        assert result["cer"] == 0.4
        assert result["character_accuracy"] == 0.6
    
    def test_brackets_in_output(self):
        """OCR artifacts like brackets"""
        result = calculate_character_accuracy("MH 12 AB 1234", "[MH 12 AB 1234)")
        # One insertion at start '[', one substitution at end ')' for nothing
        # Expected: "MH12AB1234" (10 chars)
        # Actual: "[MH12AB1234)" (12 chars)
        # Edit distance: 2
        assert result["edit_distance"] == 2
        assert result["cer"] == 0.2
        assert result["character_accuracy"] == 0.8
    
    def test_accuracy_capped_at_one(self):
        """Accuracy should be capped at 1.0"""
        result = calculate_character_accuracy("ABC", "ABC")
        assert result["character_accuracy"] <= 1.0
    
    def test_accuracy_capped_at_zero(self):
        """Accuracy should be capped at 0.0"""
        result = calculate_character_accuracy("A", "XXXXXXXXXX")
        assert result["character_accuracy"] >= 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
