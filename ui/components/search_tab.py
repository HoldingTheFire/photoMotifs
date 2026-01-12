"""
Search Tab - Main search interface for PhotoMotifs.
"""

import gradio as gr
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, List, Tuple, Optional
from PIL import Image

if TYPE_CHECKING:
    from ui.state import AppState


def create_search_tab(state: "AppState") -> dict:
    """Create the Search interface tab."""

    gr.Markdown("## Search Your Photo Library")
    gr.Markdown("Enter a natural language description to find matching photos.")

    with gr.Row():
        with gr.Column(scale=3):
            query_input = gr.Textbox(
                label="Search Query",
                placeholder="e.g., 'sunset landscape', 'portrait with bokeh', 'rusty metal'",
                lines=1
            )
        with gr.Column(scale=1):
            top_n = gr.Slider(
                minimum=5, maximum=100, step=5,
                value=state.config.default_top_n,
                label="Number of Results"
            )

    # Lightroom filters
    with gr.Accordion("Lightroom Filters", open=False):
        gr.Markdown("*Filter by Lightroom metadata (requires catalog connection)*")
        with gr.Row():
            min_rating = gr.Slider(
                minimum=0, maximum=5, step=1, value=0,
                label="Minimum Rating (stars)"
            )
            pick_filter = gr.Dropdown(
                choices=["Any", "Picked Only", "Rejected Only", "Unflagged Only"],
                value="Any",
                label="Pick Status"
            )

    # Tag filters
    with gr.Accordion("Tag Filters", open=False):
        gr.Markdown("*Filter by pre-computed semantic tags (requires tag generation)*")
        tag_filter = gr.CheckboxGroup(
            choices=[
                "people", "animals", "vehicles", "buildings", "nature", "water",
                "indoor", "outdoor", "urban", "rural",
                "portrait", "landscape_style", "macro", "action",
                "bright", "dark", "warm", "cool",
                "bokeh", "sharp", "black_white", "color"
            ],
            label="Required Tags (images must have ALL selected)"
        )

    with gr.Row():
        search_btn = gr.Button("Search", variant="primary", size="lg")
        clear_btn = gr.Button("Clear Results")

    # Status display
    search_status = gr.Markdown()

    # Results gallery
    gr.Markdown("### Results")
    results_gallery = gr.Gallery(
        label="Search Results",
        columns=5,
        rows=3,
        height="auto",
        object_fit="cover",
        show_label=False,
        allow_preview=True
    )

    # Selected image details
    with gr.Row():
        with gr.Column(scale=2):
            selected_image = gr.Image(
                label="Selected Image",
                height=400,
                show_label=True
            )
        with gr.Column(scale=1):
            image_info = gr.Markdown("*Click an image to see details*")
            image_path = gr.Textbox(
                label="File Path",
                interactive=False
            )
            with gr.Row():
                open_folder_btn = gr.Button("Open Folder")
                copy_one_btn = gr.Button("Copy to Working")

    # Batch operations
    with gr.Group():
        gr.Markdown("### Batch Operations")
        with gr.Row():
            copy_all_btn = gr.Button("Copy All Results to Working Folder")
            generate_report_btn = gr.Button("Generate HTML Report")

    operation_status = gr.Markdown()

    # State for tracking results
    results_state = gr.State([])

    def do_search(query, n, min_star, pick, tags):
        """Execute search and return gallery images."""
        if not query.strip():
            return [], [], "Please enter a search query."

        try:
            # Get searcher and ensure indexed
            searcher = state.get_searcher()

            # Check if we need to index first
            if searcher.embeddings is None:
                source = Path(state.config.photo_source)
                if not source.exists():
                    return [], [], f"Photo source not found: {source}"
                searcher.index_images(source)

            # Execute search
            results = searcher.search(query, int(n))

            if not results:
                return [], [], "No results found."

            # Filter by Lightroom metadata if configured
            if state.lr_catalog and (min_star > 0 or pick != "Any"):
                filtered_results = []
                for r in results:
                    try:
                        img_meta = state.lr_catalog.get_image(r.path)
                        if img_meta:
                            if min_star > 0 and img_meta.rating < min_star:
                                continue
                            if pick == "Picked Only" and img_meta.pick != 1:
                                continue
                            if pick == "Rejected Only" and img_meta.pick != -1:
                                continue
                            if pick == "Unflagged Only" and img_meta.pick != 0:
                                continue
                        filtered_results.append(r)
                    except Exception:
                        filtered_results.append(r)
                results = filtered_results

            # Create gallery items
            gallery_items = []
            from photo_search import load_image
            for r in results:
                try:
                    img, _ = load_image(r.path)
                    if img:
                        img.thumbnail((400, 400))
                        caption = f"[{r.score:.3f}] {r.path.name}"
                        gallery_items.append((img, caption))
                except Exception:
                    continue

            status = f"Found **{len(results)}** results for '{query}'"
            return gallery_items, results, status

        except Exception as e:
            return [], [], f"Error: {str(e)}"

    def on_gallery_select(evt: gr.SelectData, results):
        """Handle gallery image selection."""
        if not results or evt.index >= len(results):
            return None, "*No image selected*", ""

        result = results[evt.index]
        from photo_search import load_image

        try:
            img, source_type = load_image(result.path)

            info = f"""
**Score:** {result.score:.3f}
**Source:** {source_type}
**Size:** {img.size if img else 'N/A'}
**Folder:** {result.path.parent.name}
**Full Path:** `{result.path}`
"""
            return img, info, str(result.path)
        except Exception as e:
            return None, f"Error loading image: {e}", str(result.path)

    def open_folder(path_str):
        """Open the folder containing the image."""
        if not path_str:
            return "No image selected"
        try:
            import subprocess
            path = Path(path_str)
            if path.exists():
                subprocess.run(['explorer', '/select,', str(path)], check=False)
                return f"Opened folder: {path.parent}"
            return f"Path not found: {path}"
        except Exception as e:
            return f"Error: {e}"

    def copy_single(path_str):
        """Copy single image to working folder."""
        if not path_str:
            return "No image selected"
        try:
            src = Path(path_str)
            dest_dir = Path(state.config.working_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)
            dest = dest_dir / src.name
            shutil.copy2(src, dest)
            return f"Copied to: {dest}"
        except Exception as e:
            return f"Error: {e}"

    def copy_all_results(results):
        """Copy all results to working folder."""
        if not results:
            return "No results to copy"

        try:
            dest_dir = Path(state.config.working_dir)
            dest_dir.mkdir(parents=True, exist_ok=True)

            copied = 0
            for r in results:
                try:
                    dest = dest_dir / r.path.name
                    # Handle duplicates
                    if dest.exists():
                        stem = r.path.stem
                        suffix = r.path.suffix
                        counter = 1
                        while dest.exists():
                            dest = dest_dir / f"{stem}_{counter}{suffix}"
                            counter += 1
                    shutil.copy2(r.path, dest)
                    copied += 1
                except Exception:
                    continue

            return f"**Copied {copied} files** to {dest_dir}"
        except Exception as e:
            return f"Error: {e}"

    def generate_report(results, query):
        """Generate HTML report for results."""
        if not results:
            return "No results for report"

        try:
            from photo_search import generate_html_report
            output_dir = Path(state.config.results_dir)
            report_path = generate_html_report(results, query or "search", output_dir)
            return f"**Report saved:** {report_path}"
        except Exception as e:
            return f"Error: {e}"

    def clear_results():
        """Clear all results."""
        return [], [], "", None, "*Click an image to see details*", ""

    # Wire up event handlers
    search_btn.click(
        do_search,
        inputs=[query_input, top_n, min_rating, pick_filter, tag_filter],
        outputs=[results_gallery, results_state, search_status]
    )

    # Also trigger search on Enter key
    query_input.submit(
        do_search,
        inputs=[query_input, top_n, min_rating, pick_filter, tag_filter],
        outputs=[results_gallery, results_state, search_status]
    )

    results_gallery.select(
        on_gallery_select,
        inputs=[results_state],
        outputs=[selected_image, image_info, image_path]
    )

    open_folder_btn.click(
        open_folder,
        inputs=[image_path],
        outputs=[operation_status]
    )

    copy_one_btn.click(
        copy_single,
        inputs=[image_path],
        outputs=[operation_status]
    )

    copy_all_btn.click(
        copy_all_results,
        inputs=[results_state],
        outputs=[operation_status]
    )

    generate_report_btn.click(
        generate_report,
        inputs=[results_state, query_input],
        outputs=[operation_status]
    )

    clear_btn.click(
        clear_results,
        outputs=[results_gallery, results_state, search_status,
                 selected_image, image_info, image_path]
    )

    return {
        "query": query_input,
        "gallery": results_gallery,
        "results_state": results_state,
        "search_btn": search_btn,
    }
