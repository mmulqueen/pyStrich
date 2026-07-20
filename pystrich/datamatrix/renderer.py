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

    h_regions: int
    v_regions: int
    region_rows: int
    region_cols: int
    quiet_zone: int

    # Double-width glyphs make terminal output roughly square given the
    # typical 2:1 character aspect ratio.
    _SYMBOL: ClassVar[dict[int | None, str]] = {0: "  ", 1: "XX"}

    def __init__(
        self,
        matrix: list[list[int | None]],
        regions: tuple[int, int],
        *,
        quiet_zone: int = DATAMATRIX_DEFAULT_QUIET_ZONE,
    ) -> None:
        # matrix is the mapping matrix (data regions only, no finder pattern):
        # region_rows*v_regions rows by region_cols*h_regions columns.
        n_rows = len(matrix)
        n_cols = len(matrix[0])
        self.h_regions, self.v_regions = regions
        self.region_rows = n_rows // self.v_regions
        self.region_cols = n_cols // self.h_regions
        if quiet_zone < 0:
            raise PyStrichInvalidOption("Quiet zone must be non-negative")
        self.quiet_zone = quiet_zone

        self.matrix = matrix

        self._add_handle_space()

        # add the edge handles
        self._add_handles()

    def _put_cell(self, position: tuple[int, int], colour: int = 1) -> None:
        """Set the contents of the given cell"""

        posx, posy = position
        self.matrix[posy][posx] = colour

    def _add_handles(self) -> None:
        """Set up the edge handles"""

        for x_index in range(self.h_regions):
            for y_index in range(self.v_regions):
                x_origin = x_index * (self.region_cols + 2) + self.quiet_zone
                y_origin = y_index * (self.region_rows + 2) + self.quiet_zone
                x_max = x_origin + self.region_cols + 1
                y_max = y_origin + self.region_rows + 1

                # bottom solid border
                for posx in range(x_origin, x_max):
                    self._put_cell((posx, y_max))

                # left solid border
                for posy in range(y_origin, y_max):
                    self._put_cell((x_origin, posy))

                # top broken border
                for i in range(x_origin, x_max, 2):
                    self._put_cell((i, y_origin))

                # right broken border
                for i in range(y_max, y_origin, -2):
                    self._put_cell((x_max, i))

    def _add_handle_space(self, colour: int = 0) -> None:
        """Grow the matrix to make room for the edge handles.

        Splices the gaps between data regions, then wraps the result in
        the one-module handle ring and the quiet zone; :meth:`_add_handles`
        draws the finder pattern into the ring.
        """

        a_gap = 1  # Gap for alignment/"handles"
        gapped_width = self.width + (self.h_regions - 1) * a_gap * 2

        new_matrix: list[list[int | None]] = []
        for row_n, row in enumerate(self.matrix):
            if row_n > 0 and row_n % self.region_rows == 0:
                # Vertical gap between regions
                new_matrix.extend([colour] * gapped_width for _ in range(a_gap * 2))
            new_row: list[int | None] = []
            # Split according to regions
            for i in range(self.h_regions):
                if i > 0:
                    # Add the space for the alignment gap
                    new_row += [colour] * (a_gap * 2)
                new_row += row[i * self.region_cols : (i + 1) * self.region_cols]
            new_matrix.append(new_row)

        self.matrix = new_matrix
        self._add_border(colour, a_gap + self.quiet_zone)
