"""Rendering code for Interleaved 2 of 5 and ITF-14 barcodes."""

from __future__ import annotations

from math import ceil

from pystrich._vector_text import label_descent_y, make_text_label
from pystrich.bar_renderer import Bar1DRenderer
from pystrich.exceptions import PyStrichInvalidOption
from pystrich.marks import BarLayout, TextLabel
from pystrich.types import BarcodeRenderOptions

# Interleaved 2 of 5 requires a quiet zone of at least 10 narrow-bar widths on
# each side of the symbol.
DEFAULT_QUIET_ZONE_MODULES = 10

DEFAULT_IMAGE_HEIGHT_PX = 120

FONT_SIZES = {1: 8, 2: 14, 3: 18, 4: 24}


class ITFRenderOptions(BarcodeRenderOptions, total=False):
    """Optional render-time tweaks for Interleaved 2 of 5 / ITF-14 barcodes.

    Extends :class:`pystrich.types.BarcodeRenderOptions`. All keys are
    optional; omitted keys fall back to library defaults.
    """

    bearer_width: int
    """Thickness of the bearer bar's rules, in narrow-bar widths. ``0`` draws
    no bearer. Defaults to ``0`` for plain Interleaved 2 of 5 and to ``4`` for
    ITF-14."""


class ITFRenderer(Bar1DRenderer):
    """Render Interleaved 2 of 5 bars, optionally inside a bearer bar.

    A single renderer serves both plain Interleaved 2 of 5 and ITF-14; the
    ``bearer_width`` option (defaulted per encoder) selects whether the frame
    is drawn.
    """

    options: ITFRenderOptions
    digits: str
    bars: str

    def __init__(
        self,
        digits: str,
        bars: str,
        options: ITFRenderOptions | None = None,
    ) -> None:
        """See :class:`ITFRenderOptions` for accepted keys."""
        super().__init__(options)
        self.digits = digits
        self.bars = bars

    def _bar_layout(self, bar_width: int) -> BarLayout:
        """Pixel-precise layout shared by PNG, SVG and EPS rendering."""
        bearer_px = self.options.get("bearer_width", 0) * bar_width
        quiet_modules = self.options.get("quiet_width_multiplier", DEFAULT_QUIET_ZONE_MODULES)
        quiet_px = quiet_modules * bar_width

        if self.options.get("show_label", True):
            font_size = self.options.get("ttf_fontsize", FONT_SIZES.get(bar_width, 24))
        else:
            font_size = 0
        label_border = self.options.get("label_border", 0)
        bottom_border = self.options.get("bottom_border", 0)

        total_height = self.options.get("height") or DEFAULT_IMAGE_HEIGHT_PX
        bar_pixel_height = total_height - 2 * bearer_px - label_border - font_size - bottom_border
        if bar_pixel_height <= 0:
            raise PyStrichInvalidOption(
                f"height {total_height} is too small for the symbol at bar width {bar_width}"
            )

        heights = [bar_pixel_height if c == "1" else 0 for c in self.bars]
        quiet_left = bearer_px + quiet_px
        image_width = 2 * quiet_left + len(self.bars) * bar_width

        # The bearer frames the bars only (top rule, bars, bottom rule); the
        # label sits below the bottom rule, outside the frame.
        frame_bottom = bearer_px + bar_pixel_height + bearer_px
        labels: tuple[TextLabel, ...] = ()
        image_height = max(total_height, frame_bottom + bottom_border)
        if font_size:
            text_top = frame_bottom + label_border
            label = make_text_label(
                self.digits, image_width / 2, text_top, font_size, anchor="middle"
            )
            labels = (label,)
            # Grow the canvas so the label clears the font descent.
            image_height = max(image_height, ceil(label_descent_y(label)) + bottom_border)

        return BarLayout(
            heights=heights,
            bar_width=bar_width,
            quiet_left=quiet_left,
            quiet_right=quiet_left,
            quiet_top=bearer_px,
            quiet_bottom=image_height - bearer_px - bar_pixel_height,
            labels=labels,
            bearer_width=bearer_px,
        )
