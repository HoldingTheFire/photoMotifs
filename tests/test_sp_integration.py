"""Test Smart Preview integration in photo_search.py."""
import sys
sys.path.insert(0, r"C:\projects\photoMotifs")

from pathlib import Path
from photo_search import (
    get_sp_mapping, load_image, load_smart_preview,
    reset_sp_stats, get_sp_stats
)

print("=" * 60)
print("SMART PREVIEW INTEGRATION TEST")
print("=" * 60)

# Load the mapping
mapping = get_sp_mapping()
print(f"\nTotal mappings: {len(mapping)}")

if len(mapping) == 0:
    print("ERROR: No mappings found. Run smart_preview_mapper.py first.")
    sys.exit(1)

# Test a few image loads
test_paths = list(mapping.keys())[:5]

print("\n--- Testing load_image with Smart Preview ---")
reset_sp_stats()

for orig_path in test_paths:
    sp_path = mapping[orig_path]
    print(f"\nOriginal: {orig_path.name}")
    print(f"  SP: {sp_path.name}")

    # Load via load_image (should use smart preview)
    img, source_type = load_image(orig_path, use_smart_preview=True)
    if img:
        print(f"  Loaded: {img.size}, source={source_type}")
    else:
        print(f"  FAILED to load")

stats = get_sp_stats()
print(f"\n--- Stats ---")
print(f"  Smart Preview used: {stats['sp_used']}")
print(f"  Original used: {stats['original_used']}")

# Test with smart preview disabled
print("\n--- Testing with Smart Preview DISABLED ---")
reset_sp_stats()

test_path = test_paths[0]
img, source_type = load_image(test_path, use_smart_preview=False)
if img:
    print(f"Loaded: {img.size}, source={source_type}")

stats = get_sp_stats()
print(f"SP used: {stats['sp_used']}, Original used: {stats['original_used']}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
