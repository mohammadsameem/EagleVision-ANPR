import json
import cv2
from pathlib import Path

# Video file paths
videos = [
    'data/test_videos/WhatsApp Video 2026-10-30 at 6.25.41 AM.mp4',
    'data/test_videos/WhatsApp Video 2026-10-30 at 6.26.04 AM.mp4',
    'data/test_videos/WhatsApp Video 2026-10-30 at 6.26.23 AM.mp4'
]

print('='*80)
print('VIDEO IDENTITY VERIFICATION')
print('='*80)

# Load metadata
with open('data/test_videos/cctv_videos_metadata.json', 'r') as f:
    metadata = json.load(f)

# Load validation summary
with open('validation_results/cctv_real/combined_summary.json', 'r') as f:
    validation = json.load(f)

video_mapping = {}

for i, video_path in enumerate(videos, 1):
    video_file = Path(video_path)
    filename = video_file.name
    
    print(f'\n{"="*80}')
    print(f'VIDEO FILE: {filename}')
    print(f'{"="*80}')
    
    # Get metadata
    if filename in metadata:
        meta = metadata[filename]
        print(f'\nFile Metadata:')
        print(f'  Resolution: {meta["width"]}×{meta["height"]}')
        print(f'  FPS: {meta["fps"]:.2f}')
        print(f'  Duration: {meta["duration_seconds"]:.2f} seconds')
        print(f'  Total Frames: {meta["frame_count"]}')
        print(f'  File Size: {meta["file_size_mb"]:.2f} MB')
    
    # Match with validation results
    for vid_id in ['video_1', 'video_2', 'video_3']:
        if vid_id in validation['results']:
            val_result = validation['results'][vid_id]
            if val_result['video_name'] == filename:
                print(f'\nValidation Results (Identified as {vid_id}):')
                stats = val_result['statistics']
                print(f'  Frames Processed: {stats["total_frames_processed"]}')
                print(f'  Vehicles Detected: {stats["total_vehicles_detected"]}')
                print(f'  Plates Detected: {stats["total_plates_detected"]}')
                print(f'  Plate Detection Rate: {stats["total_plates_detected"]/stats["total_vehicles_detected"]*100:.1f}%')
                print(f'  Readable OCR Rate: {stats["ocr_readable_rate"]*100:.1f}%')
                print(f'  Processing Time: {val_result["processing_time"]:.1f}s')
                
                if 'plate_sizes' in stats:
                    ps = stats['plate_sizes']
                    print(f'  Mean Plate Size: {ps["mean_width"]:.0f}×{ps["mean_height"]:.0f} pixels')
                
                video_mapping[filename] = {
                    'validation_id': vid_id,
                    'resolution': f'{meta["width"]}×{meta["height"]}',
                    'fps': meta['fps'],
                    'duration': meta['duration_seconds'],
                    'frames_processed': stats['total_frames_processed'],
                    'vehicles': stats['total_vehicles_detected'],
                    'plates': stats['total_plates_detected'],
                    'plate_detection_rate': stats['total_plates_detected']/stats['total_vehicles_detected'],
                    'readable_ocr_rate': stats['ocr_readable_rate']
                }
                
                # Determine scenario
                if stats['total_plates_detected'] / stats['total_vehicles_detected'] > 0.7:
                    scenario = 'REAR-PLATE STATIONARY'
                elif stats['total_plates_detected'] / stats['total_vehicles_detected'] > 0.3:
                    scenario = 'MIXED/UNCLEAR'
                elif stats['total_vehicles_detected'] < 10:
                    scenario = 'NEGATIVE TEST (EMPTY SCENE)'
                else:
                    scenario = 'FRONT-PLATE MOVING'
                
                print(f'  Scenario: {scenario}')

print(f'\n{"="*80}')
print('VIDEO MAPPING SUMMARY')
print(f'{"="*80}\n')

for filename, info in video_mapping.items():
    print(f'{filename}:')
    print(f'  -> {info["validation_id"]}')
    print(f'  -> {info["resolution"]} @ {info["fps"]:.0f}fps')
    print(f'  -> {info["vehicles"]} vehicles, {info["plates"]} plates ({info["plate_detection_rate"]*100:.1f}%)')
    print()

# Save mapping
with open('validation_results/cctv_real/video_identity_mapping.json', 'w') as f:
    json.dump(video_mapping, f, indent=2)

print('Mapping saved to: validation_results/cctv_real/video_identity_mapping.json')
