"""
Build mapping between Smart Previews and original images.
Uses capture date matching since database IDs don't correlate directly.
"""
import sqlite3
import re
import json
import pickle
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional, Tuple
from tqdm import tqdm
from PIL import Image
import rawpy
import numpy as np

# Paths
CATALOG_PATH = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat")
SP_DIR = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Smart Previews.lrdata")
MAPPING_CACHE = Path(r"C:\projects\photoMotifs\smart_preview_mapping.pkl")

PATH_MAPPINGS = {
    "M:/Zefram Photography/": "Z:/Zefram Photography/",
    "M:\\Zefram Photography\\": "Z:\\Zefram Photography\\",
}


def map_path(catalog_path: str) -> Path:
    """Map catalog path to actual filesystem path."""
    result = catalog_path
    for old, new in PATH_MAPPINGS.items():
        result = result.replace(old, new)
    return Path(result)


def extract_sp_metadata(sp_path: Path) -> Optional[Tuple[str, datetime]]:
    """Extract CreateDate from smart preview XMP metadata."""
    try:
        with open(sp_path, 'rb') as f:
            data = f.read()

        xmp_start = data.find(b'<x:xmpmeta')
        if xmp_start == -1:
            return None

        xmp_end = data.find(b'</x:xmpmeta>', xmp_start)
        xmp = data[xmp_start:xmp_end + 12].decode('utf-8', errors='ignore')

        # Extract create date
        date_match = re.search(r'xmp:CreateDate="([^"]+)"', xmp)
        if not date_match:
            return None

        create_date = date_match.group(1)

        # Parse date (remove timezone)
        date_str = create_date.split('-07:00')[0].split('-08:00')[0].split('+')[0]
        if 'T' not in date_str:
            return None

        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
        return (sp_path.stem, dt)

    except Exception as e:
        return None


def build_mapping(force_rebuild: bool = False) -> Dict[Path, Path]:
    """
    Build mapping from original image path to smart preview path.

    Returns:
        Dict mapping original image Path -> smart preview Path
    """
    # Check cache
    if MAPPING_CACHE.exists() and not force_rebuild:
        try:
            with open(MAPPING_CACHE, 'rb') as f:
                mapping = pickle.load(f)
            print(f"Loaded {len(mapping)} cached mappings")
            return mapping
        except:
            pass

    print("Building smart preview mapping (this may take a few minutes)...")

    # Get all smart preview files
    sp_files = list(SP_DIR.rglob("*.dng"))
    print(f"Found {len(sp_files)} smart preview files")

    # Build index of capture times -> smart preview
    print("Extracting metadata from smart previews...")
    sp_by_time: Dict[str, Path] = {}  # "YYYY-MM-DDTHH:MM:SS" -> sp_path

    for sp_path in tqdm(sp_files, desc="Reading SP metadata"):
        result = extract_sp_metadata(sp_path)
        if result:
            uuid, dt = result
            time_key = dt.strftime("%Y-%m-%dT%H:%M:%S")
            sp_by_time[time_key] = sp_path

    print(f"Extracted {len(sp_by_time)} valid timestamps")

    # Now query catalog for all images with capture times
    print("Querying catalog for image capture times...")
    conn = sqlite3.connect(f'file:{CATALOG_PATH}?mode=ro', uri=True)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            i.captureTime,
            f.baseName,
            f.extension,
            fo.pathFromRoot,
            r.absolutePath
        FROM Adobe_images i
        JOIN AgLibraryFile f ON i.rootFile = f.id_local
        JOIN AgLibraryFolder fo ON f.folder = fo.id_local
        JOIN AgLibraryRootFolder r ON fo.rootFolder = r.id_local
        WHERE i.captureTime IS NOT NULL
    """)

    # Build mapping
    mapping: Dict[Path, Path] = {}
    matched = 0

    print("Matching images to smart previews...")
    for row in cursor.fetchall():
        cap_time, name, ext, folder, root = row

        # Format capture time to match XMP format
        if cap_time and 'T' in str(cap_time):
            time_key = str(cap_time).split('.')[0]  # Remove milliseconds

            if time_key in sp_by_time:
                catalog_path = f"{root}{folder}{name}.{ext}"
                actual_path = map_path(catalog_path)
                mapping[actual_path] = sp_by_time[time_key]
                matched += 1

    conn.close()

    print(f"Matched {matched} images to smart previews")

    # Save cache
    with open(MAPPING_CACHE, 'wb') as f:
        pickle.dump(mapping, f)
    print(f"Saved mapping cache to {MAPPING_CACHE}")

    return mapping


def load_smart_preview(sp_path: Path) -> Optional[Image.Image]:
    """Load smart preview DNG and convert to PIL Image."""
    try:
        with rawpy.imread(str(sp_path)) as raw:
            rgb = raw.postprocess(
                use_camera_wb=True,
                no_auto_bright=False,
                output_bps=8
            )
            return Image.fromarray(rgb)
    except Exception as e:
        # Try PIL directly (some DNGs work)
        try:
            return Image.open(sp_path).convert('RGB')
        except:
            return None


class SmartPreviewLoader:
    """Load images preferring smart previews when available."""

    def __init__(self):
        self.mapping = build_mapping()
        self._stats = {"sp_used": 0, "original_used": 0, "failed": 0}

    def load_image(self, image_path: Path) -> Optional[Image.Image]:
        """
        Load image, using smart preview if available.

        Returns:
            PIL Image or None if loading fails
        """
        # Check if smart preview exists
        if image_path in self.mapping:
            sp_path = self.mapping[image_path]
            img = load_smart_preview(sp_path)
            if img:
                self._stats["sp_used"] += 1
                return img

        # Fall back to original loading method
        from photo_search import load_image as original_load
        img, source = original_load(image_path)
        if img:
            self._stats["original_used"] += 1
        else:
            self._stats["failed"] += 1
        return img

    def get_stats(self) -> Dict:
        return {
            **self._stats,
            "total_mappings": len(self.mapping)
        }


def test_mapping():
    """Test the mapping and smart preview loading."""
    print("=" * 60)
    print("SMART PREVIEW MAPPING TEST")
    print("=" * 60)

    mapping = build_mapping()

    print(f"\nTotal mappings: {len(mapping)}")

    # Test loading a few
    print("\nTesting smart preview loading...")
    test_paths = list(mapping.keys())[:5]

    for orig_path in test_paths:
        sp_path = mapping[orig_path]
        print(f"\nOriginal: {orig_path.name}")
        print(f"Smart Preview: {sp_path.name}")

        img = load_smart_preview(sp_path)
        if img:
            print(f"Loaded: {img.size}")
        else:
            print("Failed to load")


if __name__ == "__main__":
    test_mapping()
