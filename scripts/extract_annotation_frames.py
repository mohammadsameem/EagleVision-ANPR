"""
Extract frames for manual annotation from processed CCTV videos.

Creates annotated frames with detector predictions overlaid for reference.
Saves to data/annotations/frames/ for human review.
"""

import json
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

def draw_detection_overlay(
    image: np.ndarray,
    detection: Dict,
    show_ocr: bool = True
) -> np.ndarray:
    """
    Draw detector predictions on frame for reference.
    
    Args:
        image: Frame image
        detection: Detection data from validation results
        show_ocr: Whether to display OCR predictions
        
    Returns:
        Image with overlays
    """
    img = image.copy()
    h, w = img.shape[:2]
    
    # Draw vehicle bounding box (green)
    if detection.get('vehicle_bbox'):
        vx, vy, vw, vh = detection['vehicle_bbox']
        # Convert from [x, y, w, h] to pixel coordinates
        x1, y1 = int(vx), int(vy)
        x2, y2 = int(vx + vw), int(vy + vh)
        
        # Validate coordinates
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
        
        # Draw label
        conf = detection.get('vehicle_confidence', 0)
        vclass = detection.get('vehicle_class', 2)
        class_names = {2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}
        label = f"{class_names.get(vclass, 'vehicle')} {conf:.2f}"
        cv2.putText(img, label, (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, (0, 255, 0), 1)
    
    # Draw plate bounding box (blue)
    if detection.get('plate_bbox'):
        px, py, pw, ph = detection['plate_bbox']
        # Convert from [x, y, w, h] relative to vehicle crop to full frame
        # Need to offset by vehicle position
        if detection.get('vehicle_bbox'):
            vx, vy = detection['vehicle_bbox'][:2]
            x1, y1 = int(vx + px), int(vy + py)
            x2, y2 = int(vx + px + pw), int(vy + py + ph)
        else:
            x1, y1 = int(px), int(py)
            x2, y2 = int(px + pw), int(py + ph)
        
        # Validate coordinates
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        
        # Draw OCR prediction if available and requested
        if show_ocr and detection.get('ocr_result'):
            ocr_text = detection['ocr_result'].get('final_text', '')
            ocr_conf = detection['ocr_result'].get('easyocr_conf', 0)
            
            if ocr_text:
                # Red text for OCR (to distinguish from ground truth)
                label = f"OCR: {ocr_text} ({ocr_conf:.2f})"
                cv2.putText(img, label, (x1, y2+15), cv2.FONT_HERSHEY_SIMPLEX,
                           0.4, (0, 0, 255), 1)
    
    # Add watermark indicating these are detector predictions
    cv2.putText(img, "DETECTOR PREDICTIONS (NOT GROUND TRUTH)", 
               (10, h-10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    
    return img


def extract_annotation_frames(
    annotation_list_path: str = 'data/annotations/annotation_frame_list.json',
    output_dir: str = 'data/annotations/frames',
    show_ocr_predictions: bool = True
):
    """
    Extract frames for annotation from videos.
    
    Args:
        annotation_list_path: Path to annotation frame list JSON
        output_dir: Output directory for extracted frames
        show_ocr_predictions: Whether to overlay OCR predictions (for reference)
    """
    
    # Load annotation frame list
    print("Loading annotation frame list...")
    with open(annotation_list_path, 'r') as f:
        annotation_data = json.load(f)
    
    frames_to_extract = annotation_data['frames']
    print(f"Total frames to extract: {len(frames_to_extract)}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Group by video for efficient processing
    frames_by_video = {}
    for frame_data in frames_to_extract:
        video_id = frame_data['video_id']
        if video_id not in frames_by_video:
            frames_by_video[video_id] = []
        frames_by_video[video_id].append(frame_data)
    
    # Process each video
    total_extracted = 0
    
    for video_id, frames in frames_by_video.items():
        print(f"\nProcessing {video_id}...")
        print(f"  Frames to extract: {len(frames)}")
        
        # Get video path from first frame
        video_filename = frames[0]['video_filename']
        video_path = f'data/test_videos/{video_filename}'
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"  ERROR: Could not open video: {video_path}")
            continue
        
        video_fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        print(f"  Video: {video_filename}")
        print(f"  FPS: {video_fps:.2f}, Total frames: {total_frames}")
        
        # Sort frames by index for efficient seeking
        frames_sorted = sorted(frames, key=lambda x: x['frame_index'])
        
        for frame_data in frames_sorted:
            frame_idx = frame_data['frame_index']
            timestamp_ms = frame_data['timestamp_ms']
            detection = frame_data['detection']
            
            # Seek to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                print(f"  WARNING: Could not read frame {frame_idx}")
                continue
            
            # Draw detection overlay
            annotated_frame = draw_detection_overlay(
                frame, 
                detection, 
                show_ocr=show_ocr_predictions
            )
            
            # Save frame
            output_filename = f"{video_id}_frame_{frame_idx:06d}.jpg"
            output_filepath = output_path / output_filename
            cv2.imwrite(str(output_filepath), annotated_frame)
            
            total_extracted += 1
            
            if total_extracted % 10 == 0:
                print(f"  Extracted {total_extracted} frames...")
        
        cap.release()
        print(f"  Completed {video_id}: {len(frames)} frames extracted")
    
    print(f"\n{'='*80}")
    print(f"EXTRACTION COMPLETE")
    print(f"{'='*80}")
    print(f"Total frames extracted: {total_extracted}")
    print(f"Output directory: {output_dir}")
    print(f"\nNext steps:")
    print(f"1. Review frames in {output_dir}/")
    print(f"2. Create ground_truth.json using the template")
    print(f"3. Annotate vehicles and plates manually")
    print(f"4. Run validation: python scripts/validate_ground_truth.py")


if __name__ == '__main__':
    extract_annotation_frames()
