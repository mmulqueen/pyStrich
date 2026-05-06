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

    def save(self, filename: str | os.PathLike[str], cellsize: int = 5) -> None:
        """Save the symbol as a PNG. Pass a ``.png`` filename.

        :param filename: PNG output path.
        :param cellsize: Side length in pixels of one module.
        """

        qrc = QRCodeRenderer(self.matrix)
        qrc.write_file(cellsize, filename)

    def get_imagedata(self, cellsize: int = 5) -> bytes:
        """Render the symbol and return PNG bytes.

        :param cellsize: Side length in pixels of one module.
        :returns: PNG-encoded image data.
        :rtype: bytes
        """

        qrc = QRCodeRenderer(self.matrix)
        imagedata = qrc.get_imagedata(cellsize)
        self.height = qrc.mtx_size
        self.width = qrc.mtx_size
        return imagedata

    def get_pilimage(self, cellsize: int = 5) -> PILImage:
        """Render the symbol and return a Pillow image.

        :param cellsize: Side length in pixels of one module.
        :returns: The rendered symbol.
        :rtype: PIL.Image.Image

        .. versionadded:: 0.11
        """
        qrc = QRCodeRenderer(self.matrix)
        img = qrc.get_pilimage(cellsize)
        self.height = qrc.mtx_size
        self.width = qrc.mtx_size
        return img

    def get_ascii(self) -> str:
        """Return an ASCII-art rendering of the symbol.

        :rtype: str
        """
        qrc = QRCodeRenderer(self.matrix)
        return qrc.get_ascii()

    def get_dxf(
        self, cellsize: float = 1.0, inverse: bool = True, units: str = "mm"
    ) -> str:
        """Return a DXF (CAD) representation of the symbol.

        :param cellsize: Side length of one module in ``units``.
        :param inverse: If ``True``, dark modules are drawn as filled cells.
        :param units: Unit string written into the DXF header (e.g. ``"mm"``).
        :rtype: str

        .. versionadded:: 0.9
        """
        qrc = QRCodeRenderer(self.matrix)
        return qrc.get_dxf(cellsize, inverse, units)
