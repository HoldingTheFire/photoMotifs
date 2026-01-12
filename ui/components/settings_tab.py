"""
Settings Tab - Path configuration for PhotoMotifs.
"""

import gradio as gr
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.state import AppState


def create_settings_tab(state: "AppState") -> dict:
    """Create the Settings configuration tab."""

    config = state.config

    gr.Markdown("## Path Configuration")
    gr.Markdown("Configure paths to your photo library and Lightroom catalog.")

    with gr.Group():
        gr.Markdown("### Photo Library")
        photo_source = gr.Textbox(
            label="Photo Source Directory",
            value=config.photo_source,
            info="Root directory containing your photos (READ-ONLY - never modified)"
        )

        with gr.Row():
            working_dir = gr.Textbox(
                label="Working Directory",
                value=config.working_dir,
                info="Where copied files are saved"
            )
            results_dir = gr.Textbox(
                label="Results Directory",
                value=config.results_dir,
                info="Where HTML reports are saved"
            )

        cache_dir = gr.Textbox(
            label="Cache Directory",
            value=config.cache_dir,
            info="Where embeddings and tags are cached"
        )

    with gr.Group():
        gr.Markdown("### Lightroom Integration (Optional)")
        gr.Markdown("*Connect to Lightroom to use edited previews and filter by metadata.*")

        lr_catalog = gr.Textbox(
            label="Lightroom Catalog (.lrcat)",
            value=config.lr_catalog_path,
            info="Path to your Lightroom catalog file"
        )

        lr_previews = gr.Textbox(
            label="Lightroom Previews Directory (.lrdata)",
            value=config.lr_previews_dir,
            info="Path to your Lightroom previews folder"
        )

        with gr.Accordion("Path Mappings (Advanced)", open=False):
            gr.Markdown("Map catalog drive letters to actual filesystem paths if they differ.")
            with gr.Row():
                # Get first mapping if exists
                first_from = list(config.lr_path_mappings.keys())[0] if config.lr_path_mappings else ""
                first_to = list(config.lr_path_mappings.values())[0] if config.lr_path_mappings else ""

                lr_path_from = gr.Textbox(
                    label="Catalog Path Prefix",
                    value=first_from,
                    placeholder="e.g., M:/Photos/"
                )
                lr_path_to = gr.Textbox(
                    label="Actual Path Prefix",
                    value=first_to,
                    placeholder="e.g., Z:/Photos/"
                )

    with gr.Group():
        gr.Markdown("### Defaults")
        with gr.Row():
            default_top_n = gr.Number(
                label="Default Results Count",
                value=config.default_top_n,
                precision=0,
                minimum=5,
                maximum=200
            )
            thumbnail_size = gr.Number(
                label="Thumbnail Size (px)",
                value=config.thumbnail_size,
                precision=0,
                minimum=100,
                maximum=500
            )

    with gr.Row():
        save_btn = gr.Button("Save Settings", variant="primary")
        validate_btn = gr.Button("Validate Paths")
        reset_btn = gr.Button("Reset to Defaults")

    validation_output = gr.Markdown()

    def save_settings(photo_src, work_dir, res_dir, cache, lr_cat, lr_prev,
                      path_from, path_to, top_n, thumb_size):
        """Save settings to config file."""
        config.photo_source = photo_src
        config.working_dir = work_dir
        config.results_dir = res_dir
        config.cache_dir = cache
        config.lr_catalog_path = lr_cat
        config.lr_previews_dir = lr_prev

        if path_from and path_to:
            config.lr_path_mappings = {
                path_from: path_to,
                path_from.replace("/", "\\"): path_to.replace("/", "\\"),
            }

        config.default_top_n = int(top_n)
        config.thumbnail_size = int(thumb_size)

        config.save()
        config.ensure_directories()
        state.reload_config()

        return "**Settings saved successfully!**"

    def validate_paths(photo_src, work_dir, res_dir, cache, lr_cat, lr_prev):
        """Validate that configured paths exist."""
        results = ["### Path Validation Results\n"]

        paths = [
            ("Photo Source", photo_src, True),
            ("Working Dir", work_dir, False),
            ("Results Dir", res_dir, False),
            ("Cache Dir", cache, False),
            ("LR Catalog", lr_cat, False),
            ("LR Previews", lr_prev, False),
        ]

        for name, path, required in paths:
            if not path:
                if required:
                    results.append(f"- **{name}**: Missing (required)")
                else:
                    results.append(f"- **{name}**: Not configured (optional)")
                continue

            p = Path(path)
            if p.exists():
                if p.is_file():
                    size_mb = p.stat().st_size / (1024 * 1024)
                    results.append(f"- **{name}**: OK ({size_mb:.1f} MB)")
                else:
                    results.append(f"- **{name}**: OK (directory)")
            else:
                status = "NOT FOUND" if required else "NOT FOUND (will be created)"
                results.append(f"- **{name}**: {status}")

        return "\n".join(results)

    def reset_defaults():
        """Reset all settings to defaults."""
        from ui.config import PhotoMotifsConfig
        default = PhotoMotifsConfig()
        return (
            default.photo_source,
            default.working_dir,
            default.results_dir,
            default.cache_dir,
            default.lr_catalog_path,
            default.lr_previews_dir,
            list(default.lr_path_mappings.keys())[0] if default.lr_path_mappings else "",
            list(default.lr_path_mappings.values())[0] if default.lr_path_mappings else "",
            default.default_top_n,
            default.thumbnail_size,
            "**Settings reset to defaults.** Click Save to apply."
        )

    # Wire up event handlers
    save_btn.click(
        save_settings,
        inputs=[photo_source, working_dir, results_dir, cache_dir,
                lr_catalog, lr_previews, lr_path_from, lr_path_to,
                default_top_n, thumbnail_size],
        outputs=[validation_output]
    )

    validate_btn.click(
        validate_paths,
        inputs=[photo_source, working_dir, results_dir, cache_dir,
                lr_catalog, lr_previews],
        outputs=[validation_output]
    )

    reset_btn.click(
        reset_defaults,
        outputs=[photo_source, working_dir, results_dir, cache_dir,
                 lr_catalog, lr_previews, lr_path_from, lr_path_to,
                 default_top_n, thumbnail_size, validation_output]
    )

    return {
        "photo_source": photo_source,
        "working_dir": working_dir,
        "results_dir": results_dir,
        "save_btn": save_btn,
    }
