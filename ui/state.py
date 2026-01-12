"""
Shared application state for PhotoMotifs UI.
Manages loaded models, caches, and configuration.
"""

import sys
from pathlib import Path
from typing import Optional, List

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ui.config import PhotoMotifsConfig


class AppState:
    """
    Shared application state across all UI components.
    Manages loaded models, caches, and configuration.
    """

    def __init__(self, config: Optional[PhotoMotifsConfig] = None):
        self.config = config or PhotoMotifsConfig.load()
        self._searcher = None
        self._tag_generator = None
        self._lr_catalog = None
        self._initialized = False

        # Ensure working directories exist
        self.config.ensure_directories()

    def reload_config(self) -> None:
        """Reload configuration after settings change."""
        self.config = PhotoMotifsConfig.load()
        # Invalidate cached objects that depend on paths
        self._searcher = None
        self._tag_generator = None
        self._lr_catalog = None
        # Reconfigure Lightroom preview loader
        self._configure_lr_loader()

    def _configure_lr_loader(self) -> None:
        """Configure Lightroom preview loader with current settings."""
        try:
            from src.lightroom_preview_loader import configure
            configure(
                catalog_path=Path(self.config.lr_catalog_path) if self.config.lr_catalog_path else None,
                previews_dir=Path(self.config.lr_previews_dir) if self.config.lr_previews_dir else None,
                path_mappings=self.config.lr_path_mappings
            )
        except ImportError:
            pass  # Module not yet refactored
        except Exception as e:
            print(f"Warning: Could not configure LR loader: {e}")

    def get_searcher(self):
        """Get or create PhotoSearcher instance."""
        if self._searcher is None:
            from photo_search import PhotoSearcher
            self._searcher = PhotoSearcher(
                model_name=self.config.model_name,
                cache_path=self.config.embeddings_cache_path
            )
            self._configure_lr_loader()
        return self._searcher

    def get_tag_generator(self):
        """Get or create TagGenerator instance."""
        if self._tag_generator is None:
            from tag_generator import TagGenerator
            self._tag_generator = TagGenerator(
                db_path=self.config.tag_database_path
            )
        return self._tag_generator

    @property
    def lr_catalog(self):
        """Get Lightroom catalog connection (lazy loaded)."""
        if self._lr_catalog is None and self.config.lr_catalog_path:
            try:
                from src.lightroom_integration import LightroomCatalog
                self._lr_catalog = LightroomCatalog(
                    catalog_path=Path(self.config.lr_catalog_path)
                )
            except Exception as e:
                print(f"Warning: Could not connect to Lightroom catalog: {e}")
        return self._lr_catalog

    def get_lr_collections(self) -> List[str]:
        """Get list of Lightroom collections."""
        if self.lr_catalog:
            try:
                return ["All Collections"] + self.lr_catalog.list_collections()
            except Exception:
                pass
        return ["All Collections"]

    def get_lr_keywords(self) -> List[str]:
        """Get list of Lightroom keywords."""
        if self.lr_catalog:
            try:
                return ["All Keywords"] + self.lr_catalog.list_keywords()
            except Exception:
                pass
        return ["All Keywords"]

    def get_index_stats(self) -> dict:
        """Get current index statistics."""
        from photo_search import find_images
        from datetime import datetime

        stats = {
            "total_images": 0,
            "cached_embeddings": 0,
            "last_indexed": "Never"
        }

        # Count images in source
        source = Path(self.config.photo_source)
        if source.exists():
            try:
                images = find_images(source)
                stats["total_images"] = len(images)
            except Exception:
                pass

        # Count cached embeddings
        cache_path = self.config.embeddings_cache_path
        if cache_path.exists():
            try:
                import pickle
                with open(cache_path, 'rb') as f:
                    cache = pickle.load(f)
                stats["cached_embeddings"] = len(cache)
                # Get modification time
                mtime = cache_path.stat().st_mtime
                stats["last_indexed"] = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        return stats
