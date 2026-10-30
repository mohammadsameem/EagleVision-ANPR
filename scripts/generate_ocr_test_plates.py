"""
Generate synthetic license plate images for OCR testing.

Creates high-resolution Indian-style registration plates with known ground truth.
These are FICTIONAL plates for testing purposes only.
"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from pathlib import Path
import json
import random


class SyntheticPlateGenerator:
    """Generate realistic synthetic Indian license plates"""
    
    # Fictional Indian-style registration numbers
    FICTIONAL_PLATES = [
        "MH 12 AB 1234",
        "DL 01 CA 5678",
        "KA 03 MH 9012",
        "TN 09 XY 3456",
        "GJ 05 PQ 7890",
        "UP 16 RS 2345",
        "RJ 14 TU 6789",
        "WB 02 VW 1234",
        "HR 26 AB 5678",
        "PB 10 CD 9012",
        "AP 28 EF 3456",
        "TS 07 GH 7890",
        "MP 09 IJ 2345",
        "BR 01 KL 6789",
        "OD 05 MN 1234",
        "MH 01 AB 9999",
        "DL 08 XY 1111",
        "KA 51 BC 2222",
        "TN 11 DE 3333",
        "GJ 18 FG 4444",
        "UP 32 HI 5555",
        "RJ 07 JK 6666",
        "WB 21 LM 7777",
        "HR 55 NO 8888",
        "PB 65 PQ 9999",
    ]
    
    def __init__(self, output_dir: str = "data/ocr_test"):
        """
        Initialize generator.
        
        Args:
            output_dir: Directory to save generated images
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Plate dimensions (Indian standard proportions)
        self.plate_width = 440  # High resolution for reliable OCR
        self.plate_height = 110
        
        # Colors (Indian plates: white background, black text)
        self.bg_color = (255, 255, 255)  # White
        self.text_color = (0, 0, 0)  # Black
        self.border_color = (0, 0, 0)  # Black border
        
        # Try to load a suitable font
        self.font = self._load_font()
    
    def _load_font(self):
        """Load a suitable font for plate text"""
        font_size = 60
        
        # Try common system fonts
        font_paths = [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "C:/Windows/Fonts/verdana.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        
        for font_path in font_paths:
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                continue
        
        # Fallback to default font
        print("⚠️  Using default font (may not look realistic)")
        return ImageFont.load_default()
    
    def generate_base_plate(self, registration_number: str) -> Image.Image:
        """
        Generate a clean, high-contrast plate image.
        
        Args:
            registration_number: Text to render (e.g., "MH 12 AB 1234")
        
        Returns:
            PIL Image of the plate
        """
        # Create white background
        img = Image.new('RGB', (self.plate_width, self.plate_height), self.bg_color)
        draw = ImageDraw.Draw(img)
        
        # Draw border
        border_width = 3
        draw.rectangle(
            [(border_width, border_width), 
             (self.plate_width - border_width, self.plate_height - border_width)],
            outline=self.border_color,
            width=border_width
        )
        
        # Calculate text position (centered)
        bbox = draw.textbbox((0, 0), registration_number, font=self.font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        text_x = (self.plate_width - text_width) // 2
        text_y = (self.plate_height - text_height) // 2 - 5  # Slight upward adjustment
        
        # Draw text
        draw.text((text_x, text_y), registration_number, fill=self.text_color, font=self.font)
        
        return img
    
    def apply_blur(self, img: Image.Image, blur_radius: float = 1.5) -> Image.Image:
        """Apply Gaussian blur to simulate motion or focus issues"""
        return img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    
    def apply_noise(self, img: Image.Image, noise_level: int = 15) -> Image.Image:
        """Add random noise to the image"""
        img_array = np.array(img)
        noise = np.random.randint(-noise_level, noise_level, img_array.shape, dtype=np.int16)
        noisy = np.clip(img_array.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        return Image.fromarray(noisy)
    
    def apply_contrast_reduction(self, img: Image.Image, factor: float = 0.7) -> Image.Image:
        """Reduce contrast to simulate poor lighting"""
        img_array = np.array(img)
        mean = img_array.mean()
        adjusted = mean + (img_array - mean) * factor
        adjusted = np.clip(adjusted, 0, 255).astype(np.uint8)
        return Image.fromarray(adjusted)
    
    def apply_rotation(self, img: Image.Image, angle: float = 5.0) -> Image.Image:
        """Apply small rotation to simulate camera angle"""
        return img.rotate(angle, fillcolor=self.bg_color, expand=False)
    
    def generate_variants(
        self, 
        base_img: Image.Image, 
        registration_number: str, 
        plate_id: str
    ) -> list:
        """
        Generate variants of a plate with different degradations.
        
        Args:
            base_img: Clean base plate image
            registration_number: Ground truth text
            plate_id: Unique identifier for this plate
        
        Returns:
            List of (filename, image, variant_type) tuples
        """
        variants = []
        
        # 1. Clean/pristine version
        clean_filename = f"{plate_id}_clean.png"
        variants.append((clean_filename, base_img.copy(), "clean"))
        
        # 2. Slight blur
        blur_img = self.apply_blur(base_img.copy(), blur_radius=1.0)
        blur_filename = f"{plate_id}_blur_light.png"
        variants.append((blur_filename, blur_img, "blur_light"))
        
        # 3. Moderate blur
        blur_heavy_img = self.apply_blur(base_img.copy(), blur_radius=2.0)
        blur_heavy_filename = f"{plate_id}_blur_heavy.png"
        variants.append((blur_heavy_filename, blur_heavy_img, "blur_heavy"))
        
        # 4. Noise
        noise_img = self.apply_noise(base_img.copy(), noise_level=20)
        noise_filename = f"{plate_id}_noise.png"
        variants.append((noise_filename, noise_img, "noise"))
        
        # 5. Reduced contrast
        contrast_img = self.apply_contrast_reduction(base_img.copy(), factor=0.6)
        contrast_filename = f"{plate_id}_contrast_low.png"
        variants.append((contrast_filename, contrast_img, "contrast_low"))
        
        # 6. Small rotation (clockwise)
        rotate_cw_img = self.apply_rotation(base_img.copy(), angle=-3)
        rotate_cw_filename = f"{plate_id}_rotate_cw.png"
        variants.append((rotate_cw_filename, rotate_cw_img, "rotate_cw"))
        
        # 7. Small rotation (counter-clockwise)
        rotate_ccw_img = self.apply_rotation(base_img.copy(), angle=3)
        rotate_ccw_filename = f"{plate_id}_rotate_ccw.png"
        variants.append((rotate_ccw_filename, rotate_ccw_img, "rotate_ccw"))
        
        # 8. Combined: blur + noise
        combined_img = self.apply_blur(base_img.copy(), blur_radius=1.2)
        combined_img = self.apply_noise(combined_img, noise_level=15)
        combined_filename = f"{plate_id}_combined.png"
        variants.append((combined_filename, combined_img, "combined"))
        
        return variants
    
    def generate_dataset(self, num_plates: int = 25) -> dict:
        """
        Generate complete test dataset with ground truth.
        
        Args:
            num_plates: Number of different plates to generate
        
        Returns:
            Ground truth dictionary mapping filenames to registration numbers
        """
        print(f"Generating synthetic OCR test dataset...")
        print(f"Output directory: {self.output_dir}")
        print(f"⚠️  These are FICTIONAL plates for testing only\n")
        
        ground_truth = {}
        
        # Use first N plates from our fictional list
        plates_to_generate = self.FICTIONAL_PLATES[:num_plates]
        
        for idx, registration_number in enumerate(plates_to_generate, 1):
            plate_id = f"plate_{idx:03d}"
            
            print(f"[{idx}/{num_plates}] Generating: {registration_number}")
            
            # Generate base plate
            base_img = self.generate_base_plate(registration_number)
            
            # Generate variants
            variants = self.generate_variants(base_img, registration_number, plate_id)
            
            # Save all variants
            for filename, img, variant_type in variants:
                filepath = self.output_dir / filename
                img.save(filepath)
                
                # Add to ground truth
                ground_truth[filename] = {
                    "registration_number": registration_number,
                    "variant_type": variant_type,
                    "plate_id": plate_id,
                    "width": self.plate_width,
                    "height": self.plate_height
                }
        
        # Save ground truth JSON
        ground_truth_path = self.output_dir / "ground_truth.json"
        with open(ground_truth_path, 'w') as f:
            json.dump(ground_truth, f, indent=2)
        
        print(f"\n✅ Generated {len(ground_truth)} test images")
        print(f"✅ Ground truth saved to: {ground_truth_path}")
        
        # Print summary
        variant_counts = {}
        for data in ground_truth.values():
            variant_type = data["variant_type"]
            variant_counts[variant_type] = variant_counts.get(variant_type, 0) + 1
        
        print("\nVariant breakdown:")
        for variant, count in sorted(variant_counts.items()):
            print(f"  {variant:15s}: {count} images")
        
        return ground_truth


def main():
    """Generate synthetic plate dataset"""
    generator = SyntheticPlateGenerator()
    
    # Generate 25 plates × 8 variants = 200 test images
    ground_truth = generator.generate_dataset(num_plates=25)
    
    print(f"\n{'='*60}")
    print("Dataset generation complete!")
    print(f"{'='*60}")
    print(f"Total images: {len(ground_truth)}")
    print(f"Unique plates: {len(set(d['registration_number'] for d in ground_truth.values()))}")
    print(f"\nThese are SYNTHETIC TEST IMAGES with fictional registration numbers.")
    print(f"Do not use these for any real-world vehicle identification.")


if __name__ == "__main__":
    main()
