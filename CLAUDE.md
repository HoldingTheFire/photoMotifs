# PhotoMotifs - CLIP-based Photo Search Tool

## Project Overview
A Python tool to search through a photo library for images matching specific motifs or themes using OpenAI's CLIP model for zero-shot image classification.

## Key Paths
- **Photo Source:** `Z:\Zefram Photography\` (READ-ONLY - never modify)
- **Working Directory:** `C:\projects\photoMotifs\working\`
- **Results Directory:** `C:\projects\photoMotifs\results\`
- **Embeddings Cache:** `C:\projects\photoMotifs\embeddings_cache.pkl`
- **Conda Environment:** `photomotifs`

## Photo Library Structure
- Organized by capture event or source (e.g., "Bike Rides", "Photo Walk")
- `Z:\Zefram Photography\Analog\` - Film scans organized by camera and roll
- When RAW (.RAF, .DNG) and JPG share same name, JPG is camera-processed output
- Preference: camera JPG > embedded RAW preview > RAW conversion

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

## Current Status (2025-12-27)
- **Total Images:** 7,908 unique
- **Cached Embeddings:** 7,532
- **Failed to Process:** 377 (DNG files without embedded previews)
- **GPU:** NVIDIA RTX 3080 (CUDA enabled)
- **Performance:** ~10 images/sec, full library scan ~6.5 minutes

## Files
- `photo_search.py` - Main search tool (571 lines)
- `test_search.py` - Quick test on subset
- `benchmark.py` - Performance benchmark
- `embeddings_cache.pkl` - Cached CLIP embeddings (~16 MB)
- `results/indexing_errors.log` - Files that failed to process

## Technical Details
- **Model:** `openai/clip-vit-base-patch32`
- **Supported formats:** .jpg, .jpeg, .raf, .dng, .tiff, .tif
- **Thumbnail size:** 300px for HTML reports
- **Default results:** Top 25

## Known Issues
1. DNG files without embedded JPEG previews fail (377 files)
2. rawpy disabled due to segfaults on some files
3. First image takes ~500ms (GPU warmup), then ~50-100ms each

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
- `lightroom_integration.py` - Read ratings, picks, keywords, collections from catalog
- Filter searches by Lightroom metadata (e.g., only 4+ star images)
- 13,415 images in catalog with metadata

### Usage
```bash
# Print catalog summary
conda run -n photomotifs python lightroom_integration.py
```

### Available Metadata
- **Ratings:** 0-5 stars (20 images rated 4+)
- **Picks:** 133 picked, 67 rejected
- **Keywords:** 32 keywords, 660 images tagged
- **Collections:** 15 collections (Nature, Monochrome, Creative, etc.)

### Lightroom Previews (WIP)
- Smart Previews: 7,383 DNG files with edits baked in
- Regular Previews: `.lrprev` files (proprietary format - extraction not implemented)
- **Note:** To use Lightroom-edited images for CLIP, would need to regenerate embeddings

### Known Limitations
1. Smart Preview UUID mapping is incomplete (schema is complex)
2. `.lrprev` format is proprietary Adobe container (not standard JPEG)
3. Current CLIP embeddings are from original/embedded JPEGs, not Lightroom-edited versions
