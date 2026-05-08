#!/usr/bin/env python

"""2D Datamatrix barcode encoder

All needed by the user is done via the DataMatrixEncoder class:

>>> encoder = DataMatrixEncoder("HuDoRa")
>>> # encoder.save( "test.png" )
>>> print encoder.get_ascii()
XX  XX  XX  XX  XX  XX  XX
XX  XXXX  XXXXXX      XXXXXX
XXXXXX    XX          XX
XXXXXX    XX        XXXX  XX
XXXX  XX  XXXXXX
XXXXXX    XXXXXXXX    XXXXXX
XX    XX  XXXXXXXX  XXXX
XX    XX      XXXX      XXXX
XX  XXXXXXXXXX    XXXX
XX  XXXX    XX            XX
XX  XXXXXX  XXXXXX      XX
XXXXXX  XX  XX  XX  XX    XX
XX    XX              XX
XXXXXXXXXXXXXXXXXXXXXXXXXXXX


Implemented by Helen Taylor for HUDORA GmbH.
Updated and ported to Python 3 by Michael Mulqueen for Method B Ltd.

Detailed documentation on the format here:
http://grandzebu.net/informatique/codbar-en/datamatrix.htm
Further resources here: http://www.libdmtx.org/resources.php

You may use this under a BSD License.
"""

from __future__ import annotations

from pystrich.matrix_encoder import Matrix2DEncoder

from .data import FNC1, DataMatrixCodeword, DataMatrixData
from .placement import DataMatrixPlacer
from .renderer import DATAMATRIX_DEFAULT_QUIET_ZONE, DataMatrixRenderer
from .textencoder import TextEncoder

__all__ = [
    "FNC1",
    "DataMatrixCodeword",
    "DataMatrixData",
    "DataMatrixEncoder",
]


class DataMatrixEncoder(Matrix2DEncoder[int | None]):
    """Encode text as a Data Matrix (ECC 200) 2D barcode.

    The matrix size is selected automatically based on input length. Wrap
    the input in :class:`DataMatrixData` and pass an explicit ``encoding``
    of ``"ascii"``, ``"iso-8859-1"`` or ``"utf-8"`` — or pass
    ``auto_encoding=True`` to let the constructor pick the narrowest
    encoding that fits. To produce a GS1 Data Matrix, prefix the payload
    with the :data:`FNC1` marker.

    Typical use::

        encoder = DataMatrixEncoder(DataMatrixData("Hallo", encoding="ascii"))
        encoder.save("hallo.png")

        # Or, let DataMatrixData pick the encoding:
        encoder = DataMatrixEncoder(DataMatrixData("Rausschmeißer", auto_encoding=True))

    Plain ``str`` input is also accepted but falls back to a deprecated
    ``"compat"`` encoding that warns on non-ASCII bytes and produces output
    that does not decode correctly. New code should always wrap the input
    in :class:`DataMatrixData`.

    :ivar matrix: 2D list of ints (``0``/``1``, or ``None`` for unset cells)
        describing the symbol prior to rendering.
    :ivar regions: Number of square regions the symbol is divided into.
    :ivar quiet_zone: Width in modules of the white border applied at render time.
    :ivar width: Pixel width of the most recently rendered image. ``0`` until a
        render method has been called.
    :ivar height: Pixel height of the most recently rendered image.
    """

    regions: int
    quiet_zone: int

    def __init__(
        self,
        text: DataMatrixData | str,
        *,
        quiet_zone: int = DATAMATRIX_DEFAULT_QUIET_ZONE,
    ) -> None:
        """Encode ``text`` and lay it out in a Data Matrix grid.

        :param text: The data to encode. Either a :class:`DataMatrixData`
            (the recommended path) or a plain ``str`` (deprecated
            ``"compat"`` encoding).
        :param quiet_zone: Width of the surrounding white border in modules.
            Defaults to :data:`DATAMATRIX_DEFAULT_QUIET_ZONE`.
        :raises pystrich.exceptions.PyStrichInvalidInput: if ``text`` cannot
            be encoded (e.g. exceeds the supported capacity).

        .. versionchanged:: 0.10
           Added the ``quiet_zone`` parameter; previously the quiet zone was
           fixed at 2 modules.
        """

        enc = TextEncoder()
        codewords = enc.encode(text)
        self.width = 0
        self.height = 0
        matrix_size = enc.mtx_size * enc.regions
        self.regions = enc.regions
        self.quiet_zone = quiet_zone

        self.matrix = [[None] * matrix_size for _ in range(0, matrix_size)]

        placer = DataMatrixPlacer()
        placer.place(codewords, self.matrix)

    def init_renderer(self) -> DataMatrixRenderer:
        """Construct a :class:`DataMatrixRenderer` for the encoded matrix.

        Updates :attr:`width` and :attr:`height` with the renderer's pixel
        dimensions and returns the renderer.
        """
        dmtx = DataMatrixRenderer(self.matrix, self.regions, quiet_zone=self.quiet_zone)
        self.width = dmtx.width
        self.height = dmtx.height
        return dmtx
