"""
Hybrid OCR engine using PaddleOCR (primary) and EasyOCR (fallback).
Preserves both outputs and flags disagreements for human review.
Supports configurable preprocessing for small plate crops.
"""
import numpy as np
import cv2
import logging
import os
from typing import Optional, Dict, Tuple
from src.plate_validator import validate_indian_plate_format, normalize_plate_text

logger = logging.getLogger(__name__)

# Try to import OCR engines
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    logger.warning("PaddleOCR not available")

try:
    import easyocr
    EASY_AVAILABLE = True
except ImportError:
    EASY_AVAILABLE = False
    logger.warning("EasyOCR not available")

class HybridOCREngine:
    """
    Hybrid OCR using PaddleOCR (primary) and EasyOCR (fallback).
    Preserves both outputs and compares results.
    Supports configurable preprocessing for small plate crops.
    """
    
    def __init__(self, use_gpu: bool = False, enable_preprocessing: bool = True):
        """
        Initialize OCR engines.
        
        Args:
            use_gpu: Use GPU acceleration if available
            enable_preprocessing: Enable upscaling preprocessing for small crops
        """
        self.paddle = None
        self.easy = None
        
        # Preprocessing configuration
        self.enable_preprocessing = enable_preprocessing
        self._load_preprocessing_config()
        
        logger.info("Initializing OCR engines...")
        if self.enable_preprocessing:
            logger.info(
                f"Preprocessing enabled: upscale crops between "
                f"{self.min_width}x{self.min_height} and "
                f"{self.max_width}x{self.max_height} pixels"
            )
        
        # Initialize PaddleOCR
        if PADDLE_AVAILABLE:
            try:
                # PaddleOCR 3.7.0+ doesn't support show_log or use_gpu parameters  
                # in the constructor - they're set differently now
                self.paddle = PaddleOCR(
                    use_angle_cls=True,
                    lang='en'
                )
                logger.info("✅ PaddleOCR initialized")
            except Exception as e:
                logger.error(f"PaddleOCR initialization failed: {e}")
                logger.info("⚠️  Continuing with EasyOCR only")
                self.paddle = None
        else:
            logger.warning("⚠️  PaddleOCR not installed. Install with: pip install paddleocr")
        
        # Initialize EasyOCR
        if EASY_AVAILABLE:
            try:
                self.easy = easyocr.Reader(['en'], gpu=use_gpu, verbose=False)
                logger.info("✅ EasyOCR initialized")
            except Exception as e:
                logger.error(f"EasyOCR initialization failed: {e}")
                self.easy = None
        else:
            logger.warning("⚠️  EasyOCR not installed. Install with: pip install easyocr")
        
        if not self.paddle and not self.easy:
            logger.error("❌ No OCR engines available! Install at least one.")
    
    def _load_preprocessing_config(self):
        """Load preprocessing configuration from environment or defaults."""
        # Minimum dimensions to trigger upscaling
        self.min_width = int(os.getenv('OCR_PREPROCESS_MIN_WIDTH', '60'))
        self.min_height = int(os.getenv('OCR_PREPROCESS_MIN_HEIGHT', '15'))
        
        # Maximum dimensions to apply upscaling (don't upscale already large crops)
        self.max_width = int(os.getenv('OCR_PREPROCESS_MAX_WIDTH', '150'))
        self.max_height = int(os.getenv('OCR_PREPROCESS_MAX_HEIGHT', '60'))
        
        # Target height for upscaling
        self.target_height = int(os.getenv('OCR_PREPROCESS_TARGET_HEIGHT', '60'))
        
        # Upscaling method: 'lanczos' or 'cubic'
        self.upscale_method = os.getenv('OCR_PREPROCESS_METHOD', 'lanczos').lower()
        
        # Very small crops threshold (likely unreadable)
        self.unreadable_width = int(os.getenv('OCR_PREPROCESS_UNREADABLE_WIDTH', '40'))
        self.unreadable_height = int(os.getenv('OCR_PREPROCESS_UNREADABLE_HEIGHT', '10'))
    
    def _preprocess_plate_crop(
        self, 
        plate_crop: np.ndarray
    ) -> Tuple[np.ndarray, Dict[str, any]]:
        """
        Preprocess plate crop with upscaling if needed.
        
        Args:
            plate_crop: Original plate crop image
        
        Returns:
            (preprocessed_image, preprocessing_metadata)
        """
        h, w = plate_crop.shape[:2]
        
        metadata = {
            'original_width': w,
            'original_height': h,
            'preprocessed': False,
            'method': None,
            'upscaled_width': None,
            'upscaled_height': None,
            'likely_unreadable': False
        }
        
        # Check if crop is extremely small (likely unreadable)
        if w < self.unreadable_width or h < self.unreadable_height:
            logger.warning(
                f"Crop too small ({w}×{h}px), likely unreadable "
                f"(minimum: {self.unreadable_width}×{self.unreadable_height}px)"
            )
            metadata['likely_unreadable'] = True
            return plate_crop, metadata
        
        # Check if crop should be upscaled
        if (w < self.max_width or h < self.max_height) and (w >= self.min_width and h >= self.min_height):
            # Calculate scale to reach target height
            scale = self.target_height / h
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            # Apply upscaling
            if self.upscale_method == 'lanczos':
                upscaled = cv2.resize(
                    plate_crop,
                    (new_w, new_h),
                    interpolation=cv2.INTER_LANCZOS4
                )
                method_name = 'lanczos4'
            else:  # cubic
                upscaled = cv2.resize(
                    plate_crop,
                    (new_w, new_h),
                    interpolation=cv2.INTER_CUBIC
                )
                method_name = 'cubic'
            
            metadata.update({
                'preprocessed': True,
                'method': method_name,
                'upscaled_width': new_w,
                'upscaled_height': new_h
            })
            
            logger.debug(f"Upscaled crop from {w}×{h} to {new_w}×{new_h} using {method_name}")
            
            return upscaled, metadata
        
        # No preprocessing needed
        return plate_crop, metadata
    
    def recognize(
        self, 
        plate_crop: np.ndarray, 
        confidence_threshold: float = 0.70,
        preserve_original: bool = True
    ) -> dict:
        """
        Recognize plate text using hybrid approach with optional preprocessing.
        
        Args:
            plate_crop: BGR/RGB image of license plate
            confidence_threshold: Minimum confidence for auto-acceptance
            preserve_original: Whether to preserve original crop in results
        
        Returns:
            dict with:
                - paddleocr_text: str or None
                - paddleocr_conf: float or None
                - easyocr_text: str or None
                - easyocr_conf: float or None
                - final_text: str (best result or "UNREADABLE")
                - final_engine: str ("paddleocr", "easyocr", or "unreadable")
                - format_valid: bool
                - needs_review: bool
                - agreement: bool or None (if both engines ran)
                - preprocessing: dict (metadata about preprocessing applied)
                - original_crop: np.ndarray (if preserve_original=True)
        """
        result = {
            "paddleocr_text": None,
            "paddleocr_conf": None,
            "easyocr_text": None,
            "easyocr_conf": None,
            "final_text": "UNREADABLE",
            "final_engine": "unreadable",
            "format_valid": False,
            "needs_review": True,
            "agreement": None,
            "preprocessing": {
                'enabled': self.enable_preprocessing,
                'applied': False
            }
        }
        
        # Preserve original crop if requested
        if preserve_original:
            result["original_crop"] = plate_crop.copy()
        
        # Apply preprocessing if enabled
        if self.enable_preprocessing:
            processed_crop, preprocess_meta = self._preprocess_plate_crop(plate_crop)
            result["preprocessing"].update(preprocess_meta)
            
            # Flag for review if crop is likely unreadable
            if preprocess_meta['likely_unreadable']:
                result["needs_review"] = True
        else:
            processed_crop = plate_crop
        
        # Try PaddleOCR first (using preprocessed crop)
        if self.paddle:
            paddle_result = self._recognize_paddle(processed_crop)
            result["paddleocr_text"] = paddle_result["text"]
            result["paddleocr_conf"] = paddle_result["confidence"]
            
            # Check if PaddleOCR result is good enough
            if paddle_result["text"] and paddle_result["confidence"] >= confidence_threshold:
                if validate_indian_plate_format(paddle_result["text"]):
                    result["final_text"] = paddle_result["text"]
                    result["final_engine"] = "paddleocr"
                    result["format_valid"] = True
                    result["needs_review"] = False
                    return result
        
        # Try EasyOCR as fallback (using preprocessed crop)
        if self.easy:
            easy_result = self._recognize_easyocr(processed_crop)
            result["easyocr_text"] = easy_result["text"]
            result["easyocr_conf"] = easy_result["confidence"]
            
            # Compare results if both available
            if result["paddleocr_text"] and result["easyocr_text"]:
                paddle_norm = normalize_plate_text(result["paddleocr_text"])
                easy_norm = normalize_plate_text(result["easyocr_text"])
                result["agreement"] = (paddle_norm == easy_norm)
                
                # ALWAYS flag disagreement for review, regardless of confidence
                if not result["agreement"]:
                    result["needs_review"] = True
                    logger.info(
                        f"OCR disagreement - Paddle: '{result['paddleocr_text']}' "
                        f"vs Easy: '{result['easyocr_text']}'"
                    )
            
            # Use EasyOCR if better confidence or PaddleOCR failed
            if easy_result["text"] and (result["easyocr_conf"] or 0) > (result["paddleocr_conf"] or 0):
                result["final_text"] = easy_result["text"]
                result["final_engine"] = "easyocr"
                result["format_valid"] = validate_indian_plate_format(easy_result["text"])
                
                # Flag for review if:
                # - Low confidence, OR
                # - Invalid format, OR  
                # - Disagreement with other engine (already set above)
                if (easy_result["confidence"] < confidence_threshold or 
                    not result["format_valid"]):
                    result["needs_review"] = True
                elif not result["agreement"] and result["paddleocr_text"]:
                    # Disagreement already flagged above
                    result["needs_review"] = True
                else:
                    # High confidence, valid format, and agreement (or no Paddle result)
                    result["needs_review"] = False
        
        # If we have PaddleOCR result but it's low confidence or invalid format
        if result["final_text"] == "UNREADABLE" and result["paddleocr_text"]:
            result["final_text"] = result["paddleocr_text"]
            result["final_engine"] = "paddleocr"
            result["format_valid"] = validate_indian_plate_format(result["paddleocr_text"])
            result["needs_review"] = True
        
        return result
    
    def _recognize_paddle(self, plate_crop: np.ndarray) -> dict:
        """Run PaddleOCR and extract text with confidence"""
        try:
            results = self.paddle.ocr(plate_crop, cls=True)
            
            if not results or not results[0]:
                return {"text": "", "confidence": 0.0}
            
            # Combine all detected text
            texts = []
            confidences = []
            for line in results[0]:
                text = line[1][0]
                conf = line[1][1]
                texts.append(text)
                confidences.append(conf)
            
            combined_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                "text": combined_text.strip(),
                "confidence": float(avg_confidence)
            }
            
        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
            return {"text": "", "confidence": 0.0}
    
    def _recognize_easyocr(self, plate_crop: np.ndarray) -> dict:
        """Run EasyOCR and extract text with confidence"""
        try:
            results = self.easy.readtext(plate_crop)
            
            if not results:
                return {"text": "", "confidence": 0.0}
            
            # Combine all detected text
            texts = []
            confidences = []
            for (bbox, text, conf) in results:
                texts.append(text)
                confidences.append(conf)
            
            combined_text = " ".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
            
            return {
                "text": combined_text.strip(),
                "confidence": float(avg_confidence)
            }
            
        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
            return {"text": "", "confidence": 0.0}
