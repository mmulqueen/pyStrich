"""Shared base class for 1D barcode renderers.

The 1D formats (Code 39, Code 128, EAN-13) all produce a flat list of bar
heights driven by a :class:`pystrich.marks.BarLayout`. Once the layout is
known, the rendering logic for PNG/SVG/EPS is identical across formats.
This module captures that shared logic; format-specific subclasses only
implement :meth:`Bar1DRenderer._bar_layout` and the PNG drawing path.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Mapping
from io import BytesIO
from typing import TYPE_CHECKING, Any

from pystrich.eps import bars_to_eps
from pystrich.marks import BarLayout
from pystrich.svg import bars_to_svg

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


class Bar1DRenderer(ABC):
    """Common rendering surface for 1D barcode formats.

    Subclasses must implement :meth:`_bar_layout` (the pixel-precise layout
    that drives every output format) and :meth:`get_pilimage` (the PNG
    drawing path, which adds format-specific label or digit rendering on
    top of the bar geometry).
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

    @abstractmethod
    def get_pilimage(self, bar_width: int) -> PILImage:
        """Render the symbol as a PIL image."""

    def write_file(
        self, filename: str | os.PathLike[str], bar_width: int
    ) -> None:
        """Save the symbol as a PNG file."""
        self.get_pilimage(bar_width).save(filename, "PNG")

    def get_imagedata(self, bar_width: int) -> bytes:
        """Render the symbol and return PNG bytes."""
        buffer = BytesIO()
        self.get_pilimage(bar_width).save(buffer, "PNG")
        return buffer.getvalue()

    def get_svg(self, bar_width: int) -> str:
        """Return the symbol as an SVG string."""
        return bars_to_svg(self._bar_layout(bar_width))

    def write_svg_file(
        self, filename: str | os.PathLike[str], bar_width: int
    ) -> None:
        """Save the symbol as an SVG file."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.get_svg(bar_width))

    def get_eps(self, bar_width: int) -> str:
        """Return the symbol as an EPS string."""
        return bars_to_eps(self._bar_layout(bar_width))

    def write_eps_file(
        self, filename: str | os.PathLike[str], bar_width: int
    ) -> None:
        """Save the symbol as an EPS file."""
        with open(filename, "w", encoding="ascii") as f:
            f.write(self.get_eps(bar_width))
