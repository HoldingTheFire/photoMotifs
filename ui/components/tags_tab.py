"""
Tags Tab - Semantic tag generation and browsing for PhotoMotifs.
"""

import gradio as gr
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.state import AppState

# Tag categories (from tag_generator.py)
TAG_CATEGORIES = {
    "subject": ["people", "animals", "vehicles", "buildings", "nature", "water", "food", "objects"],
    "scene": ["indoor", "outdoor", "urban", "rural", "nature_scene"],
    "style": ["portrait", "landscape_style", "macro", "action", "still_life"],
    "mood": ["bright", "dark", "warm", "cool"],
    "technical": ["bokeh", "sharp", "black_white", "color"]
}


def create_tags_tab(state: "AppState") -> dict:
    """Create the Tag generation and browsing tab."""

    gr.Markdown("## Semantic Tags")
    gr.Markdown("""
    Pre-generate semantic tags for faster filtered searches.
    Tags categorize images by subject, scene, style, mood, and technical aspects.
    """)

    with gr.Tabs():
        with gr.Tab("Generate Tags"):
            with gr.Group():
                gr.Markdown("### Tag Generation Status")
                with gr.Row():
                    tagged_count = gr.Number(label="Tagged Images", interactive=False, value=0)
                    untagged_count = gr.Number(label="Untagged Images", interactive=False, value=0)
                    coverage_pct = gr.Textbox(label="Coverage", interactive=False, value="0%")

                refresh_tag_status_btn = gr.Button("Refresh Status", size="sm")

            with gr.Group():
                gr.Markdown("### Generation Options")
                with gr.Row():
                    force_retag = gr.Checkbox(
                        label="Force Regenerate All",
                        value=False,
                        info="Retag all images (ignores existing tags)"
                    )
                    tag_threshold = gr.Slider(
                        minimum=0.1, maximum=0.5, step=0.05, value=0.2,
                        label="Confidence Threshold"
                    )

                generate_btn = gr.Button("Generate Tags", variant="primary", size="lg")

            tag_progress = gr.Textbox(
                label="Progress",
                lines=8,
                interactive=False,
                value="Ready to generate tags..."
            )

        with gr.Tab("Browse Tags"):
            gr.Markdown("### Browse Images by Tag")

            with gr.Row():
                category_select = gr.Dropdown(
                    choices=list(TAG_CATEGORIES.keys()),
                    value="subject",
                    label="Category"
                )
                tag_select = gr.Dropdown(
                    choices=TAG_CATEGORIES["subject"],
                    value="people",
                    label="Tag"
                )

            with gr.Row():
                min_score = gr.Slider(
                    minimum=0.1, maximum=0.5, step=0.05, value=0.2,
                    label="Minimum Confidence"
                )
                browse_count = gr.Slider(
                    minimum=10, maximum=100, step=10, value=25,
                    label="Number of Images"
                )

            browse_btn = gr.Button("Browse Tag", variant="primary")
            browse_status = gr.Markdown()

            tag_gallery = gr.Gallery(
                label="Images with Tag",
                columns=5,
                rows=3,
                height="auto",
                object_fit="cover"
            )

        with gr.Tab("Tag Statistics"):
            gr.Markdown("### Tag Distribution")
            gr.Markdown("*Shows how many images have each tag.*")

            refresh_stats_btn = gr.Button("Load Statistics", variant="primary")

            stats_output = gr.Dataframe(
                headers=["Tag", "Category", "Count", "Avg Score"],
                label="Tag Statistics",
                interactive=False
            )

    def get_tag_status():
        """Get tag generation statistics."""
        try:
            tag_db_path = state.config.tag_database_path
            if not tag_db_path.exists():
                stats = state.get_index_stats()
                total = stats.get("total_images", 0)
                return 0, total, "0%"

            import json
            with open(tag_db_path, 'r') as f:
                tag_db = json.load(f)

            tagged = len(tag_db)
            stats = state.get_index_stats()
            total = stats.get("total_images", 0)
            untagged = max(0, total - tagged)
            pct = f"{tagged/total*100:.1f}%" if total > 0 else "0%"

            return tagged, untagged, pct

        except Exception as e:
            return 0, 0, f"Error: {e}"

    def generate_tags(force, threshold):
        """Generate tags for the library."""
        try:
            # Check if tag_generator exists
            try:
                from tag_generator import TagGenerator, find_images
            except ImportError:
                yield "tag_generator.py not found. Please ensure it exists."
                return

            source = Path(state.config.photo_source)
            if not source.exists():
                yield f"Photo source not found: {source}"
                return

            # Get images to tag
            images = find_images(source)
            total = len(images)

            yield f"Found {total} images to tag...\n"

            # Initialize generator
            gen = TagGenerator()

            progress_log = [f"Starting tag generation for {total} images..."]
            tagged = 0

            # Tag images
            for i, path in enumerate(images):
                try:
                    if not force and path in gen.tag_db.db:
                        continue

                    from photo_search import load_image
                    img, _ = load_image(path)
                    if img is None:
                        continue

                    tags = gen.tag_image(img, threshold=threshold)
                    gen.tag_db.add(path, tags)
                    tagged += 1

                    if i % 50 == 0:
                        gen.tag_db.save()
                        progress_log.append(f"Processed {i}/{total} ({tagged} tagged)")
                        if len(progress_log) > 15:
                            progress_log = progress_log[-15:]
                        yield "\n".join(progress_log)

                except Exception as e:
                    continue

            gen.tag_db.save()
            yield "\n".join(progress_log) + f"\n\n**Complete!** Tagged {tagged} images."

        except Exception as e:
            yield f"Error: {e}"

    def update_tags_for_category(category):
        """Update tag dropdown based on selected category."""
        tags = TAG_CATEGORIES.get(category, [])
        return gr.Dropdown(choices=tags, value=tags[0] if tags else None)

    def browse_tag(category, tag, min_conf, count):
        """Browse images with a specific tag."""
        try:
            tag_db_path = state.config.tag_database_path
            if not tag_db_path.exists():
                return [], "No tag database found. Generate tags first."

            import json
            with open(tag_db_path, 'r') as f:
                tag_db = json.load(f)

            # Find images with this tag
            matching = []
            for path_str, data in tag_db.items():
                if "scores" in data and tag in data["scores"]:
                    score = data["scores"][tag]
                    if score >= min_conf:
                        matching.append((Path(path_str), score))

            # Sort by score
            matching.sort(key=lambda x: x[1], reverse=True)
            matching = matching[:int(count)]

            if not matching:
                return [], f"No images found with tag '{tag}' (min confidence: {min_conf})"

            # Load images for gallery
            from photo_search import load_image
            gallery_items = []
            for path, score in matching:
                try:
                    img, _ = load_image(path)
                    if img:
                        img.thumbnail((400, 400))
                        gallery_items.append((img, f"[{score:.2f}] {path.name}"))
                except Exception:
                    continue

            return gallery_items, f"Found **{len(matching)}** images with tag '{tag}'"

        except Exception as e:
            return [], f"Error: {e}"

    def get_tag_statistics():
        """Get statistics for all tags."""
        try:
            tag_db_path = state.config.tag_database_path
            if not tag_db_path.exists():
                return []

            import json
            with open(tag_db_path, 'r') as f:
                tag_db = json.load(f)

            # Count tags
            tag_counts = {}
            tag_scores = {}

            for data in tag_db.values():
                if "scores" in data:
                    for tag, score in data["scores"].items():
                        if tag not in tag_counts:
                            tag_counts[tag] = 0
                            tag_scores[tag] = []
                        tag_counts[tag] += 1
                        tag_scores[tag].append(score)

            # Build table
            rows = []
            for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True):
                # Find category
                cat = "other"
                for category, tags in TAG_CATEGORIES.items():
                    if tag in tags:
                        cat = category
                        break

                avg_score = sum(tag_scores[tag]) / len(tag_scores[tag])
                rows.append([tag, cat, count, f"{avg_score:.3f}"])

            return rows

        except Exception as e:
            return [[f"Error: {e}", "", "", ""]]

    # Wire up event handlers
    refresh_tag_status_btn.click(
        get_tag_status,
        outputs=[tagged_count, untagged_count, coverage_pct]
    )

    generate_btn.click(
        generate_tags,
        inputs=[force_retag, tag_threshold],
        outputs=[tag_progress]
    )

    category_select.change(
        update_tags_for_category,
        inputs=[category_select],
        outputs=[tag_select]
    )

    browse_btn.click(
        browse_tag,
        inputs=[category_select, tag_select, min_score, browse_count],
        outputs=[tag_gallery, browse_status]
    )

    refresh_stats_btn.click(
        get_tag_statistics,
        outputs=[stats_output]
    )

    return {
        "tagged_count": tagged_count,
        "tag_gallery": tag_gallery,
        "generate_btn": generate_btn,
    }
