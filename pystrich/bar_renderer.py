"""Shared base class for 1D barcode renderers.

The 1D formats (Code 39, Code 128, EAN-13) all produce a flat list of bar
heights driven by a :class:`pystrich.marks.BarLayout`. Once the layout is
known, the rendering logic for PNG/SVG/EPS is identical across formats.
This module captures that shared logic; format-specific subclasses only
implement :meth:`Bar1DRenderer._bar_layout`, and every output format (PNG,
SVG and EPS) is driven from the :class:`~pystrich.marks.BarLayout` it returns.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Mapping
from io import BytesIO
from math import ceil
from typing import TYPE_CHECKING, Any

from pystrich._vector_text import fit_labels
from pystrich.colour import RGBA, resolve_pil_palette
from pystrich.eps import bars_to_eps
from pystrich.fonts import get_font
from pystrich.limits import check_cell_size, check_image_pixels, require_valid_int
from pystrich.marks import BarLayout, SymbolMarks, iter_barcode_marks
from pystrich.svg import bars_to_svg

if TYPE_CHECKING:
    from pystrich._pillow import PILImage

# Render-option keys typed as non-negative int across the 1D formats. They are
# checked when the options reach the renderer. Zero is a valid sentinel for several.
_INT_OPTIONS = (
    "ttf_fontsize",
    "height",
    "label_border",
    "bottom_border",
    "quiet_width_multiplier",
    "bearer_width",
)


class Bar1DRenderer(ABC):
    """Common rendering surface for 1D barcode formats.

    Subclasses implement only :meth:`_bar_layout`, the pixel-precise layout
    that drives every output format. The bar geometry and the human-readable
    labels it carries are rendered identically across formats.
    """

    options: Mapping[str, Any]
    image_width: int
    image_height: int

    def __init__(self, options: Mapping[str, Any] | None = None) -> None:
        self.options = options or {}
        for key in _INT_OPTIONS:
            if key in self.options:
                require_valid_int(self.options[key], name=key, min_value=0)
        self.image_width = 0
        self.image_height = 0

    @abstractmethod
    def _bar_layout(self, bar_width: int) -> BarLayout:
        """Return the pixel-precise layout used by all output formats."""

    def _layout(self, bar_width: int) -> BarLayout:
        """The layout every output format renders: subclass layout, labels fitted."""
        margin = self.options.get("bottom_border", 0)
        return fit_labels(self._bar_layout(bar_width), margin=margin)

    def get_pilimage(
        self,
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> PILImage:
        """Render the symbol as a PIL image."""
        check_cell_size(bar_width, name="bar width")

        layout = self._layout(bar_width)
        check_image_pixels(layout.width, layout.height, name="bar width")

        from pystrich._pillow import Image, ImageDraw, ImageFont

        mode, dark_fill, light_fill = resolve_pil_palette(dark_hex, light_hex)

        self.image_width = layout.width
        self.image_height = layout.height

        ttf_font = self.options.get("ttf_font")
        fonts: list[ImageFont.ImageFont | ImageFont.FreeTypeFont] = []
        for label in layout.labels:
            if ttf_font:
                truetype = ImageFont.truetype(ttf_font, label.font_size)
                # The layout reserves descent space for the bundled font's
                # metrics; a substituted TTF may descend further.
                ascent, descent = truetype.getmetrics()
                self.image_height = max(self.image_height, ceil(label.y + ascent + descent))
                fonts.append(truetype)
            else:
                fonts.append(get_font("courR", label.font_size))

        img = Image.new(mode, (self.image_width, self.image_height), light_fill)
        draw = ImageDraw.Draw(img)

        for mx, my, mw, mh in iter_barcode_marks(layout):
            draw.rectangle(
                (mx, my, mx + mw - 1, my + mh - 1),
                fill=dark_fill,
            )

        for label, font in zip(layout.labels, fonts, strict=True):
            x = label.x
            if label.anchor == "middle":
                x -= font.getlength(label.text) / 2
            elif label.anchor == "end":
                x -= font.getlength(label.text)
            draw.text((x, int(label.y)), label.text, font=font, fill=dark_fill)

        return img

    def write_file(
        self,
        filename: str | os.PathLike[str],
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the symbol as a PNG file."""
        self.get_pilimage(bar_width, dark_hex=dark_hex, light_hex=light_hex).save(filename, "PNG")

    def get_imagedata(
        self,
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> bytes:
        """Render the symbol and return PNG bytes."""
        buffer = BytesIO()
        self.get_pilimage(bar_width, dark_hex=dark_hex, light_hex=light_hex).save(buffer, "PNG")
        return buffer.getvalue()

    def get_svg(
        self,
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Return the symbol as an SVG string."""
        check_cell_size(bar_width, name="bar width")
        return bars_to_svg(self._layout(bar_width), dark_hex=dark_hex, light_hex=light_hex)

    def write_svg_file(
        self,
        filename: str | os.PathLike[str],
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the symbol as an SVG file."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.get_svg(bar_width, dark_hex=dark_hex, light_hex=light_hex))

    def get_eps(
        self,
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Return the symbol as an EPS string."""
        check_cell_size(bar_width, name="bar width")
        return bars_to_eps(self._layout(bar_width), dark_hex=dark_hex, light_hex=light_hex)

    def write_eps_file(
        self,
        filename: str | os.PathLike[str],
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the symbol as an EPS file."""
        with open(filename, "w", encoding="ascii") as f:
            f.write(self.get_eps(bar_width, dark_hex=dark_hex, light_hex=light_hex))

    def get_rect_marks(self) -> SymbolMarks:
        """Return the barcode's dark bars as a :class:`~pystrich.marks.SymbolMarks`.

        The extent is the canvas the other output formats draw at
        ``bar_width=1``. The label glyphs themselves are not marks; pass
        ``show_label=False`` (where the format supports it) to drop the
        label space too.

        :rtype: pystrich.marks.SymbolMarks

        .. versionadded:: 0.18
        """
        layout = self._layout(1)
        marks = tuple(iter_barcode_marks(layout))
        return SymbolMarks(marks, layout.width, layout.height)
