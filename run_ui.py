#!/usr/bin/env python
"""
PhotoMotifs Web UI Launcher

Launch the Gradio-based web interface for semantic photo search.

Usage:
    python run_ui.py                  # Launch on default port 7860
    python run_ui.py --port 8080      # Custom port
    python run_ui.py --no-browser     # Don't auto-open browser
    python run_ui.py --share          # Create public link (for sharing)
"""

import os
# Fix OpenMP conflict between numpy/opencv/torch
os.environ['KMP_DUPLICATE_LIB_OK'] = 'TRUE'

import sys
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    """Launch the PhotoMotifs web UI."""
    from ui.app import create_app
    import argparse

    parser = argparse.ArgumentParser(
        description="PhotoMotifs - Semantic Photo Search Web UI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_ui.py                    Launch on http://localhost:7860
    python run_ui.py --port 8080        Use port 8080
    python run_ui.py --no-browser       Don't auto-open browser
        """
    )
    parser.add_argument(
        "--port", type=int, default=7860,
        help="Port to run the server on (default: 7860)"
    )
    parser.add_argument(
        "--share", action="store_true",
        help="Create a public Gradio link for sharing"
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Don't automatically open browser"
    )

    args = parser.parse_args()

    print()
    print("=" * 60)
    print("  PhotoMotifs - Semantic Photo Search")
    print("=" * 60)
    print()
    print("  Starting web interface...")
    print(f"  URL: http://localhost:{args.port}")
    print()
    print("  Press Ctrl+C to stop the server")
    print("=" * 60)
    print()

    app = create_app()

    app.launch(
        server_port=args.port,
        share=args.share,
        inbrowser=not args.no_browser
    )


if __name__ == "__main__":
    main()
