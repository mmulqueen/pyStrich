#!/usr/bin/env python

"""2D Datamatrix barcode encoder

All needed by the user is done via the DataMatrixEncoder class:

>>> encoder = DataMatrixEncoder("HuDoRa")
>>> # encoder.save( "test.png" )
>>> print(encoder.get_ascii())
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

from typing import get_args

from pystrich.exceptions import PyStrichInvalidOption
from pystrich.limits import require_valid_int
from pystrich.matrix_encoder import Matrix2DEncoder

from .data import FNC1, DataMatrixCodeword, DataMatrixData
from .placement import DataMatrixPlacer
from .renderer import DATAMATRIX_DEFAULT_QUIET_ZONE, DataMatrixRenderer
from .textencoder import SymbolShape, TextEncoder

__all__ = [
    "FNC1",
    "DataMatrixCodeword",
    "DataMatrixData",
    "DataMatrixEncoder",
    "SymbolShape",
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
    :ivar regions: ``(h_regions, v_regions)`` — the number of regions the symbol
        is divided into horizontally and vertically.
    :ivar quiet_zone: Width in modules of the white border applied at render time.
    :ivar width: Pixel width of the most recently rendered image. ``0`` until a
        render method has been called.
    :ivar height: Pixel height of the most recently rendered image.
    """

    regions: tuple[int, int]
    quiet_zone: int

    def __init__(
        self,
        text: DataMatrixData | str,
        *,
        quiet_zone: int = DATAMATRIX_DEFAULT_QUIET_ZONE,
        force_byte_mode: bool = False,
        symbol_shape: SymbolShape = "square",
    ) -> None:
        """Encode ``text`` and lay it out in a Data Matrix grid.

        :param text: The data to encode. Either a :class:`DataMatrixData`
            (the recommended path) or a plain ``str`` (deprecated
            ``"compat"`` encoding).
        :param quiet_zone: Width of the surrounding white border in modules.
            Defaults to :data:`DATAMATRIX_DEFAULT_QUIET_ZONE`.
        :param force_byte_mode: Controls the encodation-mode selection.
            ``False`` (the default) auto-detects: marker constants like
            :data:`FNC1` route to a single-mode byte-by-byte path,
            marker-free payloads go through the multi-mode DP optimiser.
            ``True`` forces the byte-by-byte path for any payload, giving
            a predictable codeword stream at the cost of larger symbols
            for content the DP would otherwise pack into C40/Text/X12.
        :param symbol_shape: ``"square"`` (the default) forces a square symbol;
            ``"rectangular"`` forces one of the six rectangular sizes;
            ``"auto"`` picks whichever fitting symbol has the smallest area.
        :raises pystrich.exceptions.PyStrichInvalidPayloadLength: if ``text``
            exceeds the capacity of the largest symbol.
        :raises pystrich.exceptions.PyStrichInvalidOption: if ``symbol_shape``
            is not one of the accepted values.

        .. versionchanged:: 0.10
           Added the ``quiet_zone`` parameter; previously the quiet zone was
           fixed at 2 modules.

        .. versionchanged:: 0.15
           Added the ``force_byte_mode`` parameter.

        .. versionadded:: 0.17
           The ``symbol_shape`` parameter and rectangular symbol support.

        .. versionchanged:: 0.17
           :attr:`regions` is now a ``(h_regions, v_regions)`` tuple; it was
           previously a single ``int`` that only described square symbols.
        """

        require_valid_int(quiet_zone, name="quiet_zone", min_value=0)
        if symbol_shape not in get_args(SymbolShape):
            raise PyStrichInvalidOption(
                f"symbol_shape must be one of {get_args(SymbolShape)}, got {symbol_shape!r}"
            )

        enc = TextEncoder()
        codewords = enc.encode(text, force_byte_mode=force_byte_mode, symbol_shape=symbol_shape)
        self.width = 0
        self.height = 0
        self.regions = (enc.spec.h_regions, enc.spec.v_regions)
        self.quiet_zone = quiet_zone

        self.matrix = [[None] * enc.mapping_cols for _ in range(enc.mapping_rows)]

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
