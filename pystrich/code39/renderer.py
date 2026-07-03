"""Rendering code for code39 barcode"""

from __future__ import annotations

import logging

from pystrich._vector_text import make_text_label
from pystrich.bar_renderer import Bar1DRenderer
from pystrich.marks import BarLayout, TextLabel
from pystrich.types import BarcodeRenderOptions

log = logging.getLogger("code39")

# Code 39 (MIL-STD-1189B) requires a quiet zone of at least 10 narrow-bar
# widths on each side of the symbol.
DEFAULT_QUIET_ZONE_MODULES = 10

DEFAULT_IMAGE_HEIGHT_PX = 120

FONT_SIZES = {1: 8, 2: 14, 3: 18, 4: 24}


class Code39Renderer(Bar1DRenderer):
    """Rendering class for code39 - given the bars and the original
    text, it will render an image of the barcode, including edge
    zones and text."""

    options: BarcodeRenderOptions
    bars: str
    text: str

    def __init__(
        self,
        bars: str,
        text: str,
        options: BarcodeRenderOptions | None = None,
    ) -> None:
        """See :class:`pystrich.types.BarcodeRenderOptions` for accepted keys."""
        super().__init__(options)
        self.bars = bars
        self.text = text

    def _label_metrics(self, bar_width: int) -> tuple[int, int]:
        """Return ``(fontsize_px, symbol_top_px)`` for the current options."""
        if not self.options.get("show_label", True):
            return 0, 0
        default_fontsize = FONT_SIZES.get(bar_width, 24)
        fontsize = self.options.get("ttf_fontsize", default_fontsize)
        quiet_modules = self.options.get("quiet_width_multiplier", DEFAULT_QUIET_ZONE_MODULES)
        symbol_top = bar_width * quiet_modules // 2
        return fontsize, symbol_top

    def _bar_layout(self, bar_width: int) -> BarLayout:
        """Pixel-precise layout shared by PNG, SVG and EPS rendering."""
        fontsize, symbol_top = self._label_metrics(bar_width)
        quiet_modules = self.options.get("quiet_width_multiplier", DEFAULT_QUIET_ZONE_MODULES)
        image_height = self.options.get("height") or DEFAULT_IMAGE_HEIGHT_PX
        label_border = self.options.get("label_border", 0)
        bottom_border = self.options.get("bottom_border", 0)
        bar_pixel_height = image_height - label_border - fontsize - symbol_top
        quiet_width = bar_width * quiet_modules
        heights = [bar_pixel_height if c == "1" else 0 for c in self.bars]
        labels: tuple[TextLabel, ...] = ()
        if fontsize > 0:
            image_width = (2 * quiet_width) + len(self.bars) * bar_width
            labels = (
                make_text_label(
                    self.text,
                    image_width / 2,
                    symbol_top + bar_pixel_height + label_border,
                    fontsize,
                    anchor="middle",
                ),
            )
        return BarLayout(
            heights=heights,
            bar_width=bar_width,
            quiet_left=quiet_width,
            quiet_right=quiet_width,
            quiet_top=symbol_top,
            quiet_bottom=label_border + fontsize + bottom_border,
            labels=labels,
        )
