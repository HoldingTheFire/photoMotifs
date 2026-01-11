"""
Reindex Analog folder images with negative inversion applied.
Clears cached embeddings for Analog files and recomputes them.
"""
import sys
sys.path.insert(0, r'C:\projects\photoMotifs')

import pickle
from pathlib import Path

CACHE_FILE = Path(r"C:\projects\photoMotifs\cache\embeddings_cache.pkl")
ANALOG_FOLDER = "Analog"

def clear_analog_cache():
    """Remove Analog folder entries from the embedding cache."""
    if not CACHE_FILE.exists():
        print("No cache file found.")
        return 0

    with open(CACHE_FILE, 'rb') as f:
        cache = pickle.load(f)

    original_count = len(cache)

    # Find and remove Analog entries
    # Cache keys are like "Z:\Zefram Photography\Analog\...:1234567.89"
    analog_keys = [k for k in cache.keys() if ANALOG_FOLDER in k]

    for key in analog_keys:
        del cache[key]

    removed_count = len(analog_keys)

    # Save updated cache
    with open(CACHE_FILE, 'wb') as f:
        pickle.dump(cache, f)

    print(f"Removed {removed_count} Analog entries from cache")
    print(f"Cache size: {original_count} -> {len(cache)}")
    return removed_count


if __name__ == "__main__":
    print("=" * 60)
    print("REINDEXING ANALOG FOLDER WITH NEGATIVE INVERSION")
    print("=" * 60)

    # Step 1: Clear Analog entries from cache
    print("\nStep 1: Clearing Analog entries from embedding cache...")
    removed = clear_analog_cache()

    if removed == 0:
        print("No Analog entries found in cache. Nothing to reindex.")
    else:
        # Step 2: Reindex just the Analog folder
        print("\nStep 2: Reindexing Analog folder...")
        print("This will compute embeddings with negative inversion applied.\n")

        from photo_search import PhotoSearcher
        from pathlib import Path

        ANALOG_SOURCE = Path(r"Z:\Zefram Photography\Analog")

        searcher = PhotoSearcher()
        searcher.index_images(ANALOG_SOURCE)

        print("\nDone! Analog images have been reindexed with inversion applied.")
        print("You can now run searches and Analog photos will show correct colors.")
