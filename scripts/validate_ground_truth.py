"""
Validate ground truth annotations for quality and consistency.

Checks:
- Required fields present
- Bounding boxes within image boundaries
- Valid enum values
- Vehicle-plate associations
- No duplicate IDs
- Consistent formats
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

class GroundTruthValidator:
    """Validate ground truth annotation JSON."""
    
    VALID_VISIBILITY = {'clear', 'partial', 'occluded', 'blurry', 'small', 'absent'}
    VALID_ORIENTATION = {'front', 'rear', 'side', None}
    VALID_ANNOTATION_STATUS = {'verified', 'uncertain', 'unreadable', 'review_needed'}
    VALID_VEHICLE_CLASSES = {2, 3, 5, 7}  # YOLO COCO classes
    
    def __init__(self, ground_truth_path: str):
        self.path = ground_truth_path
        self.errors = []
        self.warnings = []
        
        # Load ground truth
        try:
            with open(ground_truth_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
        except FileNotFoundError:
            print(f"ERROR: Ground truth file not found: {ground_truth_path}")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON: {e}")
            sys.exit(1)
    
    def error(self, message: str):
        """Record validation error."""
        self.errors.append(message)
    
    def warning(self, message: str):
        """Record validation warning."""
        self.warnings.append(message)
    
    def validate_metadata(self) -> bool:
        """Validate top-level metadata."""
        print("Validating metadata...")
        
        required_fields = ['annotation_set_id', 'annotator', 'annotation_date', 
                          'bounding_box_format', 'frames']
        
        for field in required_fields:
            if field not in self.data:
                self.error(f"Missing required field: {field}")
        
        if self.data.get('bounding_box_format') != '[x_min, y_min, x_max, y_max]':
            self.error(f"Invalid bounding_box_format: {self.data.get('bounding_box_format')}")
        
        if not isinstance(self.data.get('frames'), list):
            self.error("'frames' must be a list")
            return False
        
        return len(self.errors) == 0
    
    def validate_bounding_box(
        self, 
        bbox: List[int], 
        image_width: int, 
        image_height: int,
        label: str
    ) -> bool:
        """
        Validate bounding box coordinates.
        
        Args:
            bbox: [x_min, y_min, x_max, y_max]
            image_width: Image width in pixels
            image_height: Image height in pixels
            label: Label for error messages
        """
        if not isinstance(bbox, list) or len(bbox) != 4:
            self.error(f"{label}: bbox must be list of 4 integers")
            return False
        
        x_min, y_min, x_max, y_max = bbox
        
        # Check types
        if not all(isinstance(v, (int, float)) for v in bbox):
            self.error(f"{label}: bbox coordinates must be numeric")
            return False
        
        # Check order
        if x_max <= x_min:
            self.error(f"{label}: x_max ({x_max}) must be > x_min ({x_min})")
            return False
        
        if y_max <= y_min:
            self.error(f"{label}: y_max ({y_max}) must be > y_min ({y_min})")
            return False
        
        # Check boundaries
        if x_min < 0 or y_min < 0:
            self.error(f"{label}: coordinates must be >= 0")
            return False
        
        if x_max > image_width:
            self.error(f"{label}: x_max ({x_max}) exceeds image width ({image_width})")
            return False
        
        if y_max > image_height:
            self.error(f"{label}: y_max ({y_max}) exceeds image height ({image_height})")
            return False
        
        # Warn if very small
        width = x_max - x_min
        height = y_max - y_min
        if width < 10 or height < 5:
            self.warning(f"{label}: very small bbox ({width}x{height}px)")
        
        return True
    
    def validate_frame(self, frame: Dict, frame_index: int) -> Tuple[Set[str], Set[str]]:
        """
        Validate single frame annotation.
        
        Returns:
            (vehicle_ids, plate_ids) for cross-reference checking
        """
        label_prefix = f"Frame {frame_index}"
        
        # Required frame fields
        required_fields = ['video_id', 'video_filename', 'frame_index', 
                          'timestamp_ms', 'image_width', 'image_height']
        
        for field in required_fields:
            if field not in frame:
                self.error(f"{label_prefix}: missing required field '{field}'")
        
        image_width = frame.get('image_width', 0)
        image_height = frame.get('image_height', 0)
        
        if image_width <= 0 or image_height <= 0:
            self.error(f"{label_prefix}: invalid image dimensions ({image_width}x{image_height})")
        
        # Validate vehicles
        vehicle_ids = set()
        vehicles = frame.get('vehicles', [])
        
        if not isinstance(vehicles, list):
            self.error(f"{label_prefix}: 'vehicles' must be a list")
            vehicles = []
        
        for i, vehicle in enumerate(vehicles):
            v_label = f"{label_prefix}, Vehicle {i}"
            
            # Required vehicle fields
            if 'vehicle_bbox' not in vehicle:
                self.error(f"{v_label}: missing vehicle_bbox")
            else:
                self.validate_bounding_box(
                    vehicle['vehicle_bbox'], 
                    image_width, 
                    image_height,
                    v_label
                )
            
            if 'vehicle_class' not in vehicle:
                self.error(f"{v_label}: missing vehicle_class")
            elif vehicle['vehicle_class'] not in self.VALID_VEHICLE_CLASSES:
                self.error(f"{v_label}: invalid vehicle_class {vehicle['vehicle_class']}")
            
            # Track vehicle IDs
            if 'vehicle_id' in vehicle and vehicle['vehicle_id']:
                vehicle_id = vehicle['vehicle_id']
                if vehicle_id in vehicle_ids:
                    self.error(f"{v_label}: duplicate vehicle_id '{vehicle_id}'")
                vehicle_ids.add(vehicle_id)
        
        # Validate plates
        plate_ids = set()
        plates = frame.get('plates', [])
        
        if not isinstance(plates, list):
            self.error(f"{label_prefix}: 'plates' must be a list")
            plates = []
        
        for i, plate in enumerate(plates):
            p_label = f"{label_prefix}, Plate {i}"
            
            # Required plate fields
            if 'plate_bbox' not in plate:
                self.error(f"{p_label}: missing plate_bbox")
            else:
                self.validate_bounding_box(
                    plate['plate_bbox'],
                    image_width,
                    image_height,
                    p_label
                )
            
            # Validate plate_text
            if 'plate_text' in plate:
                text = plate['plate_text']
                if text is not None:
                    if not isinstance(text, str):
                        self.error(f"{p_label}: plate_text must be string or null")
                    elif len(text) == 0:
                        self.warning(f"{p_label}: plate_text is empty string (should be null)")
                    elif len(text) < 4:
                        self.warning(f"{p_label}: plate_text very short ({len(text)} chars)")
            
            # Validate visibility
            if 'plate_visibility' in plate:
                visibility = plate['plate_visibility']
                if visibility not in self.VALID_VISIBILITY:
                    self.error(f"{p_label}: invalid plate_visibility '{visibility}'")
            
            # Validate orientation
            if 'plate_orientation' in plate:
                orientation = plate['plate_orientation']
                if orientation not in self.VALID_ORIENTATION:
                    self.error(f"{p_label}: invalid plate_orientation '{orientation}'")
            
            # Validate annotation status
            if 'annotation_status' not in plate:
                self.warning(f"{p_label}: missing annotation_status")
            elif plate['annotation_status'] not in self.VALID_ANNOTATION_STATUS:
                self.error(f"{p_label}: invalid annotation_status '{plate['annotation_status']}'")
            
            # Validate vehicle association
            if 'associated_vehicle' in plate:
                assoc_vehicle = plate['associated_vehicle']
                if assoc_vehicle and assoc_vehicle not in vehicle_ids:
                    self.error(f"{p_label}: associated_vehicle '{assoc_vehicle}' not found in frame")
            
            # Track plate IDs
            if 'plate_id' in plate and plate['plate_id']:
                plate_id = plate['plate_id']
                if plate_id in plate_ids:
                    self.error(f"{p_label}: duplicate plate_id '{plate_id}'")
                plate_ids.add(plate_id)
        
        # Validate frame annotation status
        if 'annotation_status' not in frame:
            self.warning(f"{label_prefix}: missing frame annotation_status")
        elif frame['annotation_status'] not in self.VALID_ANNOTATION_STATUS:
            self.error(f"{label_prefix}: invalid annotation_status '{frame['annotation_status']}'")
        
        return vehicle_ids, plate_ids
    
    def validate(self) -> bool:
        """
        Run complete validation.
        
        Returns:
            True if validation passed (no errors)
        """
        print(f"{'='*80}")
        print("GROUND TRUTH VALIDATION")
        print(f"{'='*80}")
        print(f"File: {self.path}\n")
        
        # Validate metadata
        if not self.validate_metadata():
            print("FAILED: Metadata validation failed")
            return False
        
        # Validate each frame
        print(f"Validating {len(self.data['frames'])} frames...")
        
        for i, frame in enumerate(self.data['frames']):
            vehicle_ids, plate_ids = self.validate_frame(frame, i)
        
        # Print results
        print(f"\n{'='*80}")
        print("VALIDATION RESULTS")
        print(f"{'='*80}\n")
        
        if self.errors:
            print(f"❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  - {error}")
            print()
        
        if self.warnings:
            print(f"⚠️  WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()
        
        if not self.errors and not self.warnings:
            print("✅ VALIDATION PASSED - No errors or warnings")
        elif not self.errors:
            print(f"✅ VALIDATION PASSED - {len(self.warnings)} warnings (review recommended)")
        else:
            print(f"❌ VALIDATION FAILED - {len(self.errors)} errors, {len(self.warnings)} warnings")
        
        # Statistics
        total_vehicles = sum(len(f.get('vehicles', [])) for f in self.data['frames'])
        total_plates = sum(len(f.get('plates', [])) for f in self.data['frames'])
        plates_with_text = sum(
            1 for f in self.data['frames'] 
            for p in f.get('plates', []) 
            if p.get('plate_text')
        )
        
        print(f"\n{'='*80}")
        print("ANNOTATION STATISTICS")
        print(f"{'='*80}")
        print(f"Frames: {len(self.data['frames'])}")
        print(f"Vehicles: {total_vehicles}")
        print(f"Plates: {total_plates}")
        print(f"Plates with text: {plates_with_text}/{total_plates} ({plates_with_text/total_plates*100:.1f}%)")
        
        return len(self.errors) == 0


def main():
    """Main validation entry point."""
    ground_truth_path = 'data/annotations/ground_truth.json'
    
    # Check if file exists
    if not Path(ground_truth_path).exists():
        print(f"ERROR: Ground truth file not found: {ground_truth_path}")
        print("\nPlease create ground_truth.json from the template:")
        print("  cp data/annotations/ground_truth_template.json data/annotations/ground_truth.json")
        print("  Then add your annotations to ground_truth.json")
        sys.exit(1)
    
    # Run validation
    validator = GroundTruthValidator(ground_truth_path)
    passed = validator.validate()
    
    # Exit with appropriate code
    sys.exit(0 if passed else 1)


if __name__ == '__main__':
    main()
