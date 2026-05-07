#!/usr/bin/env python

"""QR Code encoder

All needed by the user is done via the QRCodeEncoder class:

>>> encoder = QRCodeEncoder("HuDoRa")
>>> # encoder.save( "test.png" )
>>> print encoder.get_ascii()

"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Literal

from pystrich.dxf import DxfUnit
from pystrich.marks import MarkShape

from .textencoder import TextEncoder
from .renderer import QRCodeRenderer

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


QRErrorCorrectionLevel = Literal["L", "M", "Q", "H"]


class QRCodeEncoder:
    """Encode a string as a QR Code 2D barcode.

    Typical use::

        encoder = QRCodeEncoder("https://example.com")
        encoder.save("qr.png")

    :ivar matrix: 2D list describing the symbol prior to rendering.
    :ivar width: Pixel width of the most recently rendered image.
    :ivar height: Pixel height of the most recently rendered image.
    """

    matrix: list[list[int]]
    width: int
    height: int

    def __init__(self, text: str, ecl: QRErrorCorrectionLevel | None = None) -> None:
        """Encode ``text`` and build the QR matrix.

        :param text: The data to encode.
        :param ecl: Error correction level. ``None`` (the default) selects
            ``"M"``; pass one of ``"L"``, ``"M"``, ``"Q"`` or ``"H"`` to
            override.
        """

        enc = TextEncoder()
        self.matrix = enc.encode(text, ecl)
        self.height = 0
        self.width = 0

    def init_renderer(self) -> QRCodeRenderer:
        """Construct a :class:`QRCodeRenderer` for the encoded matrix.

        Updates :attr:`width` and :attr:`height` with the renderer's
        dimensions and returns the renderer.
        """
        qrc = QRCodeRenderer(self.matrix)
        self.height = self.width = qrc.mtx_size
        return qrc

    def save(self, filename: str | os.PathLike[str], cellsize: int = 5) -> None:
        """Save the symbol as a PNG. Pass a ``.png`` filename.

        :param filename: PNG output path.
        :param cellsize: Side length in pixels of one module.
        """
        self.init_renderer().write_file(cellsize, filename)

    def get_imagedata(self, cellsize: int = 5) -> bytes:
        """Render the symbol and return PNG bytes.

        :param cellsize: Side length in pixels of one module.
        :returns: PNG-encoded image data.
        :rtype: bytes
        """
        return self.init_renderer().get_imagedata(cellsize)

    def get_pilimage(self, cellsize: int = 5) -> PILImage:
        """Render the symbol and return a Pillow image.

        :param cellsize: Side length in pixels of one module.
        :returns: The rendered symbol.
        :rtype: PIL.Image.Image

        .. versionadded:: 0.11
        """
        return self.init_renderer().get_pilimage(cellsize)

    def get_svg(
        self,
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
    ) -> str:
        """Render the symbol and return SVG markup.

        :param cellsize: Side length in user units of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :rtype: str

        .. versionadded:: 0.12
        """
        return self.init_renderer().get_svg(cellsize, inverse=inverse, mark_shape=mark_shape)

    def save_svg(
        self,
        filename: str | os.PathLike[str],
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
    ) -> None:
        """Save the symbol as an SVG file. Pass a ``.svg`` filename.

        :param filename: SVG output path.
        :param cellsize: Side length in user units of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.

        .. versionadded:: 0.12
        """
        self.init_renderer().write_svg_file(
            cellsize, filename, inverse=inverse, mark_shape=mark_shape
        )

    def get_eps(
        self,
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
    ) -> str:
        """Render the symbol and return EPS markup.

        :param cellsize: Side length in PostScript points of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :rtype: str

        .. versionadded:: 0.12
        """
        return self.init_renderer().get_eps(cellsize, inverse=inverse, mark_shape=mark_shape)

    def save_eps(
        self,
        filename: str | os.PathLike[str],
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
    ) -> None:
        """Save the symbol as an EPS file. Pass an ``.eps`` filename.

        :param filename: EPS output path.
        :param cellsize: Side length in PostScript points of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.

        .. versionadded:: 0.12
        """
        self.init_renderer().write_eps_file(
            cellsize, filename, inverse=inverse, mark_shape=mark_shape
        )

    def get_ascii(self) -> str:
        """Return an ASCII-art rendering of the symbol.

        :rtype: str
        """
        return self.init_renderer().get_ascii()

    def get_dxf(
        self,
        cellsize: float = 1.0,
        inverse: bool = True,
        units: DxfUnit | None = "mm",
        *,
        mark_shape: MarkShape = MarkShape.SQUARE_CELLS,
    ) -> str:
        """Return a DXF (CAD) representation of the symbol.

        :param cellsize: Side length of one module in ``units``.
        :param inverse: If ``True`` (the default), light modules are drawn as
            filled cells. If ``False``, dark modules are drawn, matching the
            normal appearance of the symbol.
        :param units: One of ``"in"``, ``"ft"``, ``"mi"``, ``"mm"``, ``"cm"``
            or ``"m"``, or ``None`` for Unspecified (``$INSUNITS=0``).
        :param mark_shape: How matched cells are grouped and drawn.
        :rtype: str

        .. versionadded:: 0.9

        .. versionchanged:: 0.12
            ``units`` now supports ``"in"``, ``"ft"``, ``"mi"``, ``"cm"``,
            ``"m"`` and ``None`` (Unspecified); previously any value other
            than ``"mm"`` was silently treated as unspecified.
        """
        return self.init_renderer().get_dxf(cellsize, inverse, units, mark_shape=mark_shape)
