"""
Lightroom Classic integration for PhotoMotifs.
Reads catalog database to get ratings, picks, keywords, and collections.
"""
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

# Default catalog path - update if different
CATALOG_PATH = Path(r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat")

# Path mapping: Lightroom stores M:, actual files are on Z:
PATH_MAPPINGS = {
    "M:/Zefram Photography/": "Z:/Zefram Photography/",
    "M:\\Zefram Photography\\": "Z:\\Zefram Photography\\",
}


class PickFlag(Enum):
    REJECTED = -1
    UNFLAGGED = 0
    PICKED = 1


@dataclass
class LightroomImage:
    """Metadata for an image from Lightroom catalog."""
    catalog_path: str      # Path as stored in catalog
    actual_path: Path      # Mapped to actual filesystem
    filename: str
    extension: str
    rating: int            # 0-5 stars
    pick: PickFlag         # Pick/Reject/Unflagged
    color_label: str       # Color label name
    keywords: List[str]    # Applied keywords
    collections: List[str] # Collections containing this image


class LightroomCatalog:
    """Interface to Lightroom Classic catalog database."""

    def __init__(self, catalog_path: Path = CATALOG_PATH):
        self.catalog_path = catalog_path
        self.conn = None
        self._images_cache: Dict[str, LightroomImage] = {}
        self._keywords_cache: Dict[int, str] = {}
        self._collections_cache: Dict[int, str] = {}

    def connect(self):
        """Open read-only connection to catalog."""
        if self.conn is None:
            # Read-only mode to avoid locking issues with Lightroom
            self.conn = sqlite3.connect(
                f'file:{self.catalog_path}?mode=ro',
                uri=True
            )
            self._load_keywords()
            self._load_collections()

    def close(self):
        """Close connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def _map_path(self, catalog_path: str) -> Path:
        """Map catalog path to actual filesystem path."""
        result = catalog_path
        for old, new in PATH_MAPPINGS.items():
            result = result.replace(old, new)
        return Path(result)

    def _load_keywords(self):
        """Load keyword ID to name mapping."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT id_local, name FROM AgLibraryKeyword")
        self._keywords_cache = {row[0]: row[1] for row in cursor.fetchall()}

    def _load_collections(self):
        """Load collection ID to name mapping."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT id_local, name FROM AgLibraryCollection
            WHERE creationId = 'com.adobe.ag.library.collection'
        """)
        self._collections_cache = {row[0]: row[1] for row in cursor.fetchall()}

    def get_image_keywords(self, image_id: int) -> List[str]:
        """Get keywords for an image."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT tag FROM AgLibraryKeywordImage WHERE image = ?
        """, (image_id,))
        return [self._keywords_cache.get(row[0], "") for row in cursor.fetchall()]

    def get_image_collections(self, image_id: int) -> List[str]:
        """Get collections containing an image."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT collection FROM AgLibraryCollectionImage WHERE image = ?
        """, (image_id,))
        return [self._collections_cache.get(row[0], "") for row in cursor.fetchall()]

    def get_all_images(self) -> Dict[Path, LightroomImage]:
        """Load all images from catalog with their metadata."""
        self.connect()
        cursor = self.conn.cursor()

        # Main query to get image info
        query = """
        SELECT
            i.id_local,
            f.baseName,
            f.extension,
            fo.pathFromRoot,
            r.absolutePath,
            i.rating,
            i.colorLabels,
            i.pick
        FROM Adobe_images i
        JOIN AgLibraryFile f ON i.rootFile = f.id_local
        JOIN AgLibraryFolder fo ON f.folder = fo.id_local
        JOIN AgLibraryRootFolder r ON fo.rootFolder = r.id_local
        """

        cursor.execute(query)
        rows = cursor.fetchall()

        images = {}
        for row in rows:
            img_id, name, ext, folder_path, root_path, rating, color, pick = row

            # Build full catalog path
            catalog_path = f"{root_path}{folder_path}{name}.{ext}"
            actual_path = self._map_path(catalog_path)

            # Get keywords and collections
            keywords = self.get_image_keywords(img_id)
            collections = self.get_image_collections(img_id)

            # Map color label code to name
            color_map = {
                "": "None", "red": "Red", "yellow": "Yellow",
                "green": "Green", "blue": "Blue", "purple": "Purple"
            }
            color_name = color_map.get(color or "", "None")

            lr_image = LightroomImage(
                catalog_path=catalog_path,
                actual_path=actual_path,
                filename=f"{name}.{ext}",
                extension=ext,
                rating=int(rating or 0),
                pick=PickFlag(pick or 0),
                color_label=color_name,
                keywords=keywords,
                collections=collections
            )

            images[actual_path] = lr_image

        self._images_cache = images
        return images

    def get_image(self, path: Path) -> Optional[LightroomImage]:
        """Get Lightroom metadata for a specific image."""
        if not self._images_cache:
            self.get_all_images()

        # Try exact match first
        if path in self._images_cache:
            return self._images_cache[path]

        # Try matching by filename (for RAW/JPG pairs)
        stem = path.stem.lower()
        for cached_path, img in self._images_cache.items():
            if cached_path.stem.lower() == stem:
                return img

        return None

    def filter_by_rating(self, min_rating: int = 1) -> List[Path]:
        """Get paths of images with at least min_rating stars."""
        if not self._images_cache:
            self.get_all_images()

        return [
            path for path, img in self._images_cache.items()
            if img.rating >= min_rating
        ]

    def filter_by_pick(self, picked_only: bool = True) -> List[Path]:
        """Get paths of picked (or rejected if picked_only=False) images."""
        if not self._images_cache:
            self.get_all_images()

        target = PickFlag.PICKED if picked_only else PickFlag.REJECTED
        return [
            path for path, img in self._images_cache.items()
            if img.pick == target
        ]

    def filter_by_collection(self, collection_name: str) -> List[Path]:
        """Get paths of images in a specific collection."""
        if not self._images_cache:
            self.get_all_images()

        return [
            path for path, img in self._images_cache.items()
            if collection_name.lower() in [c.lower() for c in img.collections]
        ]

    def filter_by_keyword(self, keyword: str) -> List[Path]:
        """Get paths of images with a specific keyword."""
        if not self._images_cache:
            self.get_all_images()

        return [
            path for path, img in self._images_cache.items()
            if keyword.lower() in [k.lower() for k in img.keywords]
        ]

    def get_statistics(self) -> Dict:
        """Get catalog statistics."""
        if not self._images_cache:
            self.get_all_images()

        stats = {
            "total_images": len(self._images_cache),
            "by_rating": {i: 0 for i in range(6)},
            "picked": 0,
            "rejected": 0,
            "with_keywords": 0,
            "in_collections": 0,
        }

        for img in self._images_cache.values():
            stats["by_rating"][img.rating] += 1
            if img.pick == PickFlag.PICKED:
                stats["picked"] += 1
            elif img.pick == PickFlag.REJECTED:
                stats["rejected"] += 1
            if img.keywords:
                stats["with_keywords"] += 1
            if img.collections:
                stats["in_collections"] += 1

        return stats

    def list_collections(self) -> List[str]:
        """List all collection names."""
        self.connect()
        return list(self._collections_cache.values())

    def list_keywords(self) -> List[str]:
        """List all keyword names."""
        self.connect()
        return list(self._keywords_cache.values())


def print_catalog_summary():
    """Print a summary of the Lightroom catalog."""
    catalog = LightroomCatalog()
    catalog.connect()

    print("=" * 60)
    print("LIGHTROOM CATALOG SUMMARY")
    print("=" * 60)

    stats = catalog.get_statistics()

    print(f"\nTotal images: {stats['total_images']}")
    print(f"\nBy rating:")
    for rating, count in stats["by_rating"].items():
        if count > 0:
            stars = '*' * rating if rating > 0 else '(unrated)'
            print(f"  {stars:10} {count}")

    print(f"\nPicked: {stats['picked']}")
    print(f"Rejected: {stats['rejected']}")
    print(f"With keywords: {stats['with_keywords']}")
    print(f"In collections: {stats['in_collections']}")

    print(f"\nCollections:")
    for name in catalog.list_collections():
        print(f"  - {name}")

    print(f"\nKeywords:")
    for name in catalog.list_keywords():
        print(f"  - {name}")

    catalog.close()


if __name__ == "__main__":
    print_catalog_summary()
