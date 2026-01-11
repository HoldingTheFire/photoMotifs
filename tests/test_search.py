"""Quick test script for photo search."""
import warnings
warnings.filterwarnings('ignore')

import os
os.environ['TQDM_DISABLE'] = '1'  # Disable tqdm

from pathlib import Path
from photo_search import PhotoSearcher, generate_html_report, RESULTS_DIR

print("=" * 60)
print("CLIP Photo Search Test")
print("=" * 60)

# Initialize
print("\n1. Loading CLIP model...")
searcher = PhotoSearcher()

# Index a small subset
source = Path(r"Z:\Zefram Photography\Photo Walks\Fremont\Downtown")
print(f"\n2. Indexing images from: {source}")
searcher.index_images(source)

# Search
query = "architecture buildings"
print(f"\n3. Searching for: '{query}'")
results = searcher.search(query, top_n=5)

# Show results
print(f"\n4. Top {len(results)} results:")
print("-" * 60)
for i, r in enumerate(results, 1):
    print(f"  {i}. Score: {r.score:.4f}")
    print(f"     File: {r.path.name}")
    print(f"     Path: {r.path}")
    print()

# Generate HTML report
print("5. Generating HTML report...")
report = generate_html_report(results, query, RESULTS_DIR)
print(f"   Report: {report}")

print("\n" + "=" * 60)
print("TEST COMPLETE")
print("=" * 60)
