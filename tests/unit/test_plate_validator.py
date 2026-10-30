"""
Test Indian license plate format validation.
"""
import pytest
from src.plate_validator import validate_indian_plate_format, normalize_plate_text

def test_normalize_plate_text():
    """Test plate text normalization"""
    assert normalize_plate_text("tn 09 ab 1234") == "TN 09 AB 1234"
    assert normalize_plate_text("KA01CD5678") == "KA01CD5678"
    assert normalize_plate_text("  TN  09  AB  1234  ") == "TN 09 AB 1234"
    assert normalize_plate_text("") == ""

def test_valid_plate_formats():
    """Test valid Indian plate formats"""
    # Standard format: XX 00 XX 0000
    assert validate_indian_plate_format("TN 09 AB 1234") == True
    assert validate_indian_plate_format("KA 01 CD 5678") == True
    assert validate_indian_plate_format("MH 12 EF 9012") == True
    
    # Without spaces
    assert validate_indian_plate_format("TN09AB1234") == True
    assert validate_indian_plate_format("KA01CD5678") == True
    
    # Single letter variant: XX 00 X 0000
    assert validate_indian_plate_format("TN 09 A 1234") == True
    assert validate_indian_plate_format("KA01X5678") == True
    
    # Older format: XX 00 0000
    assert validate_indian_plate_format("TN 09 1234") == True
    assert validate_indian_plate_format("KA011234") == True

def test_invalid_plate_formats():
    """Test invalid formats are rejected"""
    assert validate_indian_plate_format("INVALID") == False
    assert validate_indian_plate_format("123456") == False
    assert validate_indian_plate_format("TN091") == False
    assert validate_indian_plate_format("") == False
    assert validate_indian_plate_format("ABC DEF GHI") == False

def test_case_insensitive_validation():
    """Test validation works regardless of case"""
    assert validate_indian_plate_format("tn 09 ab 1234") == True
    assert validate_indian_plate_format("Tn 09 Ab 1234") == True
    assert validate_indian_plate_format("TN 09 AB 1234") == True
