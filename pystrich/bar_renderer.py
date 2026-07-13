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
from typing import TYPE_CHECKING, Any

from pystrich.colour import RGBA, resolve_pil_palette
from pystrich.eps import bars_to_eps
from pystrich.fonts import get_font
from pystrich.marks import BarLayout, iter_barcode_marks
from pystrich.svg import bars_to_svg

if TYPE_CHECKING:
    from pystrich._pillow import PILImage


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
        self.image_width = 0
        self.image_height = 0

    @abstractmethod
    def _bar_layout(self, bar_width: int) -> BarLayout:
        """Return the pixel-precise layout used by all output formats."""

    def get_pilimage(
        self,
        bar_width: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> PILImage:
        """Render the symbol as a PIL image."""
        from pystrich._pillow import Image, ImageDraw, ImageFont

        mode, dark_fill, light_fill = resolve_pil_palette(dark_hex, light_hex)

        layout = self._bar_layout(bar_width)
        self.image_width = (
            layout.quiet_left + len(layout.heights) * layout.bar_width + layout.quiet_right
        )
        self.image_height = layout.quiet_top + max(layout.heights, default=0) + layout.quiet_bottom

        img = Image.new(mode, (self.image_width, self.image_height), light_fill)
        draw = ImageDraw.Draw(img)

        for mx, my, mw, mh in iter_barcode_marks(layout):
            draw.rectangle(
                (mx, my, mx + mw - 1, my + mh - 1),
                fill=dark_fill,
            )

        ttf_font = self.options.get("ttf_font")
        for label in layout.labels:
            font: ImageFont.ImageFont | ImageFont.FreeTypeFont
            if ttf_font:
                font = ImageFont.truetype(ttf_font, label.font_size)
            else:
                font = get_font("courR", label.font_size)
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
        return bars_to_svg(self._bar_layout(bar_width), dark_hex=dark_hex, light_hex=light_hex)

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
        return bars_to_eps(self._bar_layout(bar_width), dark_hex=dark_hex, light_hex=light_hex)

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
