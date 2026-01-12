"""
Configuration management for PhotoMotifs UI.
Persists user settings to config.json.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, Optional

# Config file location (next to this module's parent)
CONFIG_FILE = Path(__file__).parent.parent / "config.json"


@dataclass
class PhotoMotifsConfig:
    """User-configurable settings for PhotoMotifs."""

    # Photo library paths
    photo_source: str = r"Z:\Zefram Photography"
    working_dir: str = r"C:\projects\photoMotifs\working"
    results_dir: str = r"C:\projects\photoMotifs\results"
    cache_dir: str = r"C:\projects\photoMotifs\cache"

    # Lightroom integration
    lr_catalog_path: str = r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat"
    lr_previews_dir: str = r"C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Previews.lrdata"
    lr_path_mappings: Dict[str, str] = field(default_factory=lambda: {
        "M:/Zefram Photography/": "Z:/Zefram Photography/",
        "M:\\Zefram Photography\\": "Z:\\Zefram Photography\\",
    })

    # Search defaults
    default_top_n: int = 25
    thumbnail_size: int = 300

    # Model settings
    model_name: str = "openai/clip-vit-base-patch32"

    @classmethod
    def load(cls) -> "PhotoMotifsConfig":
        """Load config from file or return defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                # Handle nested dict for path mappings
                return cls(**data)
            except Exception as e:
                print(f"Warning: Could not load config: {e}")
        return cls()

    def save(self) -> None:
        """Save config to file."""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(asdict(self), f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save config: {e}")

    @property
    def embeddings_cache_path(self) -> Path:
        """Path to embeddings cache file."""
        return Path(self.cache_dir) / "embeddings_cache.pkl"

    @property
    def tag_database_path(self) -> Path:
        """Path to tag database file."""
        return Path(self.cache_dir) / "tag_database.json"

    def validate_paths(self) -> Dict[str, bool]:
        """Validate that configured paths exist."""
        paths = {
            "photo_source": Path(self.photo_source),
            "working_dir": Path(self.working_dir),
            "results_dir": Path(self.results_dir),
            "cache_dir": Path(self.cache_dir),
        }

        # Optional Lightroom paths
        if self.lr_catalog_path:
            paths["lr_catalog"] = Path(self.lr_catalog_path)
        if self.lr_previews_dir:
            paths["lr_previews"] = Path(self.lr_previews_dir)

        return {name: path.exists() for name, path in paths.items()}

    def ensure_directories(self) -> None:
        """Create working directories if they don't exist."""
        for dir_path in [self.working_dir, self.results_dir, self.cache_dir]:
            Path(dir_path).mkdir(parents=True, exist_ok=True)
