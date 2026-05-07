"""QR Code renderer"""

from __future__ import annotations

import os
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image

from pystrich.dxf import DxfUnit, matrix_to_dxf
from pystrich.eps import matrix_to_eps
from pystrich.marks import MarkShape
from pystrich.svg import matrix_to_svg

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

_PIXEL: dict[int, bytes] = {0: b"\xff", 1: b"\x00"}
_SYMBOL: dict[int, str] = {0: ' ', 1: 'X'}


class QRCodeRenderer:
    """Rendering class - given a pre-populated QR Code matrix.
    it will add edge handles and render to either to an image
    (including quiet zone) or ascii printout"""

    mtx_size: int
    matrix: list[list[int]]

    def __init__(self, matrix: list[list[int]]) -> None:

        self.mtx_size = len(matrix)
        self.matrix = matrix

        self.add_border(colour=0, width=4)

    def add_border(self, colour: int = 1, width: int = 4) -> None:
        """Wrap the matrix in a border of given width
            and colour"""

        self.mtx_size += width * 2

        self.matrix = [[colour, ] * self.mtx_size, ] * width + \
                      [[colour, ] * width + self.matrix[i] + [colour, ] * width
                          for i in range(0, self.mtx_size - (width * 2))] + \
                      [[colour, ] * self.mtx_size, ] * width

    def get_pilimage(self, cellsize: int) -> PILImage:
        """Return the matrix as a PIL object"""

        # get the matrix into the right buffer format
        buff = self.get_buffer(cellsize)

        # write the buffer out to an image
        img = Image.frombuffer(
            'L',
            (self.mtx_size * cellsize, self.mtx_size * cellsize),
            buff, 'raw', 'L', 0, -1)
        return img

    def write_file(self, cellsize: int, filename: str | os.PathLike[str]) -> None:
        """Write the matrix out to an image file"""
        img = self.get_pilimage(cellsize)
        img.save(filename)

    def get_imagedata(self, cellsize: int) -> bytes:
        """Write the matrix out as PNG to an bytestream"""
        imagedata = BytesIO()
        img = self.get_pilimage(cellsize)
        img.save(imagedata, "PNG")
        return imagedata.getvalue()

    def get_svg(self, cellsize: int, *, inverse: bool, mark_shape: MarkShape) -> str:
        """Return the matrix as an SVG string with the QR quiet zone applied."""
        return matrix_to_svg(self.matrix, cellsize, inverse=inverse, mark_shape=mark_shape)

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

    def get_eps(self, cellsize: int, *, inverse: bool, mark_shape: MarkShape) -> str:
        """Return the matrix as an EPS string with the QR quiet zone applied."""
        return matrix_to_eps(self.matrix, cellsize, inverse=inverse, mark_shape=mark_shape)

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

    def get_buffer(self, cellsize: int) -> bytes:
        """Convert the matrix into the buffer format used by PIL"""

        # PIL writes image buffers from the bottom up,
        # so feed in the rows in reverse
        buf = b""
        for row in self.matrix[::-1]:
            bufrow = b''.join([_PIXEL[cell] * cellsize for cell in row])
            for _ in range(0, cellsize):
                buf += bufrow
        return buf

    def get_ascii(self) -> str:
        """Write an ascii version of the matrix out to screen"""

        return '\n'.join(''.join(_SYMBOL[cell] for cell in row) for row in self.matrix) + '\n'

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
