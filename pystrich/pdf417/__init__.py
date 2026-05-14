"""PDF417 2D barcode encoder.

Typical use::

    encoder = PDF417Encoder("Hello, World!", ecl=2)
    encoder.save("hello.png")
    encoder.save_svg("hello.svg")

The :class:`PDF417Encoder` constructor picks sensible defaults: an
error correction level matching the spec's recommendation for the
data length when ``ecl`` is omitted, a near-square matrix shape when
``columns`` is omitted, and the narrowest fitting character encoding
when the input is a plain ``str``. Set ``row_height`` to change the
default Y/X = 3 row aspect; wrap the input in :class:`PDF417Data` to
pin the character encoding by hand.

Macro PDF417, Compact PDF417, and optimal mode-switching are not
implemented.
"""

from __future__ import annotations

from typing import Literal

from pystrich.matrix_encoder import Matrix2DEncoder

from .data import PDF417Data, PDF417Encoding
from .layout import DEFAULT_ROW_HEIGHT, build_module_matrix
from .renderer import PDF417_DEFAULT_QUIET_ZONE, PDF417Renderer
from .textencoder import _compact, assemble, pick_dimensions

PDF417ErrorCorrectionLevel = Literal[0, 1, 2, 3, 4, 5, 6, 7, 8]
"""PDF417 error correction levels."""

__all__ = [
    "DEFAULT_ROW_HEIGHT",
    "PDF417_DEFAULT_QUIET_ZONE",
    "PDF417Data",
    "PDF417Encoder",
    "PDF417Encoding",
    "PDF417ErrorCorrectionLevel",
]


def _auto_ecl(source_count: int) -> int:
    """Recommend a minimum error correction level for ``source_count`` codewords."""
    if source_count <= 40:
        return 2
    if source_count <= 160:
        return 3
    if source_count <= 320:
        return 4
    return 5


class PDF417Encoder(Matrix2DEncoder[int]):
    """Encode text as a PDF417 2D barcode.

    The matrix shape is determined by the data length, the error correction
    level, and an optional explicit column count. When ``ecl`` is omitted,
    it is chosen to match the spec's minimum-level recommendation for the
    given data length.

    :ivar matrix: 0/1 module grid built from the codeword stream.
    :ivar rows: Number of codeword rows in the symbol.
    :ivar columns: Number of data columns (excluding row indicators).
    :ivar ecl: Error correction level in effect.
    :ivar row_height: Matrix rows per codeword row (default 3).
    :ivar quiet_zone: White border applied by the renderer, in modules.
    """

    rows: int
    columns: int
    ecl: int
    row_height: int
    quiet_zone: int

    def __init__(
        self,
        text: PDF417Data | str,
        *,
        ecl: PDF417ErrorCorrectionLevel | None = None,
        columns: int | None = None,
        quiet_zone: int = PDF417_DEFAULT_QUIET_ZONE,
        row_height: int = DEFAULT_ROW_HEIGHT,
    ) -> None:
        source = _compact(text)
        ecl_value: int = _auto_ecl(len(source) + 1) if ecl is None else ecl
        rows, columns = pick_dimensions(len(source), ecl_value, columns)
        codewords = assemble(source, rows, columns, ecl_value)

        self.width = 0
        self.height = 0
        self.rows = rows
        self.columns = columns
        self.ecl = ecl_value
        self.row_height = row_height
        self.quiet_zone = quiet_zone
        self.matrix = build_module_matrix(
            codewords, rows, columns, ecl_value, row_height=row_height
        )

    def init_renderer(self) -> PDF417Renderer:
        """Construct a :class:`PDF417Renderer` for the encoded matrix.

        Wraps the matrix in a quiet zone before handing it back and updates
        :attr:`width` and :attr:`height` to the renderer's module dimensions.
        """
        renderer = PDF417Renderer(
            self.matrix, quiet_zone=self.quiet_zone, row_height=self.row_height
        )
        self.width = renderer.width
        self.height = renderer.height
        return renderer
