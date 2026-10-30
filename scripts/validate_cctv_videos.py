"""
Validate EagleVision ANPR on real CCTV footage.

Processes three real traffic surveillance videos and generates
detailed validation reports for each.
"""
import sys
import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import cv2
import numpy as np

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.anpr_pipeline import ANPRPipeline

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CCTVValidator:
    """Validator for real CCTV footage."""
    
    def __init__(self, output_dir: Path):
        """Initialize validator."""
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize ANPR pipeline with preprocessing enabled
        logger.info("Initializing ANPR pipeline...")
        config = {
            "vehicle_model": "yolov8n.pt",
            "use_gpu": False,
            "confidence_threshold": 0.70
        }
        self.pipeline = ANPRPipeline(config=config)
        logger.info("✅ ANPR pipeline ready")
    
    def process_video(
        self,
        video_path: Path,
        video_id: str,
        target_fps: int = 5,
        save_annotations: bool = True
    ) -> Dict:
        """
        Process a single CCTV video.
        
        Args:
            video_path: Path to video file
            video_id: Unique identifier for this video (e.g., "video_1")
            target_fps: FPS for frame sampling
            save_annotations: Whether to save annotated frames
        
        Returns:
            Processing results dict
        """
        logger.info(f"\n{'='*100}")
        logger.info(f"Processing {video_id}: {video_path.name}")
        logger.info(f"{'='*100}\n")
        
        # Create output subdirectory
        video_output_dir = self.output_dir / video_id
        video_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        frames_dir = video_output_dir / "annotated_frames"
        crops_dir = video_output_dir / "plate_crops"
        frames_dir.mkdir(exist_ok=True)
        crops_dir.mkdir(exist_ok=True)
        
        start_time = time.time()
        
        # Process video
        try:
            results = self.pipeline.process_video(
                str(video_path),
                fps=target_fps
            )
        except Exception as e:
            logger.error(f"❌ Failed to process video: {e}")
            return {
                "video_id": video_id,
                "error": str(e),
                "processing_time": time.time() - start_time
            }
        
        processing_time = time.time() - start_time
        
        # Extract statistics
        stats = self._calculate_statistics(results)
        
        # Save annotated frames and crops
        if save_annotations:
            self._save_annotated_frames(
                video_path,
                results,
                frames_dir,
                crops_dir
            )
        
        # Compile output
        output = {
            "video_id": video_id,
            "video_path": str(video_path),
            "video_name": video_path.name,
            "processing_time": processing_time,
            "target_fps": target_fps,
            "statistics": stats,
            "frames": results,
            "configuration": {
                "vehicle_model": "yolov8n.pt",
                "plate_model": "plate_detector.pt",
                "ocr_preprocessing_enabled": True,
                "ocr_method": "Lanczos4",
                "gpu_enabled": False
            }
        }
        
        # Save results
        results_file = video_output_dir / f"{video_id}_results.json"
        with open(results_file, 'w') as f:
            # Convert numpy types for JSON serialization
            json.dump(output, f, indent=2, default=self._json_converter)
        
        logger.info(f"\n✅ {video_id} processing complete")
        logger.info(f"   Processing time: {processing_time:.2f}s")
        logger.info(f"   Results saved to: {results_file}")
        
        return output
    
    def _calculate_statistics(self, results: List[Dict]) -> Dict:
        """Calculate statistics from processing results."""
        total_frames = len(set(r.get("frame_index", -1) for r in results))
        frames_with_vehicles = len(set(r.get("frame_index", -1) for r in results if r.get("vehicle_bbox")))
        frames_with_plates = len(set(r.get("frame_index", -1) for r in results if r.get("plate_bbox")))
        total_vehicles = len(results)
        total_plates = sum(1 for r in results if r.get("plate_bbox"))
        total_ocr_readable = 0
        total_ocr_empty = 0
        
        plate_sizes = []
        ocr_confidences = []
        preprocessing_applied_count = 0
        preprocessing_flagged_unreadable = 0
        
        for detection in results:
            # Plate size
            plate_bbox = detection.get("plate_bbox")
            if plate_bbox:
                _, _, pw, ph = plate_bbox
                if pw > 0 and ph > 0:
                    plate_sizes.append((pw, ph))
            
            # OCR results
            ocr = detection.get("ocr_result")
            if ocr:
                text = ocr.get("final_text", "")
                if text and text != "UNREADABLE":
                    total_ocr_readable += 1
                    
                    # Confidence
                    conf = ocr.get("easyocr_conf") or ocr.get("paddleocr_conf") or 0
                    if conf > 0:
                        ocr_confidences.append(conf)
                else:
                    total_ocr_empty += 1
                
                # Preprocessing info
                preproc = ocr.get("preprocessing", {})
                if preproc.get("preprocessed"):
                    preprocessing_applied_count += 1
                if preproc.get("likely_unreadable"):
                    preprocessing_flagged_unreadable += 1
        
        stats = {
            "total_frames_processed": total_frames,
            "frames_with_vehicles": frames_with_vehicles,
            "frames_with_plates": frames_with_plates,
            "total_vehicles_detected": total_vehicles,
            "total_plates_detected": total_plates,
            "ocr_readable_count": total_ocr_readable,
            "ocr_empty_count": total_ocr_empty,
            "ocr_readable_rate": total_ocr_readable / total_plates if total_plates > 0 else 0,
            "preprocessing_applied_count": preprocessing_applied_count,
            "preprocessing_flagged_unreadable_count": preprocessing_flagged_unreadable,
            "plate_sizes": {
                "count": len(plate_sizes),
                "mean_width": float(np.mean([w for w, h in plate_sizes])) if plate_sizes else 0,
                "mean_height": float(np.mean([h for w, h in plate_sizes])) if plate_sizes else 0,
                "min_width": int(min([w for w, h in plate_sizes])) if plate_sizes else 0,
                "max_width": int(max([w for w, h in plate_sizes])) if plate_sizes else 0,
                "min_height": int(min([h for w, h in plate_sizes])) if plate_sizes else 0,
                "max_height": int(max([h for w, h in plate_sizes])) if plate_sizes else 0
            },
            "ocr_confidence": {
                "count": len(ocr_confidences),
                "mean": float(np.mean(ocr_confidences)) if ocr_confidences else 0,
                "min": float(min(ocr_confidences)) if ocr_confidences else 0,
                "max": float(max(ocr_confidences)) if ocr_confidences else 0
            }
        }
        
        return stats
    
    def _save_annotated_frames(
        self,
        video_path: Path,
        results: List[Dict],
        frames_dir: Path,
        crops_dir: Path
    ):
        """Save annotated frames and plate crops."""
        cap = cv2.VideoCapture(str(video_path))
        
        if not cap.isOpened():
            logger.warning(f"Failed to open video for annotation: {video_path}")
            return
        
        saved_frame_count = 0
        saved_crop_count = 0
        
        # Group detections by frame
        frames_dict = {}
        for detection in results:
            frame_idx = detection.get("frame_index")
            if frame_idx not in frames_dict:
                frames_dict[frame_idx] = []
            frames_dict[frame_idx].append(detection)
        
        for frame_idx, detections in frames_dict.items():
            if not detections:
                continue
            
            # Seek to frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = cap.read()
            
            if not ret:
                continue
            
            # Draw annotations
            annotated = frame.copy()
            
            for detection in detections:
                # Draw vehicle bbox
                vehicle_bbox = detection.get("vehicle_bbox")
                if vehicle_bbox:
                    vx, vy, vw, vh = vehicle_bbox
                    x1, y1, x2, y2 = vx, vy, vx+vw, vy+vh
                    
                    cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Add vehicle label
                    vehicle_conf = detection.get("vehicle_confidence", 0)
                    label = f"Vehicle {vehicle_conf:.2f}"
                    cv2.putText(annotated, label, (x1, y1-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                    
                    # Draw plate bbox and save crop
                    plate_bbox = detection.get("plate_bbox")
                    if plate_bbox:
                        px, py, pw, ph = plate_bbox
                        # Plate bbox is relative to vehicle crop
                        abs_px1 = vx + px
                        abs_py1 = vy + py
                        abs_px2 = abs_px1 + pw
                        abs_py2 = abs_py1 + ph
                        
                        cv2.rectangle(annotated, (abs_px1, abs_py1), (abs_px2, abs_py2), (0, 0, 255), 2)
                        
                        # Add OCR text if available
                        ocr = detection.get("ocr_result")
                        if ocr:
                            text = ocr.get("final_text", "")
                            if text:
                                cv2.putText(annotated, text, (abs_px1, abs_py1-10),
                                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                        
                        # Save plate crop
                        if abs_px2 > abs_px1 and abs_py2 > abs_py1 and abs_py2 <= frame.shape[0] and abs_px2 <= frame.shape[1]:
                            crop = frame[abs_py1:abs_py2, abs_px1:abs_px2]
                            vehicle_id = f"v{hash(str(vehicle_bbox)) % 10000}"
                            crop_file = crops_dir / f"frame_{frame_idx:04d}_{vehicle_id}_plate.jpg"
                            cv2.imwrite(str(crop_file), crop)
                            saved_crop_count += 1
            
            # Save annotated frame
            timestamp = detections[0].get("timestamp_ms", 0)
            frame_file = frames_dir / f"frame_{frame_idx:04d}_t{int(timestamp)}ms.jpg"
            cv2.imwrite(str(frame_file), annotated)
            saved_frame_count += 1
        
        cap.release()
        
        logger.info(f"   Saved {saved_frame_count} annotated frames")
        logger.info(f"   Saved {saved_crop_count} plate crops")
    
    def _json_converter(self, obj):
        """Convert numpy types to JSON-serializable types."""
        if isinstance(obj, (np.integer, np.floating)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif hasattr(obj, '__dict__'):
            return str(obj)
        return obj


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate ANPR on real CCTV videos')
    parser.add_argument('--output-dir', type=str, default='validation_results/cctv_real',
                       help='Output directory for results')
    parser.add_argument('--target-fps', type=int, default=5,
                       help='FPS for frame sampling')
    
    args = parser.parse_args()
    
    # Setup
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    videos_dir = Path("data/test_videos")
    
    # Find CCTV videos
    video_files = [
        ("video_1", videos_dir / "WhatsApp Video 2026-10-30 at 6.25.41 AM.mp4"),
        ("video_2", videos_dir / "WhatsApp Video 2026-10-30 at 6.26.23 AM.mp4"),
        ("video_3", videos_dir / "WhatsApp Video 2026-10-30 at 6.26.04 AM.mp4")
    ]
    
    # Verify all videos exist
    for video_id, video_path in video_files:
        if not video_path.exists():
            logger.error(f"❌ Video not found: {video_path}")
            sys.exit(1)
    
    logger.info(f"Found {len(video_files)} CCTV videos to process")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"Target FPS: {args.target_fps}")
    
    # Initialize validator
    validator = CCTVValidator(output_dir)
    
    # Process each video
    all_results = {}
    
    for video_id, video_path in video_files:
        try:
            result = validator.process_video(
                video_path,
                video_id,
                target_fps=args.target_fps,
                save_annotations=True
            )
            all_results[video_id] = result
        except Exception as e:
            logger.error(f"❌ Failed to process {video_id}: {e}")
            import traceback
            traceback.print_exc()
    
    # Save combined summary
    summary_file = output_dir / "combined_summary.json"
    with open(summary_file, 'w') as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "videos_processed": len(all_results),
            "results": all_results
        }, f, indent=2, default=validator._json_converter)
    
    logger.info(f"\n{'='*100}")
    logger.info(f"✅ Validation complete")
    logger.info(f"   Videos processed: {len(all_results)}")
    logger.info(f"   Summary saved to: {summary_file}")
    logger.info(f"{'='*100}\n")
    
    # Print summary
    print("\n" + "="*100)
    print("CCTV VIDEO VALIDATION SUMMARY")
    print("="*100)
    
    for video_id, result in all_results.items():
        if "error" in result:
            print(f"\n❌ {video_id}: {result['error']}")
            continue
        
        stats = result.get("statistics", {})
        print(f"\n📹 {video_id}: {result['video_name']}")
        print(f"   Processing time: {result['processing_time']:.2f}s")
        print(f"   Frames processed: {stats.get('total_frames_processed', 0)}")
        print(f"   Vehicles detected: {stats.get('total_vehicles_detected', 0)}")
        print(f"   Plates detected: {stats.get('total_plates_detected', 0)}")
        print(f"   OCR readable: {stats.get('ocr_readable_count', 0)}/{stats.get('total_plates_detected', 0)}")
        print(f"   Preprocessing applied: {stats.get('preprocessing_applied_count', 0)}")
    
    print("\n" + "="*100)


if __name__ == '__main__':
    main()
