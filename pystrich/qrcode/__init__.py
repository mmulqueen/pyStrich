#!/usr/bin/env python

"""QR Code encoder

All needed by the user is done via the QRCodeEncoder class:

>>> encoder = QRCodeEncoder("HuDoRa")
>>> # encoder.save( "test.png" )
>>> print encoder.get_ascii()

"""

from __future__ import annotations

from typing import Literal

from pystrich.matrix_encoder import Matrix2DEncoder

from .data import QRCodeData
from .renderer import QRCodeRenderer
from .textencoder import TextEncoder

__all__ = ["QRCodeData", "QRCodeEncoder", "QRErrorCorrectionLevel"]

QRErrorCorrectionLevel = Literal["L", "M", "Q", "H"]


class QRCodeEncoder(Matrix2DEncoder[int]):
    """Encode text as a QR Code 2D barcode.

    A plain ``str`` is encoded with the narrowest character set that fits:
    ASCII (no ECI), Latin-1 (ECI 3), or UTF-8 (ECI 26). Pass a
    :class:`QRCodeData` to pin the encoding explicitly.

    Typical use::

        encoder = QRCodeEncoder("https://d-nb.info/gnd/135514053")
        encoder.save("qr.png")

    :ivar matrix: 2D list describing the symbol prior to rendering.
    :ivar width: Pixel width of the most recently rendered image.
    :ivar height: Pixel height of the most recently rendered image.
    """

    def __init__(
        self,
        text: str | QRCodeData,
        ecl: QRErrorCorrectionLevel | None = None,
    ) -> None:
        """Encode ``text`` and build the QR matrix.

        :param text: The data to encode. A plain ``str`` is auto-encoded;
            pass a :class:`QRCodeData` to pin the encoding.
        :param ecl: Error correction level. ``None`` (the default) selects
            ``"M"``; pass one of ``"L"``, ``"M"``, ``"Q"`` or ``"H"`` to
            override.
        """

        if not isinstance(text, QRCodeData):
            text = QRCodeData(text, auto_encoding=True)
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
        self.width = qrc.width
        self.height = qrc.height
        return qrc
