"""Shared base class for 2D matrix barcode renderers.

The 2D formats (QR Code, Data Matrix) both produce a 2D module matrix and
render it identically once the matrix (with quiet zones and any
format-specific borders or handles) is in place. This module captures
that shared surface; format-specific subclasses populate :attr:`matrix`,
:attr:`width` and :attr:`height` in their ``__init__`` and override
:attr:`_SYMBOL` if their ASCII rendering needs different glyphs.
"""

from __future__ import annotations

import os
from abc import ABC
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from PIL import Image

from pystrich.dxf import DxfUnit, matrix_to_dxf
from pystrich.eps import matrix_to_eps
from pystrich.marks import MarkShape
from pystrich.svg import matrix_to_svg

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


# Cell type. Most 2D formats use 0/1; Data Matrix additionally uses None
# during placement to mean "unset".
CellT = TypeVar("CellT", int, "int | None")


class Matrix2DRenderer(ABC, Generic[CellT]):
    """Common rendering surface for 2D matrix barcode formats."""

    matrix: list[list[CellT]]
    width: int
    height: int

    _PIXEL: ClassVar[dict[int | None, bytes]] = {0: b"\xff", 1: b"\x00"}
    _SYMBOL: ClassVar[dict[int | None, str]] = {0: ' ', 1: 'X'}

    def get_pilimage(self, cellsize: int) -> PILImage:
        """Return the matrix as a PIL image."""
        buff = self.get_buffer(cellsize)
        return Image.frombuffer(
            'L',
            (self.width * cellsize, self.height * cellsize),
            buff, 'raw', 'L', 0, -1,
        )

    def write_file(
        self, cellsize: int, filename: str | os.PathLike[str]
    ) -> None:
        """Write the matrix out to an image file."""
        self.get_pilimage(cellsize).save(filename)

    def get_imagedata(self, cellsize: int) -> bytes:
        """Write the matrix out as PNG to a bytestream."""
        buffer = BytesIO()
        self.get_pilimage(cellsize).save(buffer, "PNG")
        return buffer.getvalue()

    def get_buffer(self, cellsize: int) -> bytes:
        """Convert the matrix into the buffer format used by PIL."""
        # PIL writes image buffers from the bottom up, so feed in rows in
        # reverse.
        buf = b""
        for row in self.matrix[::-1]:
            bufrow = b''.join([self._PIXEL[cell] * cellsize for cell in row])
            for _ in range(0, cellsize):
                buf += bufrow
        return buf

    def get_ascii(self) -> str:
        """Return an ASCII-art rendering of the matrix."""
        return '\n'.join(
            ''.join(self._SYMBOL[cell] for cell in row)
            for row in self.matrix
        ) + '\n'

    def get_svg(
        self, cellsize: int, *, inverse: bool, mark_shape: MarkShape
    ) -> str:
        """Return the matrix as an SVG string."""
        return matrix_to_svg(
            self.matrix, cellsize, inverse=inverse, mark_shape=mark_shape
        )

    def write_svg_file(
        self,
        cellsize: int,
        filename: str | os.PathLike[str],
        *,
        inverse: bool,
        mark_shape: MarkShape,
    ) -> None:
        """Write the matrix out to an SVG file."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(self.get_svg(cellsize, inverse=inverse, mark_shape=mark_shape))

    def get_eps(
        self, cellsize: int, *, inverse: bool, mark_shape: MarkShape
    ) -> str:
        """Return the matrix as an EPS string."""
        return matrix_to_eps(
            self.matrix, cellsize, inverse=inverse, mark_shape=mark_shape
        )

    def write_eps_file(
        self,
        cellsize: int,
        filename: str | os.PathLike[str],
        *,
        inverse: bool,
        mark_shape: MarkShape,
    ) -> None:
        """Write the matrix out to an EPS file."""
        with open(filename, "w", encoding="ascii") as f:
            f.write(self.get_eps(cellsize, inverse=inverse, mark_shape=mark_shape))

    def get_dxf(
        self,
        cellsize: float,
        inverse: bool,
        units: DxfUnit | None,
        *,
        mark_shape: MarkShape,
    ) -> str:
        """Return the matrix as a DXF string."""
        return matrix_to_dxf(
            self.matrix, cellsize, inverse=inverse, units=units, mark_shape=mark_shape
        )