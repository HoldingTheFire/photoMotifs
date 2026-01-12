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


# =============================================================================
# THEME CUSTOMIZATION
# =============================================================================
# Modify these values to change the look and feel of the UI.

# Primary accent color (buttons, highlights, links)
PRIMARY_COLOR = "#4CAF50"  # Green - change to your preferred color

# Font family for the UI
FONT_FAMILY = "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"

# Create custom theme
CUSTOM_THEME = gr.themes.Soft(
    # Primary colors
    primary_hue=gr.themes.colors.green,  # Options: red, orange, yellow, green, cyan, blue, purple, pink, gray
    secondary_hue=gr.themes.colors.gray,
    neutral_hue=gr.themes.colors.gray,

    # Font settings
    font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "monospace"],
).set(
    # Fine-tune specific elements
    button_primary_background_fill=PRIMARY_COLOR,
    button_primary_background_fill_hover="#45a049",
    block_title_text_weight="600",
    block_label_text_size="sm",
)

# Custom CSS for additional styling
CUSTOM_CSS = f"""
/* Gallery styling */
.gallery-item {{ cursor: pointer; }}
.selected-image {{ border: 3px solid {PRIMARY_COLOR}; }}

/* Score badge on results */
.score-badge {{
    background: {PRIMARY_COLOR};
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
}}

/* Status bar at bottom */
.status-bar {{
    background: #f0f0f0;
    padding: 8px 12px;
    border-radius: 4px;
    margin-top: 10px;
}}

/* Optional: Custom header styling */
h1 {{
    font-family: {FONT_FAMILY};
    color: #333;
}}

/* Optional: Make buttons more prominent */
.primary {{
    font-weight: 600 !important;
}}
"""


def create_app() -> gr.Blocks:
    """Create the main Gradio application."""

    config = PhotoMotifsConfig.load()
    state = AppState(config)

    with gr.Blocks(
        title="PhotoMotifs - Semantic Photo Search",
        theme=CUSTOM_THEME,
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
