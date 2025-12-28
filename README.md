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

Lightroom catalog path in `smart_preview_mapper.py`:
```python
CATALOG_PATH = Path(r"C:\Users\...\Lightroom Catalog.lrcat")
SP_DIR = Path(r"C:\Users\...\Lightroom Catalog Smart Previews.lrdata")
```

## How It Works

1. **CLIP Embeddings**: Images are converted to 512-dimensional vectors using OpenAI's CLIP model
2. **Smart Preview Mapping**: Maps original files to Lightroom Smart Previews via capture date matching
3. **Semantic Search**: Text queries are embedded and compared to image embeddings via cosine similarity
4. **Caching**: Embeddings are cached to disk for fast subsequent searches

## Files

| File | Description |
|------|-------------|
| `photo_search.py` | Main search tool with CLIP embeddings |
| `smart_preview_mapper.py` | Lightroom Smart Preview mapping |
| `tag_generator.py` | Semantic tag generation |
| `lightroom_integration.py` | Lightroom catalog metadata reading |
| `embeddings_cache.pkl` | Cached CLIP embeddings |
| `smart_preview_mapping.pkl` | Smart Preview path mappings |
| `tag_database.json` | Semantic tags database |

## Performance

- ~7,900 images indexed in ~29 minutes (RTX 3080)
- ~10 images/second embedding computation
- Searches complete in <1 second

## License

MIT
