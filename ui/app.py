"""
PhotoMotifs Gradio Web UI

Main application that combines all tab components into a unified interface.
"""

import os
# Fix OpenMP conflict between numpy/opencv/torch
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gradio as gr
from ui.config import PhotoMotifsConfig
from ui.state import AppState
from ui.components.settings_tab import create_settings_tab
from ui.components.search_tab import create_search_tab
from ui.components.indexing_tab import create_indexing_tab
from ui.components.tags_tab import create_tags_tab


# Custom CSS for better styling
CUSTOM_CSS = """
.gallery-item { cursor: pointer; }
.selected-image { border: 3px solid #4CAF50; }
.score-badge {
    background: #4CAF50;
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
}
.status-bar {
    background: #f0f0f0;
    padding: 8px 12px;
    border-radius: 4px;
    margin-top: 10px;
}
"""


def create_app() -> gr.Blocks:
    """Create the main Gradio application."""

    config = PhotoMotifsConfig.load()
    state = AppState(config)

    with gr.Blocks(
        title="PhotoMotifs - Semantic Photo Search",
        theme=gr.themes.Soft(),
        css=CUSTOM_CSS
    ) as app:

        # Header
        gr.Markdown("# PhotoMotifs")
        gr.Markdown("Search your photo library using natural language descriptions powered by CLIP.")

        with gr.Tabs() as tabs:
            with gr.Tab("Search", id="search"):
                search_components = create_search_tab(state)

            with gr.Tab("Indexing", id="indexing"):
                indexing_components = create_indexing_tab(state)

            with gr.Tab("Tags", id="tags"):
                tags_components = create_tags_tab(state)

            with gr.Tab("Settings", id="settings"):
                settings_components = create_settings_tab(state)

        # Status bar
        with gr.Row(elem_classes=["status-bar"]):
            gr.Markdown(
                f"**Photo Source:** {config.photo_source} | "
                f"**Model:** {config.model_name}"
            )

        # Load initial status on app start
        def on_load():
            """Initialize state on app load."""
            try:
                stats = state.get_index_stats()
                return (
                    stats.get("total_images", 0),
                    stats.get("cached_embeddings", 0),
                    stats.get("last_indexed", "Never")
                )
            except Exception:
                return 0, 0, "Error"

        # Connect the load event to indexing tab status
        app.load(
            on_load,
            outputs=[
                indexing_components["total"],
                indexing_components["cached"],
            ]
        )

    return app


def main():
    """Run the Gradio app."""
    import argparse

    parser = argparse.ArgumentParser(description="PhotoMotifs Web UI")
    parser.add_argument("--port", type=int, default=7860, help="Port to run on")
    parser.add_argument("--share", action="store_true", help="Create public link")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser")
    args = parser.parse_args()

    app = create_app()

    print("\n" + "="*60)
    print("PhotoMotifs Web UI")
    print("="*60)
    print(f"Starting server on http://localhost:{args.port}")
    print("Press Ctrl+C to stop")
    print("="*60 + "\n")

    app.launch(
        server_port=args.port,
        share=args.share,
        inbrowser=not args.no_browser
    )


if __name__ == "__main__":
    main()
