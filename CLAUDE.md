# PhotoMotifs - CLIP-based Photo Search Tool

## Project Overview
A Python tool to search through a photo library for images matching specific motifs or themes using OpenAI's CLIP model for zero-shot image classification.

## Key Paths
- **Photo Source:** `Z:\Zefram Photography\` (READ-ONLY - never modify)
- **Working Directory:** `C:\projects\photoMotifs\working\`
- **Results Directory:** `C:\projects\photoMotifs\results\`
- **Cache Directory:** `C:\projects\photoMotifs\cache\`
- **Conda Environment:** `photomotifs`

## Photo Library Structure
- Organized by capture event or source (e.g., "Bike Rides", "Photo Walk")
- `Z:\Zefram Photography\Analog\` - Film scans organized by camera and roll
- All files managed in Lightroom Classic catalog
- Preference: Lightroom preview (with edits) > camera JPG > embedded RAW preview

## Running the Tool
```bash
# Activate environment
conda activate photomotifs

# Search with query
conda run -n photomotifs python photo_search.py "your search query" --top-n 25

# Index only (no search)
conda run -n photomotifs python photo_search.py --index-only

# Copy results to working folder
conda run -n photomotifs python photo_search.py "query" --copy
```

## Web UI (Gradio)
```bash
# Launch the web interface
conda run -n photomotifs python run_ui.py

# With custom port
conda run -n photomotifs python run_ui.py --port 8080
```

The web UI provides:
- **Search Tab**: Query input, results gallery, copy to folder
- **Indexing Tab**: Build/update embeddings with progress bar
- **Tags Tab**: Generate and browse semantic tags
- **Settings Tab**: Configure all paths (photo library, Lightroom, cache)

## Current Status (2026-01-11)
- **Total Images:** 7,908 unique
- **Cached Embeddings:** 7,887
- **Lightroom Preview Coverage:** 98.9% (7,822 images use LR previews with edits)
- **GPU:** NVIDIA RTX 3080 (CUDA enabled)
- **Performance:** ~45 images/sec, full library reindex ~4 minutes

## Project Structure
```
photoMotifs/
├── photo_search.py         # Main search tool (CLI)
├── tag_generator.py        # Tag generation and filtered search
├── run_ui.py               # Launch Gradio web UI
├── config.json             # User settings (gitignored)
├── ui/                     # Web UI components
│   ├── app.py              # Main Gradio application
│   ├── config.py           # Configuration management
│   ├── state.py            # Shared app state
│   └── components/         # UI tab modules
│       ├── settings_tab.py
│       ├── search_tab.py
│       ├── indexing_tab.py
│       └── tags_tab.py
├── src/                    # Source modules
│   ├── lightroom_integration.py    # Read ratings, keywords from LR catalog
│   └── lightroom_preview_loader.py # Extract rendered previews from LR cache
├── tests/                  # Test files
├── cache/                  # Cached data (gitignored)
├── results/                # HTML reports and thumbnails
└── old/                    # Deprecated scripts
```

## Technical Details
- **Model:** `openai/clip-vit-base-patch32`
- **Supported formats:** .jpg, .jpeg, .raf, .dng, .tiff, .tif
- **Thumbnail size:** 300px for HTML reports
- **Default results:** Top 25

## Lightroom Preview Integration

All images are loaded from Lightroom's rendered preview cache instead of original files. This ensures CLIP sees:
- **Correct colors**: Lightroom edits (exposure, white balance, color grading) are baked in
- **Proper crops**: Cropped images show only the visible portion
- **Converted negatives**: Film negatives with Negative Lab Pro conversions appear as positives
- **Consistent quality**: All images rendered at similar quality levels

### How It Works
1. `src/lightroom_preview_loader.py` maps file paths to Lightroom catalog image IDs
2. Looks up preview UUID and digest from `previews.db`
3. Finds rendered JPEG pyramid files in `Previews.lrdata` folder structure
4. Returns largest available preview (typically 1024px or 2048px)
5. Falls back to original file only if no LR preview exists (~1% of images)

### Force Reindex
If Lightroom edits change significantly, reindex to update embeddings:
```bash
conda run -n photomotifs python photo_search.py --index-only --force-reindex
```

## Known Issues
1. Images not in Lightroom catalog (~1%) fall back to original/embedded JPEG
2. rawpy disabled due to segfaults on some files
3. First batch takes ~500ms (GPU warmup), then ~45 images/sec

## Example Queries
- "portraits of people"
- "architecture buildings"
- "landscapes with mountains"
- "wheels and gears"
- "railroad cars"

## Tag-Based Filtering (Hybrid Search)
The `tag_generator.py` provides pre-computed semantic tags for faster filtered searches.

### Generate tags (one-time, ~10 min for full library)
```bash
conda run -n photomotifs python tag_generator.py --generate
```

### List available tags
```bash
conda run -n photomotifs python tag_generator.py --list-tags
```

### Hybrid search (filter by tags, then rank with CLIP)
```bash
# Find buildings with people
conda run -n photomotifs python tag_generator.py --search "modern architecture" --filter buildings people

# Find outdoor animal portraits
conda run -n photomotifs python tag_generator.py --search "cute pet" --filter animals outdoor
```

### Tag Categories
- **subject:** people, animals, vehicles, buildings, nature, water, food, objects
- **scene:** indoor, outdoor, urban, rural, nature_scene
- **style:** portrait, landscape_style, macro, action, still_life
- **mood:** bright, dark, warm, cool
- **technical:** bokeh, sharp, black_white, color

## Lightroom Classic Integration

### Catalog Location
- **Catalog:** `C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4.lrcat`
- **Path Mapping:** Catalog uses `M:\Zefram Photography\`, actual files on `Z:\Zefram Photography\`

### What Works
- `src/lightroom_integration.py` - Read ratings, picks, keywords, collections from catalog
- Filter searches by Lightroom metadata (e.g., only 4+ star images)
- 13,415 images in catalog with metadata

### Usage
```bash
# Print catalog summary
conda run -n photomotifs python src/lightroom_integration.py
```

### Available Metadata
- **Ratings:** 0-5 stars (20 images rated 4+)
- **Picks:** 133 picked, 67 rejected
- **Keywords:** 32 keywords, 660 images tagged
- **Collections:** 15 collections (Nature, Monochrome, Creative, etc.)

### Lightroom Previews (Implemented)
- **Pyramid previews**: JPEG files stored in `Previews.lrdata` folder with all edits baked in
- **Coverage**: 98.9% of library images have LR previews available
- **Location**: `C:\Users\zefra\OneDrive\Pictures\Lightroom\Lightroom Catalog-v13-4 Previews.lrdata`
- All CLIP embeddings are now generated from Lightroom-edited previews

### Preview Format Details
- Previews stored as bare JPEG pyramid files with size suffixes (e.g., `{uuid}-{digest}_1024`)
- `.lrprev` container files also supported (contain embedded JPEG data)
- Previews organized in subfolders by UUID prefix (e.g., `A/ABCD/`)
