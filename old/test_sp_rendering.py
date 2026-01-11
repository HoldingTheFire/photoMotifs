"""Test different methods of loading Smart Preview DNGs."""
from pathlib import Path
from PIL import Image
import rawpy
import pickle
import numpy as np

sp_dir = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Smart Previews.lrdata")
mapping_cache = Path(r"C:\projects\photoMotifs\cache\smart_preview_mapping.pkl")
analog_dir = Path(r"Z:\Zefram Photography\Analog")

# Load mapping
with open(mapping_cache, 'rb') as f:
    mapping = pickle.load(f)

# Find Analog files in the mapping
analog_mappings = [(orig, sp) for orig, sp in mapping.items()
                   if 'Analog' in str(orig)]

print(f"Found {len(analog_mappings)} Analog files with Smart Previews")

if analog_mappings:
    # Test first one
    orig_path, sp_path = analog_mappings[0]
    print(f"\nOriginal: {orig_path}")
    print(f"Smart Preview: {sp_path}")

    # Method 1: rawpy with default settings (this is what load_smart_preview does)
    print("\nMethod 1: rawpy.postprocess(use_camera_wb=True)")
    try:
        with rawpy.imread(str(sp_path)) as raw:
            rgb = raw.postprocess(use_camera_wb=True, no_auto_bright=False, output_bps=8)
            img1 = Image.fromarray(rgb)
            # Check if it looks like a negative (orange/brown dominant)
            arr = np.array(img1)
            r_mean, g_mean, b_mean = arr[:,:,0].mean(), arr[:,:,1].mean(), arr[:,:,2].mean()
            print(f"  Image size: {img1.size}")
            print(f"  R/G/B means: {r_mean:.1f} / {g_mean:.1f} / {b_mean:.1f}")
            if r_mean > g_mean + 20 and r_mean > b_mean + 20:
                print("  WARNING: Orange tint detected - likely negative/unprocessed!")
            img1.save(r"C:\projects\photoMotifs\tests\fixtures\test_sp_method1.jpg", quality=90)
    except Exception as e:
        print(f"  Error: {e}")

    # Method 2: Try extracting embedded JPEG preview from Smart Preview
    print("\nMethod 2: Extract embedded JPEG preview")
    try:
        with open(sp_path, 'rb') as f:
            data = f.read()

        jpeg_start = data.find(b'\xff\xd8\xff')
        if jpeg_start != -1:
            jpeg_end = data.find(b'\xff\xd9', jpeg_start + 1000)
            if jpeg_end != -1:
                jpeg_data = data[jpeg_start:jpeg_end + 2]
                from io import BytesIO
                img2 = Image.open(BytesIO(jpeg_data))
                img2.load()
                arr = np.array(img2)
                r_mean, g_mean, b_mean = arr[:,:,0].mean(), arr[:,:,1].mean(), arr[:,:,2].mean()
                print(f"  Image size: {img2.size}")
                print(f"  R/G/B means: {r_mean:.1f} / {g_mean:.1f} / {b_mean:.1f}")
                img2.save(r"C:\projects\photoMotifs\tests\fixtures\test_sp_method2.jpg", quality=90)
            else:
                print("  No JPEG end marker found")
        else:
            print("  No embedded JPEG found")
    except Exception as e:
        print(f"  Error: {e}")

    # Method 3: PIL directly
    print("\nMethod 3: PIL.Image.open()")
    try:
        img3 = Image.open(sp_path)
        img3.load()
        arr = np.array(img3.convert('RGB'))
        r_mean, g_mean, b_mean = arr[:,:,0].mean(), arr[:,:,1].mean(), arr[:,:,2].mean()
        print(f"  Image size: {img3.size}")
        print(f"  Mode: {img3.mode}")
        print(f"  R/G/B means: {r_mean:.1f} / {g_mean:.1f} / {b_mean:.1f}")
        img3.convert('RGB').save(r"C:\projects\photoMotifs\tests\fixtures\test_sp_method3.jpg", quality=90)
    except Exception as e:
        print(f"  Error: {e}")

    print(f"\nTest images saved to C:\\projects\\photoMotifs\\tests\\fixtures\\test_sp_*.jpg")
    print("Please visually inspect them to determine which method produces correct colors.")
