"""
Pre-generate semantic tags for all images using CLIP.
Creates a searchable tag database for fast filtering before detailed search.
"""

import os
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import json
import pickle
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime

import numpy as np
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel
from tqdm import tqdm

from photo_search import (
    PHOTO_SOURCE, RESULTS_DIR, CACHE_FILE,
    find_images, load_image, EmbeddingCache
)

# Tag database path
TAG_DB_FILE = Path(r"C:\projects\photoMotifs\tag_database.json")

# Hierarchical tag categories with CLIP-friendly descriptions
TAG_CATEGORIES = {
    "subject": {
        "people": ["person", "people", "human", "portrait", "face", "crowd"],
        "animals": ["animal", "pet", "dog", "cat", "bird", "wildlife"],
        "vehicles": ["car", "vehicle", "bicycle", "motorcycle", "train", "airplane"],
        "buildings": ["building", "architecture", "house", "skyscraper", "church"],
        "nature": ["landscape", "mountain", "forest", "tree", "flower", "plant"],
        "water": ["water", "ocean", "lake", "river", "waterfall", "beach"],
        "food": ["food", "meal", "fruit", "vegetable", "drink"],
        "objects": ["object", "tool", "furniture", "electronics"],
    },
    "scene": {
        "indoor": ["indoor", "interior", "room", "inside"],
        "outdoor": ["outdoor", "outside", "exterior"],
        "urban": ["city", "urban", "street", "downtown"],
        "rural": ["rural", "countryside", "farm", "village"],
        "nature_scene": ["nature", "wilderness", "park", "garden"],
    },
    "style": {
        "portrait": ["portrait", "headshot", "close-up of face"],
        "landscape_style": ["landscape photo", "wide shot", "scenic view"],
        "macro": ["macro", "close-up", "detail shot"],
        "action": ["action", "motion", "movement", "sports"],
        "still_life": ["still life", "arrangement", "tabletop"],
    },
    "mood": {
        "bright": ["bright", "sunny", "cheerful", "vibrant"],
        "dark": ["dark", "moody", "dramatic", "shadowy"],
        "warm": ["warm colors", "golden hour", "sunset tones"],
        "cool": ["cool colors", "blue tones", "cold"],
    },
    "technical": {
        "bokeh": ["shallow depth of field", "bokeh", "blurred background"],
        "sharp": ["sharp focus", "crisp", "detailed"],
        "black_white": ["black and white", "monochrome", "grayscale"],
        "color": ["colorful", "vivid colors", "saturated"],
    }
}

# Flatten tags for CLIP processing
def get_all_tags() -> List[Tuple[str, str, str]]:
    """Returns list of (category, tag_name, description) tuples."""
    tags = []
    for category, tag_dict in TAG_CATEGORIES.items():
        for tag_name, descriptions in tag_dict.items():
            # Use first description as primary
            tags.append((category, tag_name, descriptions[0]))
    return tags


@dataclass
class ImageTags:
    """Tags for a single image."""
    path: str
    tags: Dict[str, List[str]]  # category -> list of tags
    scores: Dict[str, float]    # tag -> confidence score
    indexed_at: str


class TagDatabase:
    """Manages the tag database."""

    def __init__(self, db_path: Path = TAG_DB_FILE):
        self.db_path = db_path
        self.data: Dict[str, ImageTags] = {}
        self.load()

    def load(self):
        """Load database from disk."""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r') as f:
                    raw = json.load(f)
                self.data = {k: ImageTags(**v) for k, v in raw.items()}
                print(f"Loaded {len(self.data)} tagged images")
            except Exception as e:
                print(f"Warning: Could not load tag database: {e}")
                self.data = {}

    def save(self):
        """Save database to disk."""
        raw = {k: asdict(v) for k, v in self.data.items()}
        with open(self.db_path, 'w') as f:
            json.dump(raw, f, indent=2)
        print(f"Saved {len(self.data)} tagged images")

    def add(self, path: Path, tags: Dict[str, List[str]], scores: Dict[str, float]):
        """Add tags for an image."""
        self.data[str(path)] = ImageTags(
            path=str(path),
            tags=tags,
            scores=scores,
            indexed_at=datetime.now().isoformat()
        )

    def get(self, path: Path) -> ImageTags:
        """Get tags for an image."""
        return self.data.get(str(path))

    def search_by_tags(self, required_tags: Set[str],
                       min_score: float = 0.2) -> List[Tuple[Path, float]]:
        """
        Find images that have ALL required tags with score >= min_score.
        Returns list of (path, min_tag_score) sorted by score.
        """
        results = []
        for path_str, img_tags in self.data.items():
            # Check if all required tags are present with sufficient score
            tag_scores = []
            all_present = True
            for tag in required_tags:
                if tag in img_tags.scores and img_tags.scores[tag] >= min_score:
                    tag_scores.append(img_tags.scores[tag])
                else:
                    all_present = False
                    break

            if all_present and tag_scores:
                results.append((Path(path_str), min(tag_scores)))

        return sorted(results, key=lambda x: x[1], reverse=True)

    def search_fuzzy(self, query_tags: Set[str],
                     min_matches: int = 1,
                     min_score: float = 0.2) -> List[Tuple[Path, float, int]]:
        """
        Fuzzy search - find images matching at least min_matches tags.
        Returns list of (path, avg_score, match_count) sorted by match count then score.
        """
        results = []
        for path_str, img_tags in self.data.items():
            matched_scores = []
            for tag in query_tags:
                if tag in img_tags.scores and img_tags.scores[tag] >= min_score:
                    matched_scores.append(img_tags.scores[tag])

            if len(matched_scores) >= min_matches:
                avg_score = sum(matched_scores) / len(matched_scores)
                results.append((Path(path_str), avg_score, len(matched_scores)))

        # Sort by match count (desc), then by score (desc)
        return sorted(results, key=lambda x: (x[2], x[1]), reverse=True)


class TagGenerator:
    """Generates tags for images using CLIP."""

    def __init__(self, model_name: str = "openai/clip-vit-base-patch32"):
        print(f"Loading CLIP model for tagging...")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {self.device}")

        self.model = CLIPModel.from_pretrained(model_name).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(model_name, use_fast=True)
        self.model.eval()

        # Pre-compute text embeddings for all tags
        self.tags = get_all_tags()
        self.tag_names = [t[1] for t in self.tags]
        self.tag_embeddings = self._compute_tag_embeddings()

        self.db = TagDatabase()

    def _compute_tag_embeddings(self) -> np.ndarray:
        """Pre-compute CLIP embeddings for all tag descriptions."""
        print(f"Computing embeddings for {len(self.tags)} tags...")
        descriptions = [f"a photo of {t[2]}" for t in self.tags]

        inputs = self.processor(text=descriptions, return_tensors="pt",
                               padding=True, truncation=True).to(self.device)

        with torch.no_grad():
            embeddings = self.model.get_text_features(**inputs)
            embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)

        return embeddings.cpu().numpy()

    def tag_image(self, image: Image.Image,
                  threshold: float = 0.2,
                  top_k_per_category: int = 2) -> Tuple[Dict[str, List[str]], Dict[str, float]]:
        """
        Generate tags for an image.
        Returns (tags_by_category, all_scores).
        """
        # Compute image embedding
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        with torch.no_grad():
            img_embedding = self.model.get_image_features(**inputs)
            img_embedding = img_embedding / img_embedding.norm(dim=-1, keepdim=True)

        img_embedding = img_embedding.cpu().numpy().flatten()

        # Compute similarity with all tags
        similarities = self.tag_embeddings @ img_embedding

        # Organize by category and filter
        tags_by_category = {}
        all_scores = {}

        for i, (category, tag_name, _) in enumerate(self.tags):
            score = float(similarities[i])
            all_scores[tag_name] = score

            if score >= threshold:
                if category not in tags_by_category:
                    tags_by_category[category] = []
                tags_by_category[category].append((tag_name, score))

        # Keep top-k per category
        for category in tags_by_category:
            sorted_tags = sorted(tags_by_category[category], key=lambda x: x[1], reverse=True)
            tags_by_category[category] = [t[0] for t in sorted_tags[:top_k_per_category]]

        return tags_by_category, all_scores

    def process_library(self, source_dir: Path = PHOTO_SOURCE,
                       force_retag: bool = False,
                       save_interval: int = 100):
        """Tag all images in the library."""
        import gc

        images = find_images(source_dir)
        new_tags = 0
        errors = []

        print(f"\nTagging {len(images)} images...")

        for i, path in enumerate(tqdm(images, desc="Generating tags")):
            # Skip if already tagged
            if not force_retag and self.db.get(path):
                continue

            try:
                image, source_type = load_image(path)
                if image is None:
                    errors.append(path)
                    continue

                # Resize for efficiency
                image.thumbnail((512, 512), Image.Resampling.LANCZOS)

                tags, scores = self.tag_image(image)
                self.db.add(path, tags, scores)
                new_tags += 1

                del image

                # Periodic save
                if new_tags % save_interval == 0:
                    self.db.save()
                    gc.collect()
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()

            except Exception as e:
                errors.append(path)

        self.db.save()

        print(f"\nTagged {new_tags} new images")
        if errors:
            print(f"Errors: {len(errors)} images")

    def print_available_tags(self):
        """Print all available tags by category."""
        print("\nAvailable tags by category:")
        print("-" * 40)
        for category, tag_dict in TAG_CATEGORIES.items():
            print(f"\n{category.upper()}:")
            for tag_name in tag_dict.keys():
                print(f"  - {tag_name}")


def hybrid_search(query: str,
                  filter_tags: Set[str] = None,
                  min_tag_score: float = 0.2,
                  top_n: int = 25) -> List[Tuple[Path, float]]:
    """
    Hybrid search: filter by tags first, then rank with CLIP.

    Args:
        query: Text query for CLIP ranking
        filter_tags: Set of tags to filter by (AND logic)
        min_tag_score: Minimum tag confidence
        top_n: Number of results to return
    """
    from photo_search import PhotoSearcher, ImageResult

    db = TagDatabase()

    if filter_tags:
        print(f"Filtering by tags: {filter_tags}")
        # Get candidate images
        candidates = db.search_by_tags(filter_tags, min_tag_score)
        print(f"Found {len(candidates)} images matching tag filter")

        if not candidates:
            print("No images match the tag filter. Try relaxing constraints.")
            return []

        # Now search only among candidates
        searcher = PhotoSearcher()
        # Load embeddings only for candidates
        candidate_paths = [c[0] for c in candidates]

        # Compute query embedding
        query_embedding = searcher.compute_text_embedding(query)

        # Score only candidate images
        results = []
        for path in tqdm(candidate_paths, desc="Ranking candidates"):
            cached = searcher.cache.get(path)
            if cached is not None:
                score = float(np.dot(cached, query_embedding))
                results.append((path, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_n]

    else:
        # No tag filter, use regular search
        searcher = PhotoSearcher()
        searcher.index_images(PHOTO_SOURCE)
        results = searcher.search(query, top_n)
        return [(r.path, r.score) for r in results]


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Tag-based photo search")
    parser.add_argument("--generate", action="store_true",
                       help="Generate tags for all images")
    parser.add_argument("--force", action="store_true",
                       help="Force regenerate all tags")
    parser.add_argument("--list-tags", action="store_true",
                       help="List available tags")
    parser.add_argument("--search", type=str,
                       help="Search query")
    parser.add_argument("--filter", type=str, nargs="+",
                       help="Filter by these tags (AND logic)")
    parser.add_argument("-n", "--top-n", type=int, default=25,
                       help="Number of results")

    args = parser.parse_args()

    if args.list_tags:
        gen = TagGenerator()
        gen.print_available_tags()

    elif args.generate:
        gen = TagGenerator()
        gen.process_library(force_retag=args.force)

    elif args.search:
        filter_set = set(args.filter) if args.filter else None
        results = hybrid_search(args.search, filter_set, top_n=args.top_n)

        print(f"\nTop {len(results)} results:")
        print("-" * 60)
        for i, (path, score) in enumerate(results[:10], 1):
            print(f"{i:2}. [{score:.3f}] {path.name}")
            print(f"     {path.parent}")

    else:
        parser.print_help()
