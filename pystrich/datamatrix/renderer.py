"""Datamatrix renderer"""

from __future__ import annotations

from typing import ClassVar

from pystrich.exceptions import PyStrichInvalidOption
from pystrich.matrix_renderer import Matrix2DRenderer

DATAMATRIX_DEFAULT_QUIET_ZONE = 2


def repr_matrix(matrix: list[list[int | None]]) -> str:
    return "\n".join(repr(x) for x in matrix)


class DataMatrixRenderer(Matrix2DRenderer[int | None]):
    """Rendering class - given a pre-populated datamatrix.
    it will add edge handles and render to either to an image
    (including quiet zone) or ascii printout"""

    regions: int
    region_size: int
    quiet_zone: int

    # Double-width glyphs make terminal output roughly square given the
    # typical 2:1 character aspect ratio.
    _SYMBOL: ClassVar[dict[int | None, str]] = {0: '  ', 1: 'XX'}

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
