"""
Indian license plate format validation.
"""
import re

# Indian plate patterns
INDIAN_PLATE_PATTERNS = [
    r'^[A-Z]{2}\s?\d{2}\s?[A-Z]{1,2}\s?\d{4}$',  # TN 09 AB 1234
    r'^[A-Z]{2}\s?\d{2}\s?\d{4}$',  # TN 09 1234 (older format)
]

def validate_indian_plate_format(text: str) -> bool:
    """
    Check if text matches Indian license plate format.
    
    Args:
        text: Plate text to validate
        
    Returns:
        True if matches Indian plate format, False otherwise
    """
    if not text:
        return False
    
    normalized = normalize_plate_text(text)
    return any(re.match(pattern, normalized) for pattern in INDIAN_PLATE_PATTERNS)

def normalize_plate_text(text: str) -> str:
    """
    Normalize plate text for comparison.
    - Convert to uppercase
    - Collapse multiple spaces to single space
    - Strip leading/trailing whitespace
    
    Args:
        text: Raw plate text
        
    Returns:
        Normalized plate text
    """
    if not text:
        return ""
    
    return re.sub(r'\s+', ' ', text.upper().strip())
