"""Test the negative inversion function."""
import sys
sys.path.insert(0, r'C:\projects\photoMotifs')

from pathlib import Path
from PIL import Image
import pickle
import numpy as np

# Import the inversion function
from photo_search import invert_color_negative, is_analog_negative, load_smart_preview

mapping_cache = Path(r"C:\projects\photoMotifs\cache\smart_preview_mapping.pkl")

# Load mapping
with open(mapping_cache, 'rb') as f:
    mapping = pickle.load(f)

# Find Analog files in the mapping
analog_mappings = [(orig, sp) for orig, sp in mapping.items()
                   if 'Analog' in str(orig)]

print(f"Found {len(analog_mappings)} Analog files with Smart Previews")

# Test a few different ones
test_count = 3
for i, (orig_path, sp_path) in enumerate(analog_mappings[:test_count]):
    print(f"\n{'='*60}")
    print(f"Test {i+1}: {orig_path.name}")
    print(f"Is Analog: {is_analog_negative(orig_path)}")

    # Load the raw Smart Preview (without inversion)
    try:
        with open(sp_path, 'rb') as f:
            data = f.read()
        jpeg_start = data.find(b'\xff\xd8\xff')
        jpeg_end = data.find(b'\xff\xd9', jpeg_start + 1000)
        jpeg_data = data[jpeg_start:jpeg_end + 2]
        from io import BytesIO
        original_img = Image.open(BytesIO(jpeg_data)).convert('RGB')

        # Apply inversion
        inverted_img = invert_color_negative(original_img)

        # Save both
        original_img.save(f"C:\\projects\\photoMotifs\\tests\\fixtures\\test_original_{i+1}.jpg", quality=90)
        inverted_img.save(f"C:\\projects\\photoMotifs\\tests\\fixtures\\test_inverted_{i+1}.jpg", quality=90)

        # Print color stats
        orig_arr = np.array(original_img)
        inv_arr = np.array(inverted_img)

        print(f"Original R/G/B means: {orig_arr[:,:,0].mean():.1f} / {orig_arr[:,:,1].mean():.1f} / {orig_arr[:,:,2].mean():.1f}")
        print(f"Inverted R/G/B means: {inv_arr[:,:,0].mean():.1f} / {inv_arr[:,:,1].mean():.1f} / {inv_arr[:,:,2].mean():.1f}")

    except Exception as e:
        print(f"Error: {e}")

print(f"\nTest images saved to C:\\projects\\photoMotifs\\tests\\fixtures\\test_*.jpg")
print("Please visually inspect test_inverted_*.jpg to verify colors look correct.")

# Also test loading through load_smart_preview with original_path
print(f"\n{'='*60}")
print("Testing load_smart_preview with inversion:")
orig_path, sp_path = analog_mappings[0]
img = load_smart_preview(sp_path, original_path=orig_path)
if img:
    img.save(f"C:\\projects\\photoMotifs\\tests\\fixtures\\test_via_load_smart_preview.jpg", quality=90)
    print(f"Saved test_via_load_smart_preview.jpg")
