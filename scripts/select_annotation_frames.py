import json
import cv2
import numpy as np
from pathlib import Path
import random

# Create annotations directory
Path('data/annotations').mkdir(parents=True, exist_ok=True)

# Load validation results
with open('validation_results/cctv_real/combined_summary.json', 'r') as f:
    validation = json.load(f)

print('='*80)
print('ANNOTATION FRAME SELECTION')
print('='*80)

annotation_frames = []
total_selected = 0

for video_id in ['video_1', 'video_2', 'video_3']:
    val_result = validation['results'][video_id]
    video_name = val_result['video_name']
    stats = val_result['statistics']
    
    print(f'\n{"="*80}')
    print(f'{video_id.upper()}: {video_name}')
    print(f'{"="*80}')
    print(f'Total Frames Available: {stats["total_frames_processed"]}')
    print(f'Vehicles: {stats["total_vehicles_detected"]}, Plates: {stats["total_plates_detected"]}')
    
    # Load full results
    results_path = f'validation_results/cctv_real/{video_id}/{video_id}_results.json'
    with open(results_path, 'r') as f:
        full_results = json.load(f)
    
    # Use 'frames' key which contains list of detections per frame
    frames_list = full_results['frames']
    
    # Selection strategy based on video type
    if video_id == 'video_1':
        # Rear-plate stationary: select diverse frames across timeline
        target = 30
        strategy = 'diverse_timeline'
        step = max(1, len(frames_list) // target)
        selected_frames = frames_list[::step][:target]
        
    elif video_id == 'video_2':
        # Front-plate moving: select frames with plates + some without
        target = 40
        strategy = 'plate_focused'
        frames_with_plates = [f for f in frames_list if f.get('plate_bbox') is not None]
        frames_without_plates = [f for f in frames_list if f.get('plate_bbox') is None]
        
        # Sample 30 with plates
        if len(frames_with_plates) > 30:
            step = len(frames_with_plates) // 30
            selected_with_plates = frames_with_plates[::step][:30]
        else:
            selected_with_plates = frames_with_plates
        
        # Sample 10 without plates
        selected_without_plates = random.sample(frames_without_plates, min(10, len(frames_without_plates)))
        
        selected_frames = sorted(selected_with_plates + selected_without_plates, key=lambda x: x['frame_index'])
        
    else:  # video_3
        # Negative test: all frames (only 120 frames total, 4 with detections)
        target = 120  # Use all frames since it's a negative test
        strategy = 'all_frames'
        selected_frames = frames_list
    
    print(f'\nSelection Strategy: {strategy}')
    print(f'Target Frames: {target}')
    print(f'Selected Frames: {len(selected_frames)}')
    
    # Count frames with/without plates
    with_plates = len([f for f in selected_frames if f.get('plate_bbox') is not None])
    without_plates = len(selected_frames) - with_plates
    print(f'  With Plates: {with_plates}')
    print(f'  Without Plates: {without_plates}')
    
    # Add to annotation set
    for frame_data in selected_frames:
        annotation_frames.append({
            'video_id': video_id,
            'video_filename': video_name,
            'frame_index': frame_data['frame_index'],
            'timestamp_ms': frame_data['timestamp_ms'],
            'detection': frame_data
        })
    
    total_selected += len(selected_frames)

print(f'\n{"="*80}')
print('ANNOTATION SET SUMMARY')
print(f'{"="*80}')
print(f'Total Frames Selected: {total_selected}')
print(f'  Video 1 (Rear-plate): {len([f for f in annotation_frames if f["video_id"] == "video_1"])} frames')
print(f'  Video 2 (Front-plate): {len([f for f in annotation_frames if f["video_id"] == "video_2"])} frames')
print(f'  Video 3 (Empty scene): {len([f for f in annotation_frames if f["video_id"] == "video_3"])} frames')

# Count total detections
total_vehicles = 0
total_plates = 0
for frame in annotation_frames:
    if frame['detection'].get('vehicle_bbox') is not None:
        total_vehicles += 1
    if frame['detection'].get('plate_bbox') is not None:
        total_plates += 1

print(f'\nDetections to Annotate:')
print(f'  Vehicle Detections: {total_vehicles}')
print(f'  Plate Detections: {total_plates}')

# Save annotation frame list
output = {
    'annotation_set_id': 'cctv_real_set_1',
    'created_at': '2026-10-28',
    'description': 'Annotation set for real CCTV validation',
    'total_frames': total_selected,
    'frames': annotation_frames
}

Path('data/annotations').mkdir(parents=True, exist_ok=True)
with open('data/annotations/annotation_frame_list.json', 'w') as f:
    json.dump(output, f, indent=2)

print(f'\nAnnotation frame list saved to: data/annotations/annotation_frame_list.json')
print(f'\nNext: Extract these frames to data/annotations/frames/ for manual review')
