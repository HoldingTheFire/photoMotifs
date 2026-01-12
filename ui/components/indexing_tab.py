"""
Indexing Tab - Embedding generation for PhotoMotifs.
"""

import gradio as gr
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.state import AppState


def create_indexing_tab(state: "AppState") -> dict:
    """Create the Indexing operations tab."""

    gr.Markdown("## Index Your Photo Library")
    gr.Markdown("""
    Build or update the CLIP embedding index for your photos.
    This enables semantic search but may take several minutes for large libraries.
    """)

    # Current status
    with gr.Group():
        gr.Markdown("### Current Index Status")
        with gr.Row():
            total_images = gr.Number(label="Total Images", interactive=False, value=0)
            cached_embeddings = gr.Number(label="Cached Embeddings", interactive=False, value=0)
            index_date = gr.Textbox(label="Last Indexed", interactive=False, value="Never")

        refresh_status_btn = gr.Button("Refresh Status", size="sm")

    # Indexing options
    with gr.Group():
        gr.Markdown("### Indexing Options")

        source_path = gr.Textbox(
            label="Source Directory",
            value=state.config.photo_source,
            info="Directory to index (uses config by default)"
        )

        with gr.Row():
            force_reindex = gr.Checkbox(
                label="Force Reindex",
                value=False,
                info="Recompute all embeddings (ignores cache)"
            )
            analog_only = gr.Checkbox(
                label="Analog Folder Only",
                value=False,
                info="Only reindex the Analog subfolder"
            )

    # Action buttons
    with gr.Row():
        index_btn = gr.Button("Start Indexing", variant="primary", size="lg")
        clear_cache_btn = gr.Button("Clear Cache")

    # Progress display
    with gr.Group():
        gr.Markdown("### Progress")
        progress_bar = gr.Slider(
            minimum=0, maximum=100, value=0,
            label="Progress",
            interactive=False
        )
        progress_text = gr.Textbox(
            label="Status",
            lines=8,
            interactive=False,
            value="Ready to index..."
        )

    def get_index_status():
        """Get current index statistics."""
        try:
            stats = state.get_index_stats()
            return (
                stats.get("total_images", 0),
                stats.get("cached_embeddings", 0),
                stats.get("last_indexed", "Never")
            )
        except Exception as e:
            return 0, 0, f"Error: {e}"

    def do_indexing(source, force, analog_only):
        """Run the indexing process with progress updates."""
        try:
            if analog_only:
                source = str(Path(source) / "Analog")

            source_path = Path(source)
            if not source_path.exists():
                yield 0, f"Source directory not found: {source_path}", 0, 0, "Never"
                return

            # Get searcher and run indexing with progress
            searcher = state.get_searcher()

            progress_log = []

            for current, total, message in searcher.index_images_with_progress(
                source_path, force_reindex=force
            ):
                progress_log.append(message)
                # Keep last 15 lines
                if len(progress_log) > 15:
                    progress_log = progress_log[-15:]

                progress_pct = (current / total * 100) if total > 0 else 0
                log_text = "\n".join(progress_log)

                yield progress_pct, log_text, total, current, "In progress..."

            # Final status
            stats = state.get_index_stats()
            yield (
                100,
                "\n".join(progress_log) + "\n\n**Indexing complete!**",
                stats.get("total_images", 0),
                stats.get("cached_embeddings", 0),
                stats.get("last_indexed", "Just now")
            )

        except Exception as e:
            yield 0, f"Error during indexing: {e}", 0, 0, "Failed"

    def clear_cache():
        """Clear the embeddings cache."""
        try:
            cache_path = state.config.embeddings_cache_path
            if cache_path.exists():
                cache_path.unlink()
                # Also clear the in-memory cache
                searcher = state.get_searcher()
                searcher.cache.cache = {}
                searcher.embeddings = None
                return "Cache cleared successfully. Run indexing to rebuild."
            return "No cache file found."
        except Exception as e:
            return f"Error clearing cache: {e}"

    # Wire up event handlers
    refresh_status_btn.click(
        get_index_status,
        outputs=[total_images, cached_embeddings, index_date]
    )

    index_btn.click(
        do_indexing,
        inputs=[source_path, force_reindex, analog_only],
        outputs=[progress_bar, progress_text, total_images, cached_embeddings, index_date]
    )

    clear_cache_btn.click(
        clear_cache,
        outputs=[progress_text]
    )

    return {
        "progress": progress_text,
        "total": total_images,
        "cached": cached_embeddings,
        "index_btn": index_btn,
    }
