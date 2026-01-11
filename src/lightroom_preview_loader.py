"""
Lightroom Preview Loader

Extracts rendered previews from Lightroom's preview cache.
These previews have all Lightroom edits baked in, including Negative Lab conversions.
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Tuple
from PIL import Image

# Lightroom paths
LR_CATALOG_PATH = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat")
LR_PREVIEWS_DIR = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Previews.lrdata")
LR_PREVIEWS_DB = LR_PREVIEWS_DIR / "previews.db"

# Path mapping from catalog paths to actual file paths
LR_PATH_MAPPING = {
    "M:/Zefram Photography/": "Z:/Zefram Photography/",
    "M:\\Zefram Photography\\": "Z:\\Zefram Photography\\",
}

# Cache for image ID lookups (path -> catalog image ID)
_image_id_cache: Optional[Dict[str, int]] = None

# Cache for preview UUID lookups (image ID -> (preview UUID, digest))
_preview_cache: Optional[Dict[int, Tuple[str, str]]] = None


def _normalize_path(path: Path) -> str:
    """Normalize path for comparison."""
    return str(path).replace("\\", "/").lower()


def _build_image_id_cache() -> Dict[str, int]:
    """Build cache mapping file paths to Lightroom image IDs."""
    cache = {}

    if not LR_CATALOG_PATH.exists():
        return cache

    try:
        conn = sqlite3.connect(f'file:{LR_CATALOG_PATH}?mode=ro', uri=True)
        cursor = conn.cursor()

        # Get all images with their paths
        cursor.execute("""
            SELECT
                i.id_local,
                r.absolutePath || fo.pathFromRoot || f.baseName || '.' || f.extension as fullPath
            FROM Adobe_images i
            JOIN AgLibraryFile f ON i.rootFile = f.id_local
            JOIN AgLibraryFolder fo ON f.folder = fo.id_local
            JOIN AgLibraryRootFolder r ON fo.rootFolder = r.id_local
        """)

        for row in cursor.fetchall():
            img_id, full_path = row
            if full_path:
                # Apply path mapping and normalize
                for old, new in LR_PATH_MAPPING.items():
                    full_path = full_path.replace(old, new)
                normalized = full_path.replace("\\", "/").lower()
                cache[normalized] = int(img_id)

        conn.close()
    except Exception as e:
        print(f"Warning: Could not build image ID cache: {e}")

    return cache


def _build_preview_cache() -> Dict[int, Tuple[str, str]]:
    """Build cache mapping image IDs to preview UUIDs."""
    cache = {}

    if not LR_PREVIEWS_DB.exists():
        return cache

    try:
        conn = sqlite3.connect(f'file:{LR_PREVIEWS_DB}?mode=ro', uri=True)
        cursor = conn.cursor()

        cursor.execute("SELECT imageId, uuid, digest FROM ImageCacheEntry")

        for row in cursor.fetchall():
            img_id, uuid, digest = row
            if img_id and uuid and digest:
                cache[int(img_id)] = (uuid, digest)

        conn.close()
    except Exception as e:
        print(f"Warning: Could not build preview cache: {e}")

    return cache


def get_image_id(path: Path) -> Optional[int]:
    """Get Lightroom catalog image ID for a file path."""
    global _image_id_cache

    if _image_id_cache is None:
        _image_id_cache = _build_image_id_cache()

    normalized = _normalize_path(path)
    return _image_id_cache.get(normalized)


def get_preview_info(image_id: int) -> Optional[Tuple[str, str]]:
    """Get preview UUID and digest for an image ID."""
    global _preview_cache

    if _preview_cache is None:
        _preview_cache = _build_preview_cache()

    return _preview_cache.get(image_id)


def find_preview_file(preview_uuid: str, digest: str, min_size: int = 200) -> Optional[Path]:
    """
    Find the best preview file for a given UUID and digest.

    Args:
        preview_uuid: The preview UUID
        digest: The preview digest
        min_size: Minimum dimension size (default 200 for CLIP)

    Returns:
        Path to the largest available preview file, or None
    """
    # Preview files are stored in folders by UUID prefix
    uuid_prefix = preview_uuid[:4].upper()
    preview_folder = LR_PREVIEWS_DIR / uuid_prefix[0] / uuid_prefix

    if not preview_folder.exists():
        return None

    # Look for pyramid files with size suffixes
    # Format: {UUID}-{digest}_{size}
    base_name = f"{preview_uuid}-{digest}"

    # Find all matching pyramid files
    pyramid_files = []
    for f in preview_folder.iterdir():
        if f.name.startswith(base_name) and '_' in f.name:
            try:
                size = int(f.name.split('_')[-1])
                if size >= min_size:
                    pyramid_files.append((size, f))
            except ValueError:
                continue

    if not pyramid_files:
        # Check for .lrprev file as fallback
        lrprev = preview_folder / f"{base_name}.lrprev"
        if lrprev.exists():
            return lrprev
        return None

    # Return largest preview
    pyramid_files.sort(key=lambda x: x[0], reverse=True)
    return pyramid_files[0][1]


def extract_jpeg_from_lrprev(lrprev_path: Path) -> Optional[Image.Image]:
    """
    Extract JPEG image from .lrprev container.

    The .lrprev format has a header followed by embedded JPEG data.
    """
    try:
        with open(lrprev_path, 'rb') as f:
            data = f.read()

        # Find JPEG start marker
        jpeg_start = data.find(b'\xff\xd8\xff')
        if jpeg_start < 0:
            return None

        # Find JPEG end marker
        jpeg_end = data.rfind(b'\xff\xd9')
        if jpeg_end < 0:
            return None

        # Extract JPEG data
        jpeg_data = data[jpeg_start:jpeg_end + 2]

        # Load as PIL Image
        from io import BytesIO
        return Image.open(BytesIO(jpeg_data))

    except Exception as e:
        print(f"Warning: Could not extract JPEG from {lrprev_path}: {e}")
        return None


def load_lightroom_preview(path: Path, min_size: int = 200) -> Optional[Image.Image]:
    """
    Load the Lightroom preview for an image.

    This preview has all Lightroom edits baked in, including Negative Lab conversions.

    Args:
        path: Path to the original image file
        min_size: Minimum preview dimension (default 200 for CLIP)

    Returns:
        PIL Image with Lightroom edits applied, or None if no preview available
    """
    # Get image ID from catalog
    image_id = get_image_id(path)
    if image_id is None:
        return None

    # Get preview info
    preview_info = get_preview_info(image_id)
    if preview_info is None:
        return None

    preview_uuid, digest = preview_info

    # Find preview file
    preview_file = find_preview_file(preview_uuid, digest, min_size)
    if preview_file is None:
        return None

    try:
        if preview_file.suffix == '.lrprev':
            return extract_jpeg_from_lrprev(preview_file)
        else:
            # Bare JPEG pyramid file
            return Image.open(preview_file)
    except Exception as e:
        print(f"Warning: Could not load preview {preview_file}: {e}")
        return None


def get_preview_stats() -> Dict[str, int]:
    """Get statistics about preview availability."""
    global _image_id_cache, _preview_cache

    if _image_id_cache is None:
        _image_id_cache = _build_image_id_cache()
    if _preview_cache is None:
        _preview_cache = _build_preview_cache()

    # Count Analog images with previews
    analog_with_preview = 0
    analog_without_preview = 0

    for path, img_id in _image_id_cache.items():
        if 'analog' in path.lower():
            if img_id in _preview_cache:
                analog_with_preview += 1
            else:
                analog_without_preview += 1

    return {
        'total_images': len(_image_id_cache),
        'total_previews': len(_preview_cache),
        'analog_with_preview': analog_with_preview,
        'analog_without_preview': analog_without_preview,
    }


if __name__ == "__main__":
    # Test the preview loader
    print("=== Lightroom Preview Loader Test ===\n")

    stats = get_preview_stats()
    print(f"Total images in catalog: {stats['total_images']}")
    print(f"Total previews available: {stats['total_previews']}")
    print(f"Analog images with preview: {stats['analog_with_preview']}")
    print(f"Analog images without preview: {stats['analog_without_preview']}")

    # Test loading a specific preview
    test_path = Path(r"Z:\Zefram Photography\Analog\Nikon F\Roll 14 Kodak Portra 400\NikonF_Roll14_KodakPortra400_15.dng")
    print(f"\nTesting: {test_path.name}")

    preview = load_lightroom_preview(test_path)
    if preview:
        print(f"  Preview loaded: {preview.size} {preview.mode}")
    else:
        print("  No preview available")
