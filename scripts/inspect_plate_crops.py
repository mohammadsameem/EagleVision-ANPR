"""Manually inspect plate crop images to verify content and visibility."""
import cv2
import numpy as np
from pathlib import Path

def inspect_crops(input_dir: str = "data/gemini_anpr_test", num_samples: int = 10):
    """
    Inspect sample plate crops and report image statistics.
    
    Args:
        input_dir: Directory containing plate crops
        num_samples: Number of samples to inspect
    """
    print("="*70)
    print("PLATE CROP INSPECTION")
    print("="*70)
    print()
    
    # Find plate crops
    input_path = Path(input_dir)
    plate_files = sorted(input_path.glob("plate_f*.jpg"))
    
    if not plate_files:
        print(f"[ERROR] No plate crops found in {input_dir}")
        return
    
    print(f"Found {len(plate_files)} plate crops")
    print(f"Inspecting first {num_samples} crops...")
    print()
    
    for i, plate_file in enumerate(plate_files[:num_samples]):
        img = cv2.imread(str(plate_file))
        
        if img is None:
            print(f"{i+1}. {plate_file.name}: ERROR - Cannot read")
            continue
        
        h, w = img.shape[:2]
        mean_val = img.mean()
        std_val = img.std()
        min_val = img.min()
        max_val = img.max()
        
        # Check if image is mostly uniform (no text)
        has_detail = std_val > 10  # Arbitrary threshold
        
        print(f"{i+1}. {plate_file.name}")
        print(f"   Size: {w}x{h} pixels")
        print(f"   Mean: {mean_val:.2f}, Std: {std_val:.2f}")
        print(f"   Range: {min_val} - {max_val}")
        print(f"   Has detail: {'YES' if has_detail else 'NO (too uniform)'}")
        print()
    
    print("="*70)
    print("ANALYSIS")
    print("="*70)
    print()
    
    # Analyze all crops
    sizes = []
    means = []
    stds = []
    
    for plate_file in plate_files:
        img = cv2.imread(str(plate_file))
        if img is not None:
            h, w = img.shape[:2]
            sizes.append((w, h))
            means.append(img.mean())
            stds.append(img.std())
    
    if sizes:
        widths = [s[0] for s in sizes]
        heights = [s[1] for s in sizes]
        
        print(f"Size statistics (across {len(sizes)} crops):")
        print(f"  Width:  min={min(widths)}, max={max(widths)}, avg={np.mean(widths):.1f}")
        print(f"  Height: min={min(heights)}, max={max(heights)}, avg={np.mean(heights):.1f}")
        print()
        
        print(f"Pixel statistics:")
        print(f"  Mean:   min={min(means):.2f}, max={max(means):.2f}, avg={np.mean(means):.2f}")
        print(f"  Std:    min={min(stds):.2f}, max={max(stds):.2f}, avg={np.mean(stds):.2f}")
        print()
        
        low_detail_count = sum(1 for s in stds if s < 10)
        print(f"Crops with low detail (std < 10): {low_detail_count}/{len(stds)} ({low_detail_count/len(stds)*100:.1f}%)")
        print()
    
    print("CONCLUSION:")
    print()
    
    if np.mean(stds) < 10:
        print("[!] Most crops have low pixel variation (std < 10)")
        print("    This indicates plates may be:")
        print("    - Too small/blurred to have readable text")
        print("    - AI-generated without actual characters")
        print("    - Solid color regions mistaken for plates")
    else:
        print("[OK] Crops have reasonable pixel variation")
        print("    OCR failure may be due to:")
        print("    - Text style not recognized by EasyOCR")
        print("    - Need different OCR model or settings")
    
    print()
    print("RECOMMENDATION:")
    print("  1. Manually view a few crop images to verify content")
    print("  2. Test with real CCTV footage containing actual plates")
    print("  3. Try PaddleOCR as alternative OCR engine")
    print()

if __name__ == "__main__":
    inspect_crops()
