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

## Current Status (2026-01-10)
- **Total Images:** 7,908 unique
- **Cached Embeddings:** 7,870
- **Analog Images:** 1,298 (with film type detection)
- **GPU:** NVIDIA RTX 3080 (CUDA enabled)
- **Performance:** ~10 images/sec, full library scan ~6.5 minutes

## Project Structure
```
photoMotifs/
├── photo_search.py         # Main search tool
├── tag_generator.py        # Tag generation and filtered search
├── src/                    # Source modules
│   ├── lightroom_integration.py
│   └── smart_preview_mapper.py
├── scripts/                # Utility scripts
│   └── reindex_analog.py
├── tests/                  # Test files
│   ├── benchmark.py
│   ├── test_*.py
│   └── fixtures/
├── cache/                  # Cached data (gitignored)
│   ├── embeddings_cache.pkl
│   ├── smart_preview_mapping.pkl
│   └── tag_database.json
├── results/                # HTML reports and thumbnails
└── old/                    # Deprecated exploration scripts
```

## Technical Details
- **Model:** `openai/clip-vit-base-patch32`
- **Supported formats:** .jpg, .jpeg, .raf, .dng, .tiff, .tif
- **Thumbnail size:** 300px for HTML reports
- **Default results:** Top 25

## Analog Film Processing
Film scans in `Z:\Zefram Photography\Analog\` are auto-detected by type:
- **Slide films** (Velvia, Ektachrome, Provia): No inversion needed
- **B&W negatives** (TMAX, HP5, Ilford): Simple grayscale inversion
- **Color negatives** (Portra, CineStill, Ektar): Orange mask removal + inversion
- **Already processed** (Underdog, Nikon Scan): No processing

Detection logic in `photo_search.py`:
- `detect_film_type(path)` - Returns 'slide', 'bw_negative', 'color_negative', 'already_processed', or 'not_analog'
- `apply_film_processing(image, path)` - Applies correct processing based on film type
- Checks Lightroom profile first ("Negative Lab v2.3" = already converted)
- Falls back to folder name pattern matching

To reindex Analog after changes:
```bash
conda run -n photomotifs python scripts/reindex_analog.py
```

## Known Issues
1. DNG files without embedded JPEG previews fail
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

### Lightroom Previews (WIP)
- Smart Previews: 7,383 DNG files with edits baked in
- Regular Previews: `.lrprev` files (proprietary format - extraction not implemented)
- **Note:** To use Lightroom-edited images for CLIP, would need to regenerate embeddings

### Known Limitations
1. Smart Preview UUID mapping is incomplete (schema is complex)
2. `.lrprev` format is proprietary Adobe container (not standard JPEG)
3. Current CLIP embeddings are from original/embedded JPEGs, not Lightroom-edited versions
