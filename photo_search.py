"""
CLIP-based Photo Library Search Tool
Searches for images matching text descriptions using zero-shot classification.
"""

import os
# Fix OpenMP conflict between numpy/opencv/torch
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'
import sys
import pickle
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Tuple, Dict
from dataclasses import dataclass
import argparse
import hashlib

import numpy as np
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
from tqdm import tqdm

# Import Lightroom preview loader
from src.lightroom_preview_loader import load_lightroom_preview

# Configuration
PHOTO_SOURCE = Path(r"Z:\Zefram Photography")
WORKING_DIR = Path(r"C:\projects\photoMotifs\working")
RESULTS_DIR = Path(r"C:\projects\photoMotifs\results")
CACHE_FILE = Path(r"C:\projects\photoMotifs\cache\embeddings_cache.pkl")

# Image loading statistics
_load_stats = {"lr_preview": 0, "original": 0, "failed": 0}

SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.raf', '.dng', '.tiff', '.tif'}
RAW_EXTENSIONS = {'.raf', '.dng'}
THUMBNAIL_SIZE = 300
DEFAULT_TOP_N = 25


@dataclass
class ImageResult:
    """Represents a search result."""
    path: Path
    score: float
    source_type: str  # 'jpg', 'raw_embedded', 'raw_converted', 'smart_preview'


def get_load_stats() -> Dict[str, int]:
    """Get image loading statistics."""
    return _load_stats.copy()


def reset_load_stats():
    """Reset image loading statistics."""
    global _load_stats
    _load_stats = {"lr_preview": 0, "original": 0, "failed": 0}


class EmbeddingCache:
    """Persistent cache for CLIP embeddings."""

    def __init__(self, cache_path: Path):
        self.cache_path = cache_path
        self.cache: Dict[str, Tuple[np.ndarray, float]] = {}  # hash -> (embedding, mtime)
        self.load()

    def load(self):
        """Load cache from disk."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, 'rb') as f:
                    self.cache = pickle.load(f)
                print(f"Loaded {len(self.cache)} cached embeddings")
            except Exception as e:
                print(f"Warning: Could not load cache: {e}")
                self.cache = {}

    def save(self):
        """Save cache to disk."""
        try:
            with open(self.cache_path, 'wb') as f:
                pickle.dump(self.cache, f)
            print(f"Saved {len(self.cache)} embeddings to cache")
        except Exception as e:
            print(f"Warning: Could not save cache: {e}")

    def get_key(self, path: Path) -> str:
        """Generate cache key from file path and modification time."""
        mtime = path.stat().st_mtime
        return f"{path}:{mtime}"

    def get(self, path: Path) -> Optional[np.ndarray]:
        """Get cached embedding if available and not stale."""
        key = self.get_key(path)
        if key in self.cache:
            return self.cache[key]
        return None

    def set(self, path: Path, embedding: np.ndarray):
        """Store embedding in cache."""
        key = self.get_key(path)
        self.cache[key] = embedding


def extract_embedded_jpeg_from_raf(raf_path: Path) -> Optional[Image.Image]:
    """Extract embedded JPEG preview from Fujifilm RAF file."""
    try:
        with open(raf_path, 'rb') as f:
            data = f.read()

        # RAF files contain embedded JPEG - search for JPEG markers
        # JPEG starts with FFD8 and ends with FFD9
        jpeg_start = data.find(b'\xff\xd8\xff')
        if jpeg_start == -1:
            return None

        # Find the end of JPEG
        jpeg_end = data.find(b'\xff\xd9', jpeg_start)
        if jpeg_end == -1:
            return None

        jpeg_data = data[jpeg_start:jpeg_end + 2]

        # Verify it's a reasonable size (at least 50KB for a useful preview)
        if len(jpeg_data) < 50 * 1024:
            return None

        from io import BytesIO
        return Image.open(BytesIO(jpeg_data))

    except Exception as e:
        return None


def extract_embedded_jpeg_from_dng(dng_path: Path) -> Optional[Image.Image]:
    """Extract embedded JPEG preview from DNG file.
    Uses binary search for JPEG markers instead of rawpy to avoid crashes.
    """
    try:
        # Read DNG file and look for embedded JPEG (similar to RAF approach)
        with open(dng_path, 'rb') as f:
            data = f.read()

        # DNG files may contain embedded JPEG previews
        # Search for JPEG markers
        jpeg_start = data.find(b'\xff\xd8\xff')
        if jpeg_start == -1:
            return None

        # Find the end of JPEG (search from a reasonable offset)
        jpeg_end = data.find(b'\xff\xd9', jpeg_start + 1000)
        if jpeg_end == -1:
            return None

        jpeg_data = data[jpeg_start:jpeg_end + 2]

        # Verify it's a reasonable size
        if len(jpeg_data) < 50 * 1024:
            return None

        from io import BytesIO
        img = Image.open(BytesIO(jpeg_data))
        img.load()  # Force load to verify it's valid
        return img

    except Exception:
        return None


def convert_raw_to_image(raw_path: Path) -> Optional[Image.Image]:
    """Convert RAW file to image. Currently disabled due to rawpy crashes."""
    # Disabled - rawpy causes segfaults on some files
    # Just return None and let the caller handle missing images
    return None


def load_image(path: Path, skip_raw_conversion: bool = True) -> Tuple[Optional[Image.Image], str]:
    """
    Load image with preference: Lightroom Preview > JPG > embedded RAW preview.
    Returns (image, source_type).

    Lightroom previews are preferred because they include all edits (crops, color
    corrections, exposure adjustments, negative inversions, etc.).

    Args:
        skip_raw_conversion: If True, skip full RAW conversion (faster, avoids crashes)
    """
    global _load_stats
    try:
        ext = path.suffix.lower()

        # Try Lightroom preview first (has all edits baked in)
        lr_preview = load_lightroom_preview(path, min_size=200)
        if lr_preview:
            _load_stats["lr_preview"] += 1
            return lr_preview.convert('RGB'), 'lr_preview'

        # Fall back to loading original file
        _load_stats["original"] += 1

        # For regular images, just load directly
        if ext in {'.jpg', '.jpeg', '.tiff', '.tif'}:
            try:
                img = Image.open(path)
                img.load()  # Force load to catch errors early
                return img.convert('RGB'), 'original'
            except Exception:
                _load_stats["failed"] += 1
                return None, 'error'

        # For RAW files, check if companion JPG exists
        if ext in RAW_EXTENSIONS:
            for jpg_ext in ['.jpg', '.JPG', '.jpeg', '.JPEG']:
                jpg_path = path.with_suffix(jpg_ext)
                if jpg_path.exists():
                    try:
                        img = Image.open(jpg_path)
                        img.load()
                        return img.convert('RGB'), 'original'
                    except:
                        pass

            # Try to extract embedded preview (fast, safe)
            if ext == '.raf':
                try:
                    img = extract_embedded_jpeg_from_raf(path)
                    if img:
                        return img.convert('RGB'), 'raw_embedded'
                except:
                    pass
            elif ext == '.dng':
                try:
                    img = extract_embedded_jpeg_from_dng(path)
                    if img:
                        return img.convert('RGB'), 'raw_embedded'
                except:
                    pass

            # Fall back to full RAW conversion (slow, may crash)
            if not skip_raw_conversion:
                try:
                    img = convert_raw_to_image(path)
                    if img:
                        return img, 'raw_converted'
                except:
                    pass

        _load_stats["failed"] += 1
        return None, 'error'
    except Exception:
        _load_stats["failed"] += 1
        return None, 'error'


def find_images(source_dir: Path) -> List[Path]:
    """Recursively find all supported image files."""
    images = []
    seen_basenames = set()  # Track to avoid duplicate RAW+JPG pairs

    print(f"Scanning {source_dir} for images...")

    for ext in SUPPORTED_EXTENSIONS:
        for path in source_dir.rglob(f"*{ext}"):
            images.append(path)
        for path in source_dir.rglob(f"*{ext.upper()}"):
            images.append(path)

    # Deduplicate: prefer JPG over RAW when both exist
    deduped = []
    processed = set()

    # Sort so JPGs come before RAWs
    images.sort(key=lambda p: (p.parent, p.stem, 0 if p.suffix.lower() in {'.jpg', '.jpeg'} else 1))

    for path in images:
        key = (path.parent, path.stem.lower())
        if key not in processed:
            processed.add(key)
            deduped.append(path)

    print(f"Found {len(deduped)} unique images")
    return deduped


class PhotoSearcher:
    """CLIP-based photo search engine."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32",
                 cache_path: Optional[Path] = None):
        print(f"Loading CLIP model: {model_name}")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name, use_fast=True)
        self.model.eval()

        self.cache = EmbeddingCache(cache_path or CACHE_FILE)
        self.image_paths: List[Path] = []
        self.embeddings: Optional[np.ndarray] = None

    def compute_image_embedding(self, image: Image.Image) -> np.ndarray:
        """Compute CLIP embedding for a single image."""
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            embedding = self.model.get_image_features(**inputs)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.cpu().numpy().flatten()

    def compute_text_embedding(self, text: str) -> np.ndarray:
        """Compute CLIP embedding for text query."""
        inputs = self.processor(text=[text], return_tensors="pt", padding=True).to(self.device)

        with torch.no_grad():
            embedding = self.model.get_text_features(**inputs)
            embedding = embedding / embedding.norm(dim=-1, keepdim=True)

        return embedding.cpu().numpy().flatten()

    def index_images(self, source_dir: Path, force_reindex: bool = False):
        """Build or update the image embedding index."""
        import gc

        # Reset loading stats
        reset_load_stats()

        self.image_paths = find_images(source_dir)
        embeddings = []
        errors = []
        new_embeddings = 0
        save_interval = 100  # Save cache every N new embeddings

        print(f"\nIndexing {len(self.image_paths)} images...")

        for i, path in enumerate(tqdm(self.image_paths, desc="Computing embeddings")):
            # Check cache first
            cached = self.cache.get(path)
            if cached is not None and not force_reindex:
                embeddings.append(cached)
                continue

            # Load and embed image
            try:
                # Debug: print current file being processed
                sys.stdout.write(f"\rProcessing: {path.name[:40]}...")
                sys.stdout.flush()

                image, source_type = load_image(path)
                if image is None:
                    errors.append(path)
                    embeddings.append(np.zeros(512))  # Placeholder for failed loads
                    continue

                # Resize for faster processing
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                embedding = self.compute_image_embedding(image)
                embeddings.append(embedding)
                self.cache.set(path, embedding)
                new_embeddings += 1

                # Clean up memory
                del image

                # Periodic cache save and memory cleanup
                if new_embeddings % save_interval == 0:
                    self.cache.save()
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

            except Exception as e:
                errors.append(path)
                embeddings.append(np.zeros(512))
                # Clean up on error
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

        self.embeddings = np.vstack(embeddings)
        self.cache.save()

        if errors:
            print(f"\nWarning: {len(errors)} images could not be processed")
            log_path = RESULTS_DIR / "indexing_errors.log"
            with open(log_path, 'w') as f:
                for e in errors:
                    f.write(f"{e}\n")
            print(f"Error log saved to: {log_path}")

        # Report loading stats
        load_stats = get_load_stats()
        print(f"\nImage loading stats:")
        print(f"  Loaded from Lightroom preview: {load_stats['lr_preview']}")
        print(f"  Loaded from original file: {load_stats['original']}")
        print(f"  Failed to load: {load_stats['failed']}")

    def index_images_with_progress(self, source_dir: Path, force_reindex: bool = False):
        """
        Build or update image embedding index with progress updates.
        Yields progress tuples: (current, total, message)
        For use with UI progress bars.
        """
        import gc

        # Reset loading stats
        reset_load_stats()

        self.image_paths = find_images(source_dir)
        total = len(self.image_paths)
        embeddings = []
        errors = []
        new_embeddings = 0
        save_interval = 100

        yield (0, total, f"Found {total} images to index...")

        for i, path in enumerate(self.image_paths):
            # Check cache first
            cached = self.cache.get(path)
            if cached is not None and not force_reindex:
                embeddings.append(cached)
                if i % 100 == 0:
                    yield (i + 1, total, f"Using cached: {path.name}")
                continue

            # Load and embed image
            try:
                image, source_type = load_image(path)
                if image is None:
                    errors.append(path)
                    embeddings.append(np.zeros(512))
                    continue

                image.thumbnail((512, 512), Image.Resampling.LANCZOS)
                embedding = self.compute_image_embedding(image)
                embeddings.append(embedding)
                self.cache.set(path, embedding)
                new_embeddings += 1

                del image

                # Periodic cache save and memory cleanup
                if new_embeddings % save_interval == 0:
                    self.cache.save()
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                    yield (i + 1, total, f"Saved checkpoint ({new_embeddings} new embeddings)")

            except Exception as e:
                errors.append(path)
                embeddings.append(np.zeros(512))
                gc.collect()
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

            # Yield progress every 10 images
            if i % 10 == 0:
                yield (i + 1, total, f"Processing: {path.name[:40]}")

        self.embeddings = np.vstack(embeddings)
        self.cache.save()

        # Final stats
        load_stats = get_load_stats()
        final_msg = (f"Complete! {new_embeddings} new embeddings. "
                     f"LR preview: {load_stats['lr_preview']}, "
                     f"Original: {load_stats['original']}, "
                     f"Failed: {load_stats['failed']}")

        if errors:
            log_path = RESULTS_DIR / "indexing_errors.log"
            with open(log_path, 'w') as f:
                for e in errors:
                    f.write(f"{e}\n")
            final_msg += f" Errors logged to: {log_path}"

        yield (total, total, final_msg)

    def search(self, query: str, top_n: int = DEFAULT_TOP_N) -> List[ImageResult]:
        """Search for images matching the text query."""
        if self.embeddings is None:
            raise ValueError("No images indexed. Call index_images() first.")

        print(f"\nSearching for: '{query}'")

        # Compute query embedding
        query_embedding = self.compute_text_embedding(query)

        # Compute cosine similarity
        similarities = self.embeddings @ query_embedding

        # Get top N results
        top_indices = np.argsort(similarities)[::-1][:top_n]

        results = []
        for idx in top_indices:
            if similarities[idx] > 0:  # Skip failed loads
                path = self.image_paths[idx]
                _, source_type = load_image(path)
                results.append(ImageResult(
                    path=path,
                    score=float(similarities[idx]),
                    source_type=source_type
                ))

        return results


def create_thumbnail(image_path: Path, output_dir: Path, size: int = THUMBNAIL_SIZE) -> Optional[Path]:
    """Create a thumbnail for the HTML report."""
    try:
        img, _ = load_image(image_path)
        if img is None:
            return None

        # Resize maintaining aspect ratio
        img.thumbnail((size, size), Image.Resampling.LANCZOS)

        # Save thumbnail
        thumb_name = f"{hashlib.md5(str(image_path).encode()).hexdigest()}.jpg"
        thumb_path = output_dir / thumb_name
        img.save(thumb_path, "JPEG", quality=85)

        return thumb_path
    except Exception as e:
        return None


def generate_html_report(results: List[ImageResult], query: str, output_dir: Path) -> Path:
    """Generate an HTML report with thumbnails."""
    thumb_dir = output_dir / "thumbnails"
    thumb_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_query = "".join(c if c.isalnum() else "_" for c in query)[:30]
    report_name = f"search_{safe_query}_{timestamp}.html"
    report_path = output_dir / report_name

    print(f"\nGenerating HTML report with {len(results)} results...")

    html_parts = [f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Photo Search: {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #1a1a1a; color: #fff; }}
        h1 {{ color: #fff; }}
        .meta {{ color: #888; margin-bottom: 20px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }}
        .card {{ background: #2a2a2a; border-radius: 8px; overflow: hidden; }}
        .card img {{ width: 100%; height: 250px; object-fit: cover; cursor: pointer; }}
        .card-info {{ padding: 10px; }}
        .score {{ color: #4CAF50; font-weight: bold; font-size: 1.2em; }}
        .path {{ font-size: 0.8em; color: #888; word-break: break-all; margin-top: 5px; }}
        .source-type {{ font-size: 0.7em; color: #666; }}
        a {{ color: #4da6ff; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <h1>Photo Search Results</h1>
    <div class="meta">
        <p><strong>Query:</strong> {query}</p>
        <p><strong>Results:</strong> {len(results)} images</p>
        <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
    </div>
    <div class="grid">
"""]

    for i, result in enumerate(tqdm(results, desc="Creating thumbnails")):
        thumb_path = create_thumbnail(result.path, thumb_dir)
        if thumb_path is None:
            continue

        rel_thumb = thumb_path.relative_to(output_dir)
        file_url = result.path.as_uri()

        html_parts.append(f"""
        <div class="card">
            <a href="{file_url}" target="_blank">
                <img src="{rel_thumb}" alt="Result {i+1}" loading="lazy">
            </a>
            <div class="card-info">
                <span class="score">{result.score:.3f}</span>
                <span class="source-type">({result.source_type})</span>
                <div class="path">
                    <a href="{file_url}" target="_blank">{result.path}</a>
                </div>
            </div>
        </div>
""")

    html_parts.append("""
    </div>
</body>
</html>
""")

    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("".join(html_parts))

    print(f"Report saved to: {report_path}")
    return report_path


def copy_to_working(results: List[ImageResult], working_dir: Path, top_n: Optional[int] = None):
    """Copy top results to working directory for review."""
    working_dir.mkdir(exist_ok=True)

    to_copy = results[:top_n] if top_n else results

    print(f"\nCopying {len(to_copy)} images to {working_dir}...")

    for result in tqdm(to_copy, desc="Copying files"):
        dest = working_dir / result.path.name

        # Handle name conflicts
        if dest.exists():
            stem = result.path.stem
            suffix = result.path.suffix
            counter = 1
            while dest.exists():
                dest = working_dir / f"{stem}_{counter}{suffix}"
                counter += 1

        shutil.copy2(result.path, dest)

    print(f"Files copied to: {working_dir}")


def main():
    parser = argparse.ArgumentParser(description="CLIP-based photo library search")
    parser.add_argument("query", nargs="?", help="Search query text")
    parser.add_argument("-n", "--top-n", type=int, default=DEFAULT_TOP_N,
                        help=f"Number of results (default: {DEFAULT_TOP_N})")
    parser.add_argument("--index-only", action="store_true",
                        help="Only build/update the index, don't search")
    parser.add_argument("--force-reindex", action="store_true",
                        help="Force recompute all embeddings")
    parser.add_argument("--copy", action="store_true",
                        help="Copy top results to working directory")
    parser.add_argument("--source", type=Path, default=PHOTO_SOURCE,
                        help=f"Photo source directory (default: {PHOTO_SOURCE})")

    args = parser.parse_args()

    # Ensure directories exist
    WORKING_DIR.mkdir(exist_ok=True)
    RESULTS_DIR.mkdir(exist_ok=True)

    # Initialize searcher
    searcher = PhotoSearcher()

    # Index images
    searcher.index_images(args.source, force_reindex=args.force_reindex)

    if args.index_only:
        print("Indexing complete.")
        return

    if not args.query:
        print("No query provided. Use --index-only to just build the index.")
        return

    # Search
    results = searcher.search(args.query, args.top_n)

    # Print results to console
    print(f"\nTop {len(results)} results for '{args.query}':")
    print("-" * 80)
    for i, r in enumerate(results[:10], 1):
        print(f"{i:2}. [{r.score:.3f}] {r.path}")
    if len(results) > 10:
        print(f"    ... and {len(results) - 10} more")

    # Generate HTML report
    report_path = generate_html_report(results, args.query, RESULTS_DIR)

    # Optionally copy to working directory
    if args.copy:
        copy_to_working(results, WORKING_DIR, args.top_n)

    print(f"\nDone! Open the report: {report_path}")


if __name__ == "__main__":
    main()
