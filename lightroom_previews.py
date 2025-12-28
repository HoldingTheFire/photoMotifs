"""
Extract rendered previews from Lightroom Classic catalog.
These previews have all develop settings applied.
"""
import sqlite3
from pathlib import Path
from typing import Optional, Tuple, Dict
from PIL import Image
from io import BytesIO

# Lightroom catalog paths
CATALOG_PATH = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat")
PREVIEWS_DB = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Previews.lrdata\previews.db")
ROOT_PIXELS_DB = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Previews.lrdata\root-pixels.db")
PREVIEWS_DIR = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Previews.lrdata")

# Path mapping
PATH_MAPPINGS = {
    "M:/Zefram Photography/": "Z:/Zefram Photography/",
    "M:\\Zefram Photography\\": "Z:\\Zefram Photography\\",
}


class LightroomPreviews:
    """Extract rendered previews from Lightroom catalog."""

    def __init__(self):
        self.catalog_conn = None
        self.previews_conn = None
        self.root_pixels_conn = None
        self._image_uuid_cache: Dict[Path, str] = {}  # path -> uuid

    def connect(self):
        """Open connections to Lightroom databases."""
        if self.catalog_conn is None:
            self.catalog_conn = sqlite3.connect(f'file:{CATALOG_PATH}?mode=ro', uri=True)
            self.previews_conn = sqlite3.connect(f'file:{PREVIEWS_DB}?mode=ro', uri=True)
            self.root_pixels_conn = sqlite3.connect(f'file:{ROOT_PIXELS_DB}?mode=ro', uri=True)

    def close(self):
        """Close all connections."""
        for conn in [self.catalog_conn, self.previews_conn, self.root_pixels_conn]:
            if conn:
                conn.close()
        self.catalog_conn = None
        self.previews_conn = None
        self.root_pixels_conn = None

    def _map_path(self, catalog_path: str) -> Path:
        """Map catalog path to actual filesystem path."""
        result = catalog_path
        for old, new in PATH_MAPPINGS.items():
            result = result.replace(old, new)
        return Path(result)

    def _reverse_map_path(self, actual_path: Path) -> str:
        """Map actual path back to catalog path format."""
        path_str = str(actual_path).replace("\\", "/")
        for old, new in PATH_MAPPINGS.items():
            old_normalized = old.replace("\\", "/")
            new_normalized = new.replace("\\", "/")
            path_str = path_str.replace(new_normalized, old_normalized)
        return path_str

    def _get_image_uuid(self, image_path: Path) -> Optional[str]:
        """Get the preview UUID for an image by its file path."""
        if image_path in self._image_uuid_cache:
            return self._image_uuid_cache[image_path]

        self.connect()
        cursor = self.catalog_conn.cursor()

        # Get image ID from catalog
        catalog_path = self._reverse_map_path(image_path)
        filename = image_path.name

        # Try to find by filename
        cursor.execute("""
            SELECT i.id_local
            FROM Adobe_images i
            JOIN AgLibraryFile f ON i.rootFile = f.id_local
            WHERE f.baseName || '.' || f.extension = ?
        """, (filename,))

        row = cursor.fetchone()
        if not row:
            return None

        image_id = row[0]

        # Get preview UUID from ImageCacheEntry
        cursor = self.previews_conn.cursor()
        cursor.execute("""
            SELECT uuid FROM ImageCacheEntry WHERE imageId = ?
        """, (image_id,))

        row = cursor.fetchone()
        if row:
            uuid = row[0]
            self._image_uuid_cache[image_path] = uuid
            return uuid

        return None

    def get_preview(self, image_path: Path,
                    min_size: int = 512,
                    prefer_size: int = 2048) -> Optional[Image.Image]:
        """
        Get a rendered preview for an image.

        Args:
            image_path: Path to the original image file
            min_size: Minimum acceptable preview size (long dimension)
            prefer_size: Preferred preview size (will get closest available)

        Returns:
            PIL Image of the preview, or None if not available
        """
        uuid = self._get_image_uuid(image_path)
        if not uuid:
            return None

        self.connect()
        cursor = self.previews_conn.cursor()

        # Find available pyramid levels for this image
        cursor.execute("""
            SELECT pl.digest, pl.longDimension, pl.width, pl.height
            FROM PyramidLevel pl
            WHERE pl.uuid = ?
            ORDER BY pl.longDimension DESC
        """, (uuid,))

        levels = cursor.fetchall()
        if not levels:
            return None

        # Find best matching level
        best_level = None
        for digest, dim, width, height in levels:
            if dim >= min_size:
                if dim <= prefer_size:
                    best_level = (digest, dim)
                    break
                elif best_level is None:
                    best_level = (digest, dim)

        # Fall back to largest available if nothing meets min_size
        if best_level is None and levels:
            best_level = (levels[0][0], levels[0][1])

        if best_level is None:
            return None

        digest, dim = best_level

        # Build preview file path
        prefix = uuid[:4]
        filename = f"{uuid}-{digest}_{int(dim)}"
        preview_path = PREVIEWS_DIR / prefix[0] / prefix / filename

        if not preview_path.exists():
            return None

        try:
            return Image.open(preview_path)
        except Exception:
            return None

    def get_thumbnail(self, image_path: Path) -> Optional[Image.Image]:
        """Get small thumbnail from root-pixels.db."""
        uuid = self._get_image_uuid(image_path)
        if not uuid:
            return None

        self.connect()
        cursor = self.root_pixels_conn.cursor()

        # Get pyramid digest to match in RootPixels
        pv_cursor = self.previews_conn.cursor()
        pv_cursor.execute("SELECT digest FROM Pyramid WHERE uuid = ?", (uuid,))
        row = pv_cursor.fetchone()
        if not row:
            return None

        digest = row[0]

        cursor.execute("""
            SELECT jpegData FROM RootPixels WHERE uuid = ? AND digest = ?
        """, (uuid, digest))

        row = cursor.fetchone()
        if row and row[0]:
            try:
                return Image.open(BytesIO(row[0]))
            except Exception:
                return None

        return None

    def get_preview_stats(self) -> Dict:
        """Get statistics about available previews."""
        self.connect()
        cursor = self.previews_conn.cursor()

        stats = {}

        cursor.execute("SELECT COUNT(*) FROM Pyramid")
        stats["total_pyramids"] = cursor.fetchone()[0]

        cursor.execute("""
            SELECT level, COUNT(*), MAX(longDimension)
            FROM PyramidLevel
            GROUP BY level
            ORDER BY level
        """)
        stats["levels"] = {
            int(row[0]): {"count": row[1], "max_size": int(row[2])}
            for row in cursor.fetchall()
        }

        return stats

    def build_path_uuid_index(self) -> Dict[Path, str]:
        """Build complete index of file paths to preview UUIDs."""
        self.connect()

        # Get all images from catalog with their paths
        cursor = self.catalog_conn.cursor()
        cursor.execute("""
            SELECT
                i.id_local,
                f.baseName,
                f.extension,
                fo.pathFromRoot,
                r.absolutePath
            FROM Adobe_images i
            JOIN AgLibraryFile f ON i.rootFile = f.id_local
            JOIN AgLibraryFolder fo ON f.folder = fo.id_local
            JOIN AgLibraryRootFolder r ON fo.rootFolder = r.id_local
        """)

        catalog_images = {}
        for row in cursor.fetchall():
            img_id, name, ext, folder, root = row
            catalog_path = f"{root}{folder}{name}.{ext}"
            actual_path = self._map_path(catalog_path)
            catalog_images[img_id] = actual_path

        # Get all preview UUIDs
        cursor = self.previews_conn.cursor()
        cursor.execute("SELECT imageId, uuid FROM ImageCacheEntry")

        index = {}
        for img_id, uuid in cursor.fetchall():
            img_id = int(img_id)
            if img_id in catalog_images:
                path = catalog_images[img_id]
                index[path] = uuid
                self._image_uuid_cache[path] = uuid

        return index


def test_preview_extraction():
    """Test preview extraction functionality."""
    print("=" * 60)
    print("LIGHTROOM PREVIEW EXTRACTION TEST")
    print("=" * 60)

    lp = LightroomPreviews()

    # Get stats
    print("\n=== Preview Statistics ===")
    stats = lp.get_preview_stats()
    print(f"Total images with previews: {stats['total_pyramids']}")
    print("\nPreview levels:")
    for level, info in stats["levels"].items():
        print(f"  Level {level}: {info['count']} images, max {info['max_size']}px")

    # Build index
    print("\n=== Building path index ===")
    index = lp.build_path_uuid_index()
    print(f"Indexed {len(index)} images")

    # Test preview extraction on a sample image
    print("\n=== Sample preview extraction ===")
    sample_path = list(index.keys())[0] if index else None
    if sample_path:
        print(f"Testing: {sample_path}")

        # Get different sizes
        for size in [512, 1024, 2048]:
            preview = lp.get_preview(sample_path, min_size=256, prefer_size=size)
            if preview:
                print(f"  Size {size}: got {preview.size}")

        # Get thumbnail
        thumb = lp.get_thumbnail(sample_path)
        if thumb:
            print(f"  Thumbnail: {thumb.size}")

    lp.close()


if __name__ == "__main__":
    test_preview_extraction()
