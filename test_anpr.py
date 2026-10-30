from src.anpr_pipeline import ANPRPipeline
from pathlib import Path

# Check for test video
video_path = 'data/test_videos/WhatsApp Video 2026-10-30 at 6.25.41 AM.mp4'
if not Path(video_path).exists():
    print(f'❌ Test video not found: {video_path}')
    exit(1)

print('✅ Test video found')
print(f'Video: {video_path}')

# Initialize pipeline
config = {
    'vehicle_model': 'yolov8n.pt',
    'use_gpu': False,
    'confidence_threshold': 0.70
}

pipeline = ANPRPipeline(config=config)

# Process 1 second (5 frames at 5 FPS)
print('\n' + '='*60)
print('Testing ANPR Pipeline - Processing 1 second...')
print('='*60)

results = pipeline.process_video(video_path, fps=1)  # Only 1 FPS for quick test

print(f'\nResults: {len(results)} detections')
if results:
    print(f'Sample detection keys: {list(results[0].keys())}')
    print('✅ ANPR Pipeline functional!')
else:
    print('⚠️  No detections (may be normal for test video)')
    
print('Test complete!')
