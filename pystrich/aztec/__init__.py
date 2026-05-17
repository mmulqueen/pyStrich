"""Aztec Code encoder.

Public entry: :class:`AztecEncoder`. See :class:`AztecData` for pinning
the character encoding explicitly.
"""

from __future__ import annotations

from typing import Literal

from pystrich.matrix_encoder import Matrix2DEncoder

from .data import AztecData
from .renderer import AZTEC_DEFAULT_QUIET_ZONE, AztecRenderer
from .textencoder import TextEncoder

__all__ = [
    "AZTEC_DEFAULT_QUIET_ZONE",
    "AztecData",
    "AztecEncoder",
    "AztecErrorCorrectionLevel",
    "AztecSymbolKind",
]

AztecErrorCorrectionLevel = int  # percentage 5..95
AztecSymbolKind = Literal["auto", "compact", "full"]


class AztecEncoder(Matrix2DEncoder[int]):
    """Encode text as an Aztec Code 2D barcode.

    A plain ``str`` is encoded with the narrowest character set that fits:
    ASCII, Latin-1 (ECI 3) or UTF-8 (ECI 26). Pass an :class:`AztecData` to
    pin the encoding explicitly.

    Typical use::

        encoder = AztecEncoder("https://github.com/mmulqueen/pyStrich")
        encoder.save("aztec.png")

    :ivar matrix: 2D list describing the symbol prior to rendering.
    :ivar quiet_zone: Width in modules of the white border applied at render time.
    :ivar width: Pixel width of the most recently rendered image.
    :ivar height: Pixel height of the most recently rendered image.
    """

    quiet_zone: int

    def __init__(
        self,
        text: str | AztecData,
        *,
        ecc: AztecErrorCorrectionLevel = 23,
        symbol_kind: AztecSymbolKind = "auto",
        layers: int | None = None,
        quiet_zone: int = AZTEC_DEFAULT_QUIET_ZONE,
    ) -> None:
        """Encode ``text`` and build the Aztec matrix.

        :param text: The data to encode. A plain ``str`` is auto-encoded;
            pass :class:`AztecData` to pin the encoding.
        :param ecc: Error correction percentage in 5..95. Default 23.
        :param symbol_kind: ``"auto"`` (the default), ``"compact"`` or
            ``"full"``. With ``"auto"`` the smallest fitting symbol is chosen.
        :param layers: Override the data layer count. Requires
            ``symbol_kind`` to be ``"compact"`` or ``"full"``.
        :param quiet_zone: Width of the surrounding white border in modules.
            Defaults to :data:`AZTEC_DEFAULT_QUIET_ZONE`.
        """
        if not isinstance(text, AztecData):
            text = AztecData(text, auto_encoding=True)
        encoder = TextEncoder()
        self.matrix = encoder.encode(text, ecc_pct=ecc, symbol_kind=symbol_kind, layers=layers)
        self.quiet_zone = quiet_zone
        self.height = 0
        self.width = 0

    def init_renderer(self) -> AztecRenderer:
        """Construct an :class:`AztecRenderer` for the encoded matrix."""
        renderer = AztecRenderer(self.matrix, quiet_zone=self.quiet_zone)
        self.width = renderer.width
        self.height = renderer.height
        return renderer
