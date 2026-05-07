"""Datamatrix renderer"""

from __future__ import annotations

import os
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image
from pystrich.dxf import DxfUnit, matrix_to_dxf
from pystrich.eps import matrix_to_eps
from pystrich.exceptions import PyStrichInvalidOption
from pystrich.marks import MarkShape
from pystrich.svg import matrix_to_svg

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

DATAMATRIX_DEFAULT_QUIET_ZONE = 2

_PIXEL: dict[int | None, bytes] = {0: b"\xff", 1: b"\x00"}
_SYMBOL: dict[int | None, str] = {0: '  ', 1: 'XX'}


def repr_matrix(matrix: list[list[int | None]]) -> str:
    return "\n".join(repr(x) for x in matrix)


class DataMatrixRenderer:
    """Rendering class - given a pre-populated datamatrix.
    it will add edge handles and render to either to an image
    (including quiet zone) or ascii printout"""

    width: int
    height: int
    regions: int
    region_size: int
    quiet_zone: int
    matrix: list[list[int | None]]

    def __init__(
        self,
        matrix: list[list[int | None]],
        regions: int,
        *,
        quiet_zone: int = DATAMATRIX_DEFAULT_QUIET_ZONE,
    ) -> None:
        self.width = len(matrix)
        self.height = len(matrix[0])
        self.regions = regions
        self.region_size = self.width//regions
        if quiet_zone < 0:
            raise PyStrichInvalidOption("Quiet zone must be non-negative")
        self.quiet_zone = quiet_zone

        self.matrix = matrix

        # grow the matrix in preparation for the handles
        self.add_border(colour=0)

        # add the edge handles
        self.add_handles()

    def put_cell(self, position: tuple[int, int], colour: int = 1) -> None:
        """Set the contents of the given cell"""

        posx, posy = position
        self.matrix[posy][posx] = colour

    def add_handles(self) -> None:
        """Set up the edge handles"""

        for x_index in range(self.regions):
            for y_index in range(self.regions):
                x_origin = x_index * (self.region_size + 2) + self.quiet_zone
                y_origin = y_index * (self.region_size + 2) + self.quiet_zone
                x_max = x_origin + self.region_size + 1
                y_max = y_origin + self.region_size + 1

                # bottom solid border
                for posx in range(x_origin, x_max):
                    self.put_cell((posx, y_max))

                # left solid border
                for posy in range(y_origin, y_max):
                    self.put_cell((x_origin, posy))

                # top broken border
                for i in range(x_origin, x_max, 2):
                    self.put_cell((i, y_origin))

                # right broken border
                for i in range(y_max, y_origin, -2):
                    self.put_cell((x_max, i))

    def add_border(self, colour: int = 1) -> None:
        """Wrap the matrix in a border of given width
            and colour"""

        a_gap = 1  # Gap for alignment/"handles"
        self.width += a_gap*2 + self.quiet_zone*2 + (self.regions-1)*a_gap*2
        self.height += a_gap*2 + self.quiet_zone*2 + (self.regions-1)*a_gap*2

        new_matrix: list[list[int | None]] = []
        for i in range(a_gap+self.quiet_zone):
            new_matrix += [[colour]*self.width]

        for row_n, row in enumerate(self.matrix):
            if row_n > 0 and row_n % self.region_size == 0:
                # Vertical gap between regions
                for j in range(a_gap*2):
                    new_matrix += [[colour]*self.width]
            # Left gap
            new_row: list[int | None] = [colour]*(a_gap+self.quiet_zone)
            # Split according to regions
            for i in range(self.regions):
                part = row[i*self.region_size:(i+1)*self.region_size]
                if i > 0:
                    # Add the space for the alignment gap
                    new_row += [colour]*(a_gap*2)
                new_row += part
            # Right gap
            new_row += [colour]*(a_gap+self.quiet_zone)
            new_matrix.append(new_row)

        for i in range(a_gap+self.quiet_zone):
            new_matrix += [[colour]*self.width]
        self.matrix = new_matrix

    def get_pilimage(self, cellsize: int) -> PILImage:
        """Return the matrix as an PIL object"""

        # get the matrix into the right buffer format
        buff = self.get_buffer(cellsize)

        # write the buffer out to an image
        img = Image.frombuffer('L',
                               (self.width * cellsize, self.height * cellsize),
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
        """Return the matrix as an SVG string."""
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
        """Return the matrix as an EPS string."""
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
