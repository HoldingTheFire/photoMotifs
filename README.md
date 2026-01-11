# PhotoMotifs

CLIP-based semantic photo search tool with Lightroom Smart Preview integration.

## Features

- **Semantic Search**: Find photos by natural language descriptions ("sunset portrait", "black and white street photography")
- **Lightroom Integration**: Uses Smart Previews with your Lightroom edits baked in
- **Semantic Tagging**: Auto-generated tags for subject, scene, style, mood, and technical aspects
- **GPU Accelerated**: CUDA support for fast embedding computation

## Requirements

- Python 3.10+
- NVIDIA GPU with CUDA (tested on RTX 3080)
- Lightroom Classic (for Smart Preview integration)

## Installation

```bash
conda create -n photomotifs python=3.10
conda activate photomotifs
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
pip install transformers pillow tqdm rawpy numpy
```

## Usage

### Basic Search
```bash
python photo_search.py "sunset landscape"
python photo_search.py "portrait of a person" -n 50
```

### Index Library
```bash
# First-time indexing
python photo_search.py --index-only

# Force reindex (regenerate all embeddings)
python photo_search.py --force-reindex --index-only
```

### Smart Preview Integration
```bash
# Rebuild Smart Preview mapping from Lightroom catalog
python photo_search.py --rebuild-sp-cache

# Disable Smart Previews (use original files only)
python photo_search.py --no-smart-preview "query"
```

### Semantic Tags
```bash
# Generate tags for all images
python tag_generator.py --generate

# Force regenerate all tags
python tag_generator.py --generate --force

# Search with tag filtering
python tag_generator.py --search "portrait" --filter people outdoor
```

## Configuration

Edit paths in `photo_search.py`:

```python
PHOTO_SOURCE = Path(r"Z:\Zefram Photography")  # Your photo library
WORKING_DIR = Path(r"C:\projects\photoMotifs\working")
RESULTS_DIR = Path(r"C:\projects\photoMotifs\results")
```

Lightroom catalog path in `src/smart_preview_mapper.py`:
```python
CATALOG_PATH = Path(r"C:\Users\...\Lightroom Catalog.lrcat")
SP_DIR = Path(r"C:\Users\...\Lightroom Catalog Smart Previews.lrdata")
```

## How It Works

1. **CLIP Embeddings**: Images are converted to 512-dimensional vectors using OpenAI's CLIP model
2. **Smart Preview Mapping**: Maps original files to Lightroom Smart Previews via capture date matching
3. **Film Type Detection**: Analog film scans are automatically processed based on film type
4. **Semantic Search**: Text queries are embedded and compared to image embeddings via cosine similarity
5. **Caching**: Embeddings are cached to disk for fast subsequent searches

## Analog Film Processing

Film scans in the `Analog/` folder are automatically detected and processed appropriately:

| Film Type | Examples | Processing |
|-----------|----------|------------|
| Slide film | Velvia, Ektachrome, Provia, Kodachrome | No inversion (positive) |
| B&W negative | TMAX, HP5, Tri-X, Ilford, Delta | Simple grayscale inversion |
| Color negative | Portra, Ektar, CineStill, Gold | Orange mask removal + inversion |
| Already processed | Underdog, Nikon Scan | No processing |

Detection uses:
1. **Lightroom profile lookup** - "Negative Lab v2.3" indicates already converted
2. **Folder name patterns** - Film stock names in path (e.g., "Roll 12 Fujifilm Velvia 50")

### Reindex Analog Files
```bash
# Clear and rebuild embeddings for Analog folder
python scripts/reindex_analog.py
```

## Project Structure

```
photoMotifs/
├── photo_search.py              # Main search tool with CLIP embeddings
├── tag_generator.py             # Semantic tag generation and filtered search
├── README.md
├── CLAUDE.md                    # AI assistant instructions
├── .gitignore
│
├── src/                         # Source modules
│   ├── lightroom_integration.py # Lightroom catalog metadata reading
│   └── smart_preview_mapper.py  # Smart Preview path mapping
│
├── scripts/                     # Utility scripts
│   └── reindex_analog.py        # Reindex analog film negatives
│
├── tests/                       # Test files
│   ├── benchmark.py             # Performance benchmarks
│   ├── test_*.py                # Various test scripts
│   └── fixtures/                # Test images (generated)
│
├── cache/                       # Cached data (gitignored)
│   ├── embeddings_cache.pkl     # CLIP embeddings
│   ├── smart_preview_mapping.pkl # Smart Preview mappings
│   └── tag_database.json        # Semantic tags database
│
├── results/                     # Search results HTML reports
└── old/                         # Deprecated exploration scripts
```

## Performance

- ~7,900 images indexed in ~29 minutes (RTX 3080)
- ~10 images/second embedding computation
- Searches complete in <1 second

## License

MIT
