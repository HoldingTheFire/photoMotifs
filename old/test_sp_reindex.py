"""Test reindexing with Smart Previews."""
import sys
sys.path.insert(0, r"C:\projects\photoMotifs")

from pathlib import Path
from photo_search import (
    PhotoSearcher, get_sp_mapping, reset_sp_stats, get_sp_stats, PHOTO_SOURCE
)

print("=" * 60)
print("SMART PREVIEW REINDEX TEST")
print("=" * 60)

# Load mapping
mapping = get_sp_mapping()
print(f"Smart preview mappings: {len(mapping)}")

# Create a test folder with a subset
test_folder = Path(r"Z:\Zefram Photography\Analog")
print(f"\nTest folder: {test_folder}")

# Initialize searcher
searcher = PhotoSearcher()

# Force reindex the test folder
print("\nForce reindexing (will use Smart Previews)...")
reset_sp_stats()
searcher.index_images(test_folder, force_reindex=True)

# Show stats
stats = get_sp_stats()
print(f"\nFinal Stats:")
print(f"  Smart Preview used: {stats['sp_used']}")
print(f"  Original used: {stats['original_used']}")
print(f"  Total embeddings: {len(searcher.image_paths)}")

# Test a search
results = searcher.search("black and white portrait", top_n=5)
print(f"\nSearch results for 'black and white portrait':")
for i, r in enumerate(results[:5], 1):
    print(f"  {i}. [{r.score:.3f}] {r.path.name}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
