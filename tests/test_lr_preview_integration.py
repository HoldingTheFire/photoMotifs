"""Test Lightroom preview integration in photo_search."""
import sys
sys.path.insert(0, r'C:\projects\photoMotifs')
from pathlib import Path
from photo_search import load_image, ANALOG_FOLDER_NAME

# Test files
test_files = [
    # Analog - should use lr_preview
    Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 14 Kodak Portra 400\NikonF_Roll14_KodakPortra400_15.dng"),
    Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 20 CineStill 800T\NikonF_Roll20_CineStill800T_22.dng"),
    # Non-Analog - should use smart_preview or jpg
    Path(r"Z:\Zefram Photography\Parks\Don Edwards Wildlife Refuge\Don Edwards June 2023\DSCF4095.JPG"),
]

print("=== Testing Lightroom Preview Integration ===\n")

for path in test_files:
    is_analog = ANALOG_FOLDER_NAME in path.parts
    print(f"File: {path.parent.name}/{path.name}")
    print(f"  Is Analog: {is_analog}")

    if path.exists():
        img, source_type = load_image(path)
        if img:
            print(f"  Loaded: {source_type}, size={img.size}")
        else:
            print(f"  Failed to load")
    else:
        print(f"  File not found")
    print()
