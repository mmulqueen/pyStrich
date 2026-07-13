"""Matrix placement for 2D datamatrix barcode encoder"""

from __future__ import annotations

from collections.abc import Sequence
from typing import NamedTuple


class _Plan(NamedTuple):
    """A replayable placement for one symbol size.

    ``groups[k]`` holds the eight matrix cells that carry codeword ``k``'s
    bits, in MSB-to-LSB order. ``corner`` and ``zero_cells`` capture the
    geometry-only tail (corner module and unused-cell fill) so the whole
    layout is data-independent and can be cached per ``(rows, cols)``.
    """

    groups: list[list[tuple[int, int]]]
    corner: list[tuple[int, int, int]]
    zero_cells: list[tuple[int, int]]


# The snake traversal maps codeword bits to cells purely from the symbol
# geometry, so each size's plan is computed once and replayed thereafter.
_PLAN_CACHE: dict[tuple[int, int], _Plan] = {}


class DataMatrixPlacer:
    """Class which takes care of placing codewords in the correct position
    in the 2D datamatrix"""

    matrix: list[list[int | None]]
    rows: int
    cols: int
    _record: list[tuple[int, int]] | None

    def __init__(self) -> None:
        """Initialise with an empty matrix"""
        self.matrix = []
        self.rows = 0
        self.cols = 0
        self._record = None

    def place_bit(self, position: tuple[int, int], bit: int) -> None:
        """Place bit in the correct location in the matrix"""

        posx, posy = position

        # If out of bounds, wrap around to the other side
        if posx < 0:
            posx += self.rows
            posy += 4 - ((self.rows + 4) % 8)

        if posy < 0:
            posy += self.cols
            posx += 4 - ((self.cols + 4) % 8)

        self.matrix[posx][posy] = bit
        if self._record is not None:
            self._record.append((posx, posy))

    def place_special_1(self, codeword: int) -> None:
        """Special corner case 1
        bottom left corner: |1|2|3|

        top right corner:   |4|5|
                              |6|
                              |7|
                              |8|"""

        self.place_bit((self.rows - 1, 0), (codeword & (0x01 << 7)) >> 7)
        self.place_bit((self.rows - 1, 1), (codeword & (0x01 << 6)) >> 6)
        self.place_bit((self.rows - 1, 2), (codeword & (0x01 << 5)) >> 5)
        self.place_bit((0, self.cols - 2), (codeword & (0x01 << 4)) >> 4)
        self.place_bit((0, self.cols - 1), (codeword & (0x01 << 3)) >> 3)
        self.place_bit((1, self.cols - 1), (codeword & (0x01 << 2)) >> 2)
        self.place_bit((2, self.cols - 1), (codeword & (0x01 << 1)) >> 1)
        self.place_bit((3, self.cols - 1), codeword & 0x01)

    def place_special_2(self, codeword: int) -> None:
        """Special corner case 2
        bottom left corner: |1|
                            |2|
                            |3|

        top right corner:  |4|5|6|7|
                                 |8|"""

        self.place_bit((self.rows - 3, 0), (codeword & (0x01 << 7)) >> 7)
        self.place_bit((self.rows - 2, 0), (codeword & (0x01 << 6)) >> 6)
        self.place_bit((self.rows - 1, 0), (codeword & (0x01 << 5)) >> 5)
        self.place_bit((0, self.cols - 4), (codeword & (0x01 << 4)) >> 4)
        self.place_bit((0, self.cols - 3), (codeword & (0x01 << 3)) >> 3)
        self.place_bit((0, self.cols - 2), (codeword & (0x01 << 2)) >> 2)
        self.place_bit((0, self.cols - 1), (codeword & (0x01 << 1)) >> 1)
        self.place_bit((1, self.cols - 1), codeword & 0x01)

    def place_special_3(self, codeword: int) -> None:
        """Special corner case 3
        bottom left corner: |1|
                            |2|
                            |3|

        top right corner:   |4|5|
                              |6|
                              |7|
                              |8|"""

        self.place_bit((self.rows - 3, 0), (codeword & (0x01 << 7)) >> 7)
        self.place_bit((self.rows - 2, 0), (codeword & (0x01 << 6)) >> 6)
        self.place_bit((self.rows - 1, 0), (codeword & (0x01 << 5)) >> 5)
        self.place_bit((0, self.cols - 2), (codeword & (0x01 << 4)) >> 4)
        self.place_bit((0, self.cols - 1), (codeword & (0x01 << 3)) >> 3)
        self.place_bit((1, self.cols - 1), (codeword & (0x01 << 2)) >> 2)
        self.place_bit((2, self.cols - 1), (codeword & (0x01 << 1)) >> 1)
        self.place_bit((3, self.cols - 1), codeword & 0x01)

    def place_special_4(self, codeword: int) -> None:
        """Special corner case 4
        bottom left corner: |1|

        bottom right corner: |2|

        top right corner: |3|4|5|
                          |6|7|8|"""

        self.place_bit((self.rows - 1, 0), (codeword & (0x01 << 7)) >> 7)
        self.place_bit((self.rows - 1, self.cols - 1), (codeword & (0x01 << 6)) >> 6)
        self.place_bit((0, self.cols - 3), (codeword & (0x01 << 5)) >> 5)
        self.place_bit((0, self.cols - 2), (codeword & (0x01 << 4)) >> 4)
        self.place_bit((0, self.cols - 1), (codeword & (0x01 << 3)) >> 3)
        self.place_bit((1, self.cols - 3), (codeword & (0x01 << 2)) >> 2)
        self.place_bit((1, self.cols - 2), (codeword & (0x01 << 1)) >> 1)
        self.place_bit((1, self.cols - 1), codeword & 0x01)

    def place_standard_shape(self, position: tuple[int, int], codeword: int) -> None:
        """Standard codeword placement
        |1|2|
        |3|4|5|
        |6|7|8|"""

        posx, posy = position

        if self.matrix[posx][posy] is None:
            self.place_bit((posx - 2, posy - 2), (codeword & (0x01 << 7)) >> 7)
            self.place_bit((posx - 2, posy - 1), (codeword & (0x01 << 6)) >> 6)
            self.place_bit((posx - 1, posy - 2), (codeword & (0x01 << 5)) >> 5)
            self.place_bit((posx - 1, posy - 1), (codeword & (0x01 << 4)) >> 4)
            self.place_bit((posx - 1, posy - 0), (codeword & (0x01 << 3)) >> 3)
            self.place_bit((posx, posy - 2), (codeword & (0x01 << 2)) >> 2)
            self.place_bit((posx, posy - 1), (codeword & (0x01 << 1)) >> 1)
            self.place_bit((posx, posy - 0), (codeword & 0x01))

    def place(self, codewords: Sequence[int], matrix: list[list[int | None]]) -> None:
        """Place all the given codewords into the given matrix
        Matrix should be correctly pre-sized"""

        rows = len(matrix)
        cols = len(matrix[0])

        plan = _PLAN_CACHE.get((rows, cols))
        if plan is None:
            plan = _PLAN_CACHE[(rows, cols)] = self._build_plan(rows, cols)

        for k, cells in enumerate(plan.groups):
            codeword = codewords[k]
            for bit, (posx, posy) in enumerate(cells):
                matrix[posx][posy] = (codeword >> (7 - bit)) & 0x01
        for posx, posy, bit in plan.corner:
            matrix[posx][posy] = bit
        for posx, posy in plan.zero_cells:
            matrix[posx][posy] = 0

    def _build_plan(self, rows: int, cols: int) -> _Plan:
        """Run the snake once on a scratch matrix, recording where each bit lands.

        Codeword values are irrelevant to the layout, so this places zeros and
        captures the resolved cell of every ``place_bit`` call. Each codeword
        emits exactly eight bits (MSB first), so the flat record chunks cleanly
        into per-codeword groups.
        """
        self.matrix = [[None] * cols for _ in range(rows)]
        self.rows = rows
        self.cols = cols
        record: list[tuple[int, int]] = []
        self._record = record

        row, col = 4, 0

        while True:
            # Special corner cases
            if row == self.rows and col == 0:
                self.place_special_1(0)

            elif row == self.rows - 2 and col == 0 and self.cols % 4:
                self.place_special_2(0)

            elif row == self.rows - 2 and col == 0 and (self.cols % 8 == 4):
                self.place_special_3(0)

            elif row == self.rows + 4 and col == 2 and (self.cols % 8 == 0):
                self.place_special_4(0)

            # Sweep upwards diagonally
            while True:
                if row < self.rows and col >= 0 and self.matrix[row][col] is None:
                    self.place_standard_shape((row, col), 0)

                row -= 2
                col += 2

                if row < 0 or col >= self.cols:
                    break

            row += 1
            col += 3

            # Sweep downwards diagonally
            while True:
                if row >= 0 and col < self.cols and self.matrix[row][col] is None:
                    self.place_standard_shape((row, col), 0)

                row += 2
                col -= 2

                if row >= self.rows or col < 0:
                    break

            row += 3
            col += 1

            if row >= self.rows and col >= self.cols:
                break

        self._record = None
        groups = [record[i : i + 8] for i in range(0, len(record), 8)]

        # Corner module: when the snake leaves the bottom-right cell untouched,
        # set the diagonal pattern. Geometry-only, so it lives in the plan.
        corner: list[tuple[int, int, int]] = []
        if self.matrix[rows - 1][cols - 1] is None:
            corner = [
                (rows - 1, cols - 1, 1),
                (rows - 2, cols - 2, 1),
                (rows - 1, cols - 2, 0),
                (rows - 2, cols - 1, 0),
            ]
            for posx, posy, bit in corner:
                self.matrix[posx][posy] = bit

        zero_cells = [(r, c) for r in range(rows) for c in range(cols) if self.matrix[r][c] is None]
        return _Plan(groups, corner, zero_cells)
