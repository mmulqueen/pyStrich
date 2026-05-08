"""Shared typing helpers for pyStrich encoders and renderers."""

from __future__ import annotations

from typing import TypedDict


class BarcodeRenderOptions(TypedDict, total=False):
    """Optional render-time tweaks for label-bearing 1D barcodes.

    Currently used by :class:`pystrich.code128.Code128Encoder` and
    :class:`pystrich.code39.Code39Encoder`. All keys are optional;
    omitted keys fall back to library defaults.
    """

    show_label: bool
    """Whether to render the human-readable label underneath the bars.
    Defaults to ``True``; set to ``False`` to suppress it."""

    ttf_font: str
    """Absolute path to a TrueType font file used for the label in PNG
    output. Defaults to a bundled bitmap font if unset. SVG and EPS
    output always render the label using the bundled Courier Prime
    glyph paths and ignore this option."""

    ttf_fontsize: int
    """Font size in points (PNG output only — SVG/EPS use the bundled
    Courier Prime glyph paths)."""

    height: int
    """Total image height in pixels. Defaults to roughly a third of the
    image width for Code 128, and to ``120`` for Code 39."""

    label_border: int
    """Pixels of vertical space between the bars and the label."""

    bottom_border: int
    """Pixels of vertical space between the label and the bottom edge."""
