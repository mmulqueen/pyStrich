"""Shared base class for 1D barcode encoders.

Encoder subclasses (:class:`pystrich.code39.Code39Encoder`,
:class:`pystrich.code128.Code128Encoder`,
:class:`pystrich.ean13.EAN13Encoder`) translate their input into a bar
string and supply :meth:`Bar1DEncoder.init_renderer` that constructs the
matching :class:`pystrich.bar_renderer.Bar1DRenderer`. Render entry
points (PNG, SVG, EPS) live on the base.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

    from pystrich.bar_renderer import Bar1DRenderer


class Bar1DEncoder(ABC):
    """Common encoder surface for 1D barcode formats."""

    options: Mapping[str, Any]
    width: int
    height: int

    def __init__(self, options: Mapping[str, Any] | None = None) -> None:
        self.options = options or {}
        self.width = 0
        self.height = 0

    @abstractmethod
    def init_renderer(self) -> Bar1DRenderer:
        """Construct a :class:`Bar1DRenderer` for the encoded symbol."""

    def get_imagedata(self, bar_width: int = 3) -> bytes:
        """Render the barcode and return PNG bytes.

        :param bar_width: Width in pixels of the narrowest bar.
        :returns: PNG-encoded image data.
        :rtype: bytes
        """
        barcode = self.init_renderer()
        imagedata = barcode.get_imagedata(bar_width)
        self.width = barcode.image_width
        self.height = barcode.image_height
        return imagedata

    def get_pilimage(self, bar_width: int = 3) -> PILImage:
        """Render the barcode and return a Pillow image.

        :param bar_width: Width in pixels of the narrowest bar.
        :returns: The rendered barcode.
        :rtype: PIL.Image.Image

        .. versionadded:: 0.11
        """
        barcode = self.init_renderer()
        img = barcode.get_pilimage(bar_width)
        self.width = barcode.image_width
        self.height = barcode.image_height
        return img

    def save(
        self, filename: str | os.PathLike[str], bar_width: int = 3
    ) -> None:
        """Render the barcode to a PNG file.

        :param filename: Path to write the PNG to.
        :param bar_width: Width in pixels of the narrowest bar.
        """
        self.init_renderer().write_file(filename, bar_width)

    def get_svg(self, bar_width: int = 3) -> str:
        """Render the barcode and return SVG markup.

        :param bar_width: Width in user units of the narrowest bar.
        :rtype: str

        .. versionadded:: 0.12
        """
        return self.init_renderer().get_svg(bar_width)

    def save_svg(
        self, filename: str | os.PathLike[str], bar_width: int = 3
    ) -> None:
        """Save the barcode as an SVG file. Pass a ``.svg`` filename.

        :param filename: SVG output path.
        :param bar_width: Width in user units of the narrowest bar.

        .. versionadded:: 0.12
        """
        self.init_renderer().write_svg_file(filename, bar_width)

    def get_eps(self, bar_width: int = 3) -> str:
        """Render the barcode and return EPS markup.

        :param bar_width: Width in PostScript points of the narrowest bar.
        :rtype: str

        .. versionadded:: 0.12
        """
        return self.init_renderer().get_eps(bar_width)

    def save_eps(
        self, filename: str | os.PathLike[str], bar_width: int = 3
    ) -> None:
        """Save the barcode as an EPS file. Pass an ``.eps`` filename.

        :param filename: EPS output path.
        :param bar_width: Width in PostScript points of the narrowest bar.

        .. versionadded:: 0.12
        """
        self.init_renderer().write_eps_file(filename, bar_width)
