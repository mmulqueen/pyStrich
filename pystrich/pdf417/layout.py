"""Matrix layout for PDF417 symbols.

Turns a linear codeword stream into the 0/1 module grid the renderer
draws. Every row has the same shape:

    start (17 modules) | left indicator (17) | data * c (17 each) | right indicator (17) | stop (18)

Rows cycle through clusters 0, 3 and 6 in turn -- adjacent rows always
use different clusters, which is how a scanner detects row transitions.
The cluster picks which of three bar-space patterns represents each
codeword value.
"""

from __future__ import annotations

from ._cluster_patterns import CLUSTER_0, CLUSTER_3, CLUSTER_6

START_PATTERN: int = 0x1FEA8
"""Start pattern, widths 8,1,1,1,1,1,1,3 -- 17 modules beginning with a bar."""
START_WIDTH: int = 17

STOP_PATTERN: int = 0x3FA29
"""Stop pattern, widths 7,1,1,3,1,1,1,2,1 -- 18 modules ending with a bar."""
STOP_WIDTH: int = 18

CODEWORD_WIDTH: int = 17
"""Every codeword occupies 17 modules."""

_CLUSTERS = (CLUSTER_0, CLUSTER_3, CLUSTER_6)

DEFAULT_ROW_HEIGHT: int = 3
"""Spec-recommended row height ``Y >= 3 * X`` (module width)."""


def left_row_indicator(row: int, rows: int, columns: int, ecl: int) -> int:
    """Codeword value of the left row indicator for ``row`` (1-based).

    The indicator encodes row number, total rows, column count and error
    correction level, spread across three rows in a repeating cycle.
    """
    f = row
    k = ((f - 1) % 3) * 3
    base = 30 * ((f - 1) // 3)
    if k == 0:
        return base + (rows - 1) // 3
    if k == 3:
        return base + ecl * 3 + (rows - 1) % 3
    return base + (columns - 1)


def right_row_indicator(row: int, rows: int, columns: int, ecl: int) -> int:
    """Codeword value of the right row indicator for ``row`` (1-based).

    Encodes the same four parameters as the left indicator but shuffled
    so the spread completes across three consecutive rows.
    """
    f = row
    k = ((f - 1) % 3) * 3
    base = 30 * ((f - 1) // 3)
    if k == 0:
        return base + (columns - 1)
    if k == 3:
        return base + (rows - 1) // 3
    return base + ecl * 3 + (rows - 1) % 3


def _bits(pattern: int, width: int) -> list[int]:
    """Expand a binary pattern into ``width`` module values, MSB first."""
    return [(pattern >> (width - 1 - i)) & 1 for i in range(width)]


def row_modules(columns: int) -> int:
    """Number of modules in one codeword row, excluding quiet zones."""
    return START_WIDTH + CODEWORD_WIDTH * (columns + 2) + STOP_WIDTH


def build_module_matrix(
    codewords: list[int],
    rows: int,
    columns: int,
    ecl: int,
    *,
    row_height: int = DEFAULT_ROW_HEIGHT,
) -> list[list[int]]:
    """Build a 0/1 module matrix from the codeword stream.

    Each codeword row produces ``row_height`` matrix rows so square-celled
    renderers naturally produce the spec's recommended Y >= 3*X aspect.
    The output has shape ``(rows * row_height, row_modules(columns))``.

    :param codewords: Linear codeword stream of length ``rows * columns``.
    :param rows: Symbol height in codeword rows.
    :param columns: Number of data columns (excluding indicators).
    :param ecl: Error correction level (used in row indicator formulas).
    :param row_height: Vertical pixels per codeword row; defaults to 3.
    """
    if len(codewords) != rows * columns:
        raise ValueError(f"codeword stream has {len(codewords)} entries; expected {rows * columns}")
    if row_height < 1:
        raise ValueError(f"row_height must be >= 1, got {row_height}")

    matrix: list[list[int]] = []
    start_bits = _bits(START_PATTERN, START_WIDTH)
    stop_bits = _bits(STOP_PATTERN, STOP_WIDTH)

    for r in range(rows):
        f = r + 1
        cluster = _CLUSTERS[(f - 1) % 3]
        left_cw = left_row_indicator(f, rows, columns, ecl)
        right_cw = right_row_indicator(f, rows, columns, ecl)
        data_codewords = codewords[r * columns : (r + 1) * columns]

        row_bits: list[int] = []
        row_bits.extend(start_bits)
        row_bits.extend(_bits(cluster[left_cw], CODEWORD_WIDTH))
        for cw in data_codewords:
            row_bits.extend(_bits(cluster[cw], CODEWORD_WIDTH))
        row_bits.extend(_bits(cluster[right_cw], CODEWORD_WIDTH))
        row_bits.extend(stop_bits)

        for _ in range(row_height):
            matrix.append(list(row_bits))

    return matrix
