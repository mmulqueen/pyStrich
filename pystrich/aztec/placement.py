"""Aztec module placement — bullseye, orientation chevrons, reference grid, data spiral.

Public helpers take and mutate a row-major ``list[list[int]]`` matrix in
matrix coordinates. The spec describes the symbol in centre-origin
Cartesian terms with y pointing up; that framing only appears in the
test goldens, where it is used to derive the expected cell values.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from itertools import chain

from pystrich.aztec.symbol import SymbolKind, codeword_bits, module_count


def _finder_radius(kind: SymbolKind) -> int:
    return 4 if kind == "compact" else 6


def _core_size(kind: SymbolKind) -> int:
    return 11 if kind == "compact" else 15


def draw_bullseye(matrix: list[list[int]], origin: tuple[int, int], kind: SymbolKind) -> None:
    """Paint the bullseye into the matrix at the given origin.

    :param matrix: target 2D list (rows x cols), mutated in place.
    :param origin: ``(row, col)`` of the core's top-left cell.
    :param kind: ``"compact"`` (9x9 bullseye in 11x11 core) or ``"full"``
        (13x13 bullseye in 15x15 core).
    """
    f = _finder_radius(kind)
    core = _core_size(kind)
    centre = (core - 1) // 2
    r0, c0 = origin
    for dr in range(core):
        for dc in range(core):
            d = max(abs(dr - centre), abs(dc - centre))
            if d <= f:
                matrix[r0 + dr][c0 + dc] = (d + 1) % 2


def draw_orientation_chevrons(
    matrix: list[list[int]], origin: tuple[int, int], kind: SymbolKind
) -> None:
    """Paint the four orientation chevrons at the core corners.

    Pattern: upper-left all dark; upper-right has the corner and the cell
    below it dark, the cell to its left light; lower-right has only the cell
    above the corner dark, with the corner and the cell to its left light;
    lower-left all light. The dark count decreases by one each corner going
    clockwise, identifying which corner is "up" for the decoder.
    """
    core = _core_size(kind)
    r0, c0 = origin
    n = core - 1

    matrix[r0][c0] = 1
    matrix[r0][c0 + 1] = 1
    matrix[r0 + 1][c0] = 1

    matrix[r0][c0 + n] = 1
    matrix[r0 + 1][c0 + n] = 1
    matrix[r0][c0 + n - 1] = 0

    matrix[r0 + n - 1][c0 + n] = 1
    matrix[r0 + n][c0 + n] = 0
    matrix[r0 + n][c0 + n - 1] = 0

    matrix[r0 + n][c0] = 0
    matrix[r0 + n][c0 + 1] = 0
    matrix[r0 + n - 1][c0] = 0


def is_reference_cell(row: int, col: int, symbol_size: int) -> bool:
    """True if ``(row, col)`` lies on a reference grid row or column.

    The reference grid exists in full-range symbols only; callers should not
    invoke this for compact symbols.
    """
    centre = (symbol_size - 1) // 2
    return (row - centre) % 16 == 0 or (col - centre) % 16 == 0


def reference_cell_value(row: int, col: int, symbol_size: int) -> int:
    """Dark (1) or light (0) value for a reference grid cell."""
    centre = (symbol_size - 1) // 2
    return ((row - centre) + (col - centre) + 1) % 2


def draw_reference_grid(matrix: list[list[int]], symbol_size: int) -> None:
    """Paint every reference grid cell into the matrix."""
    for r in range(symbol_size):
        for c in range(symbol_size):
            if is_reference_cell(r, c, symbol_size):
                matrix[r][c] = reference_cell_value(r, c, symbol_size)


def _mode_ring_positions(kind: SymbolKind) -> list[tuple[int, int]]:
    if kind == "compact":
        n = 11
        return list(
            chain(
                ((0, c) for c in range(2, 9)),
                ((r, n - 1) for r in range(2, 9)),
                ((n - 1, c) for c in range(n - 3, 1, -1)),
                ((r, 0) for r in range(n - 3, 1, -1)),
            )
        )
    # full: skip the centre cell of each side (reference grid)
    n = 15
    centre = (n - 1) // 2
    return list(
        chain(
            ((0, c) for c in range(2, centre)),
            ((0, c) for c in range(centre + 1, n - 2)),
            ((r, n - 1) for r in range(2, centre)),
            ((r, n - 1) for r in range(centre + 1, n - 2)),
            ((n - 1, c) for c in range(n - 3, centre, -1)),
            ((n - 1, c) for c in range(centre - 1, 1, -1)),
            ((r, 0) for r in range(n - 3, centre, -1)),
            ((r, 0) for r in range(centre - 1, 1, -1)),
        )
    )


def lay_mode_ring(
    matrix: list[list[int]],
    bits: Sequence[int],
    origin: tuple[int, int],
    kind: SymbolKind,
) -> None:
    """Lay the mode message bits around the core's outer ring, clockwise from the upper-left.

    :param matrix: target 2D list (mutated in place).
    :param bits: 28 (compact) or 40 (full) MSB-first mode message bits.
    :param origin: ``(row, col)`` of the core's top-left cell.
    :param kind: ``"compact"`` or ``"full"``.
    """
    r0, c0 = origin
    for bit, (r, c) in zip(bits, _mode_ring_positions(kind), strict=True):
        matrix[r0 + r][c0 + c] = bit


def _walk_outward(
    start: int, direction: int, count: int, is_grid_fn: Callable[[int], bool]
) -> list[int]:
    """Return ``count`` positions stepping by ``direction``, skipping grid cells."""
    out: list[int] = []
    cur = start
    while len(out) < count:
        if not is_grid_fn(cur):
            out.append(cur)
        cur += direction
    return out


def _data_cells(symbol_size: int, kind: SymbolKind, layers: int) -> Iterator[tuple[int, int]]:
    """Yield data area cells in clockwise spiral, inner-then-outer per domino.

    The spiral starts adjacent to the upper-left corner of the Core Symbol
    and walks clockwise: top L->R, right T->B, bottom R->L, left B->T. Each
    side's range stops before its successor's starting column/row so that
    the matrix corners go to the side they introduce (e.g. the upper-right
    corner cells fall under the top run, the lower-right under the right
    run, etc.). Each domino is yielded as ``(inner, outer)`` with inner
    closer to the symbol's centre. Reference grid cells are skipped.
    """
    core_size = _core_size(kind)
    core_start = (symbol_size - core_size) // 2
    core_end = core_start + core_size - 1
    centre = (symbol_size - 1) // 2

    def is_grid(pos: int) -> bool:
        return kind == "full" and (pos - centre) % 16 == 0

    # Each walk yields 2 positions per layer; index 2L-2 = inner, 2L-1 = outer.
    top_rows = _walk_outward(core_start - 1, -1, 2 * layers, is_grid)
    bot_rows = _walk_outward(core_end + 1, +1, 2 * layers, is_grid)
    left_cols = _walk_outward(core_start - 1, -1, 2 * layers, is_grid)
    right_cols = _walk_outward(core_end + 1, +1, 2 * layers, is_grid)

    for layer in range(1, layers + 1):
        inner_top = top_rows[2 * layer - 2]
        outer_top = top_rows[2 * layer - 1]
        inner_bot = bot_rows[2 * layer - 2]
        outer_bot = bot_rows[2 * layer - 1]
        inner_left = left_cols[2 * layer - 2]
        outer_left = left_cols[2 * layer - 1]
        inner_right = right_cols[2 * layer - 2]
        outer_right = right_cols[2 * layer - 1]

        # Top: cols adjacent to the core's left edge through the layer's
        # outer-right column (incorporates the upper-right corner cells).
        for c in range(inner_left + 1, outer_right + 1):
            if not is_grid(c):
                yield (inner_top, c)
                yield (outer_top, c)
        # Right: rows from just below the top run through the layer's outer
        # bottom (incorporates the lower-right corner cells).
        for r in range(inner_top + 1, outer_bot + 1):
            if not is_grid(r):
                yield (r, inner_right)
                yield (r, outer_right)
        # Bottom: cols R->L from just left of the right run through the
        # layer's outer-left column (incorporates the lower-left corner).
        for c in range(inner_right - 1, outer_left - 1, -1):
            if not is_grid(c):
                yield (inner_bot, c)
                yield (outer_bot, c)
        # Left: rows B->T from just above the bottom run through the layer's
        # outer top (incorporates the upper-left corner cells).
        for r in range(inner_bot - 1, outer_top - 1, -1):
            if not is_grid(r):
                yield (r, inner_left)
                yield (r, outer_left)


def _lay_codewords(
    matrix: list[list[int]],
    codewords: Sequence[int],
    *,
    width: int,
    kind: SymbolKind,
    layers: int,
) -> None:
    """Lay the data + EC codewords into the spiral, in reverse order.

    Bits are laid LSB-first per codeword so that the spiral, which yields
    each domino as ``(inner, outer)``, puts the LSB pair at the leftmost
    domino of a codeword's brick and the MSB pair at the rightmost.
    """
    cell_iter = _data_cells(len(matrix), kind, layers)
    for cw in reversed(codewords):
        for i in range(width):
            try:
                r, c = next(cell_iter)
            except StopIteration:
                return
            matrix[r][c] = (cw >> i) & 1


def build_matrix(
    kind: SymbolKind,
    *,
    layers: int,
    codewords: Sequence[int],
    mode_word: Sequence[int],
) -> list[list[int]]:
    """Assemble the full Aztec symbol matrix.

    :param kind: ``"compact"`` or ``"full"``.
    :param layers: number of data layers.
    :param codewords: data + EC codewords in natural order.
    :param mode_word: 28 (compact) or 40 (full) MSB-first mode message bits.
    :returns: a ``size`` x ``size`` matrix of 0/1.
    """
    size = module_count(kind, layers)
    width = codeword_bits(kind, layers)
    core_start = (size - _core_size(kind)) // 2
    core_origin = (core_start, core_start)

    matrix = [[0] * size for _ in range(size)]

    if kind == "full":
        draw_reference_grid(matrix, size)

    draw_bullseye(matrix, core_origin, kind)
    draw_orientation_chevrons(matrix, core_origin, kind)
    lay_mode_ring(matrix, mode_word, core_origin, kind)
    _lay_codewords(matrix, codewords, width=width, kind=kind, layers=layers)

    return matrix
