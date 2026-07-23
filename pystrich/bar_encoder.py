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
from typing import TYPE_CHECKING, Any, ClassVar

from pystrich._dataurl import png_to_data_url, svg_to_data_url

if TYPE_CHECKING:
    from pystrich._pillow import PILImage
    from pystrich.bar_renderer import Bar1DRenderer
    from pystrich.colour import RGBA
    from pystrich.marks import SymbolMarks


class Bar1DEncoder(ABC):
    """Common encoder surface for 1D barcode formats."""

    options: Mapping[str, Any]
    width: int
    height: int

    # Longest input the format accepts, in characters; ``None`` falls back to the
    # global ceiling. Fixed-length formats set their maximum.
    _MAX_PAYLOAD_LENGTH: ClassVar[int | None] = None

    def __init__(self, options: Mapping[str, Any] | None = None) -> None:
        self.options = options or {}
        self.width = 0
        self.height = 0

    @abstractmethod
    def init_renderer(self) -> Bar1DRenderer:
        """Construct a :class:`Bar1DRenderer` for the encoded symbol."""

    def get_imagedata(
        self,
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> bytes:
        """Render the barcode and return PNG bytes.

        :param bar_width: Width in pixels of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :returns: PNG-encoded image data.
        :rtype: bytes

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        barcode = self.init_renderer()
        imagedata = barcode.get_imagedata(bar_width, dark_hex=dark_hex, light_hex=light_hex)
        self.width = barcode.image_width
        self.height = barcode.image_height
        return imagedata

    def png_dataurl(
        self,
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the barcode and return a PNG ``data:`` URL string.

        :param bar_width: Width in pixels of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :rtype: str

        .. versionadded:: 0.15

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return png_to_data_url(
            self.get_imagedata(bar_width, dark_hex=dark_hex, light_hex=light_hex)
        )

    def get_pilimage(
        self,
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> PILImage:
        """Render the barcode and return a Pillow image.

        :param bar_width: Width in pixels of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :returns: The rendered barcode.
        :rtype: PIL.Image.Image

        .. versionadded:: 0.11

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        barcode = self.init_renderer()
        img = barcode.get_pilimage(bar_width, dark_hex=dark_hex, light_hex=light_hex)
        self.width = barcode.image_width
        self.height = barcode.image_height
        return img

    def save(
        self,
        filename: str | os.PathLike[str],
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Render the barcode to a PNG file.

        :param filename: Path to write the PNG to.
        :param bar_width: Width in pixels of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        self.init_renderer().write_file(filename, bar_width, dark_hex=dark_hex, light_hex=light_hex)

    def get_svg(
        self,
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the barcode and return SVG markup.

        :param bar_width: Width in user units of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :rtype: str

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return self.init_renderer().get_svg(bar_width, dark_hex=dark_hex, light_hex=light_hex)

    def svg_dataurl(
        self,
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the barcode and return an SVG ``data:`` URL string.

        :param bar_width: Width in user units of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :rtype: str

        .. versionadded:: 0.15

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return svg_to_data_url(self.get_svg(bar_width, dark_hex=dark_hex, light_hex=light_hex))

    def save_svg(
        self,
        filename: str | os.PathLike[str],
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the barcode as an SVG file. Pass a ``.svg`` filename.

        :param filename: SVG output path.
        :param bar_width: Width in user units of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        self.init_renderer().write_svg_file(
            filename, bar_width, dark_hex=dark_hex, light_hex=light_hex
        )

    def get_eps(
        self,
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the barcode and return EPS markup.

        :param bar_width: Width in PostScript points of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``, opaque. Defaults to white.
        :rtype: str

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return self.init_renderer().get_eps(bar_width, dark_hex=dark_hex, light_hex=light_hex)

    def save_eps(
        self,
        filename: str | os.PathLike[str],
        bar_width: int = 3,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the barcode as an EPS file. Pass an ``.eps`` filename.

        :param filename: EPS output path.
        :param bar_width: Width in PostScript points of the narrowest bar.
        :param dark_hex: Bar and text colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``, opaque. Defaults to white.

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        self.init_renderer().write_eps_file(
            filename, bar_width, dark_hex=dark_hex, light_hex=light_hex
        )

    def get_rect_marks(self) -> SymbolMarks:
        """Return the barcode's dark bars as rectangles in layout units.

        :rtype: pystrich.marks.SymbolMarks

        .. versionadded:: 0.18
        """
        return self.init_renderer().get_rect_marks()
