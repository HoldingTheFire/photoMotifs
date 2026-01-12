# PhotoMotifs

CLIP-based semantic photo search tool with Lightroom Preview integration.

## Features

- **Web UI**: User-friendly Gradio interface for searching, indexing, and configuration
- **Semantic Search**: Find photos by natural language descriptions ("sunset portrait", "rusty metal")
- **Lightroom Integration**: Uses rendered previews with all your Lightroom edits baked in
- **Semantic Tagging**: Auto-generated tags for subject, scene, style, mood, and technical aspects
- **GPU Accelerated**: CUDA support for fast embedding computation (~45 images/sec)

## Requirements

- Python 3.10+
- NVIDIA GPU with CUDA (recommended, tested on RTX 3080)
- Lightroom Classic (for preview integration)

## Installation

```bash
# Create conda environment
conda create -n photomotifs python=3.10
conda activate photomotifs

# Install PyTorch with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118

# Install dependencies
pip install transformers pillow tqdm numpy gradio
```

## Quick Start

### Web UI (Recommended)

```bash
python run_ui.py
```

This opens a browser with the PhotoMotifs interface:
- **Search Tab**: Enter queries, view results gallery, copy files
- **Indexing Tab**: Build/update embeddings with progress tracking
- **Tags Tab**: Generate and browse semantic tags
- **Settings Tab**: Configure paths to your photo library and Lightroom

### Command Line

```bash
# Search for photos
python photo_search.py "sunset landscape"
python photo_search.py "portrait with bokeh" --top-n 50

# Index library (first time or after adding photos)
python photo_search.py --index-only

# Force reindex (regenerate all embeddings)
python photo_search.py --force-reindex --index-only
```

## Configuration

### Via Web UI (Recommended)
1. Launch `python run_ui.py`
2. Go to **Settings** tab
3. Configure your paths and click **Save**

### Via config.json
Settings are saved to `config.json` (auto-generated on first run):

```json
{
  "photo_source": "Z:\\Zefram Photography",
  "working_dir": "C:\\projects\\photoMotifs\\working",
  "results_dir": "C:\\projects\\photoMotifs\\results",
  "cache_dir": "C:\\projects\\photoMotifs\\cache",
  "lr_catalog_path": "C:\\Users\\...\\Lightroom Catalog.lrcat",
  "lr_previews_dir": "C:\\Users\\...\\Lightroom Catalog Previews.lrdata"
}
```

## How It Works

1. **Lightroom Previews**: Images are loaded from Lightroom's rendered preview cache, which includes all edits (exposure, color grading, crops, negative conversions)
2. **CLIP Embeddings**: Images are converted to 512-dimensional vectors using OpenAI's CLIP model
3. **Semantic Search**: Text queries are embedded and compared to image embeddings via cosine similarity
4. **Caching**: Embeddings are cached to disk for fast subsequent searches

### Why Lightroom Previews?

- **Edit-aware search**: CLIP sees your edited photos, not raw originals
- **Correct colors**: White balance, exposure, and color grading are baked in
- **Proper crops**: Cropped images show only the visible portion
- **Film negatives**: Negative Lab Pro conversions appear as positives
- **98.9% coverage**: Most images in your catalog have previews available

## Semantic Tags

Pre-generate tags for faster filtered searches:

```bash
# Generate tags for all images
python tag_generator.py --generate

# Search with tag filtering
python tag_generator.py --search "portrait" --filter people outdoor
```

**Tag Categories:**
- **Subject**: people, animals, vehicles, buildings, nature, water, food, objects
- **Scene**: indoor, outdoor, urban, rural, nature_scene
- **Style**: portrait, landscape_style, macro, action, still_life
- **Mood**: bright, dark, warm, cool
- **Technical**: bokeh, sharp, black_white, color

## Project Structure

```
photoMotifs/
├── run_ui.py                    # Web UI launcher
├── photo_search.py              # CLI search tool
├── tag_generator.py             # Semantic tag generation
├── config.json                  # User settings (gitignored)
│
├── ui/                          # Gradio web interface
│   ├── app.py                   # Main app with theme customization
│   ├── config.py                # Settings management
│   ├── state.py                 # Shared app state
│   └── components/              # UI tabs
│       ├── search_tab.py
│       ├── indexing_tab.py
│       ├── tags_tab.py
│       └── settings_tab.py
│
├── src/                         # Core modules
│   ├── lightroom_integration.py # Catalog metadata reading
│   └── lightroom_preview_loader.py # Preview extraction
│
├── cache/                       # Cached data (gitignored)
│   ├── embeddings_cache.pkl     # CLIP embeddings
│   └── tag_database.json        # Semantic tags
│
├── results/                     # HTML search reports
└── old/                         # Deprecated scripts
```

## Customizing the UI

Edit theme colors and fonts in `ui/app.py`:

```python
# Primary accent color
PRIMARY_COLOR = "#4CAF50"  # Change to any hex color

# Color theme
primary_hue=gr.themes.colors.green  # red, orange, yellow, green, cyan, blue, purple, pink

# Font
font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"]
```

## Performance

| Metric | Value |
|--------|-------|
| Indexing speed | ~45 images/sec |
| Full library (7,900 images) | ~4 minutes |
| Search time | <1 second |
| Lightroom preview coverage | 98.9% |

Tested on NVIDIA RTX 3080 with CUDA.

## License

MIT
