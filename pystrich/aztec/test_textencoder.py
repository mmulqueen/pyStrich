"""Tests for the high-level Aztec text encoder.

Anchors on the spec's worked example for "Code 2D!": the encoder must
pick a compact 1-layer symbol (15x15 modules, 6-bit codewords) at the
default ECC level of 23%, and the resulting matrix must reproduce the
spec's figure module-for-module.
"""

import pytest

from pystrich.aztec.data import AztecData
from pystrich.aztec.textencoder import TextEncoder

# fmt: off
CODE_2D_EXCL_GOLDEN = [
    [int(c == "#") for c in row]
    for row in (
        "...##...##.....",
        "......##.....#.",
        "#.##....#...#.#",
        ".############..",
        "####.......##.#",
        "...#.#####.##..",
        "#..#.#...#.####",
        "..##.#.#.#.#..#",
        "..##.#...#.#.#.",
        ".#.#.#####.#..#",
        "#..#.......#.##",
        "#..##########.#",
        ".#...##...#..#.",
        ".##....##.##.#.",
        "###..##.##.....",
    )
]
# fmt: on


def test_code_2d_excl_picks_compact_l1():
    """'Code 2D!' fits into a compact 1-layer symbol at 23% ECC."""
    data = AztecData("Code 2D!", encoding="ascii")
    matrix = TextEncoder().encode(data, ecc_pct=23)
    assert len(matrix) == 15
    assert all(len(row) == 15 for row in matrix)


# Fixed-structure cells (bullseye + chevrons) for a compact L1 symbol.
# Bullseye: 9x9 finder centred on the symbol; cells at rows/cols 3..11.
# Chevrons: 12 cells at the corners of the 11x11 core (rows/cols 2 and 12).
_BULLSEYE_CELLS = [(r, c) for r in range(3, 12) for c in range(3, 12)]
_CHEVRON_CELLS = [
    (3, 2),
    (2, 2),
    (2, 3),  # upper-left
    (2, 11),
    (2, 12),
    (3, 12),  # upper-right
    (11, 12),
    (12, 12),
    (12, 11),  # lower-right
    (11, 2),
    (12, 2),
    (12, 3),  # lower-left
]

# Mode-ring cells, 28 bits clockwise from the upper-left of the core.
# Top L->R, right T->B, bottom R->L, left B->T; chevron cells are skipped.
_MODE_RING_CELLS = (
    [(2, c) for c in range(4, 11)]
    + [(r, 12) for r in range(4, 11)]
    + [(12, c) for c in range(10, 3, -1)]
    + [(r, 2) for r in range(10, 3, -1)]
)


def test_code_2d_excl_fixed_structures_match_spec():
    """The bullseye and chevrons in the encoded matrix match the spec figure.

    Isolates fixed-structure placement from data-area placement: if the
    finder pattern and orientation chevrons are at the right cells with
    the right values, any whole-matrix mismatch is purely in the mode
    message ring or data spiral.
    """
    data = AztecData("Code 2D!", encoding="ascii")
    matrix = TextEncoder().encode(data, ecc_pct=23)
    for r, c in _BULLSEYE_CELLS + _CHEVRON_CELLS:
        assert matrix[r][c] == CODE_2D_EXCL_GOLDEN[r][c], (
            f"fixed cell ({r}, {c}): got {matrix[r][c]}, spec {CODE_2D_EXCL_GOLDEN[r][c]}"
        )


def test_code_2d_excl_mode_ring_matches_spec():
    """The mode-message ring in the encoded matrix matches the spec figure.

    Independent of the data spiral: if this passes alongside the fixed
    structures test, any whole-matrix mismatch is purely in the data area.
    """
    data = AztecData("Code 2D!", encoding="ascii")
    matrix = TextEncoder().encode(data, ecc_pct=23)
    for r, c in _MODE_RING_CELLS:
        assert matrix[r][c] == CODE_2D_EXCL_GOLDEN[r][c], (
            f"mode ring cell ({r}, {c}): got {matrix[r][c]}, spec {CODE_2D_EXCL_GOLDEN[r][c]}"
        )


def test_code_2d_excl_matrix_matches_spec():
    """The encoded matrix reproduces the spec's figure module-for-module."""
    data = AztecData("Code 2D!", encoding="ascii")
    matrix = TextEncoder().encode(data, ecc_pct=23)
    assert matrix == CODE_2D_EXCL_GOLDEN


@pytest.mark.parametrize(
    "codeword, start_col",
    [
        pytest.param(40, 2, id="cw40-at-cols-2-4"),
        pytest.param(20, 5, id="cw20-at-cols-5-7"),
        pytest.param(10, 8, id="cw10-at-cols-8-10"),
    ],
)
def test_code_2d_excl_top_strip_first_codewords(codeword, start_col):
    """First three placed codewords (the trailing EC checkwords 40, 20, 10
    after reversal) sit at the top of the data spiral in 3-col x 2-row
    bricks adjacent to the core's upper-left corner.

    The LSB-pair domino is at the leftmost col and the MSB-pair domino at
    the rightmost; within each domino MSB is at the outer (top) row and
    LSB at the inner (bottom) row.
    """
    data = AztecData("Code 2D!", encoding="ascii")
    matrix = TextEncoder().encode(data, ecc_pct=23)
    for i in range(3):
        col = start_col + i
        # LSB pair on the left, MSB pair on the right.
        inner_bit = (codeword >> (2 * i)) & 1
        outer_bit = (codeword >> (2 * i + 1)) & 1
        assert matrix[1][col] == inner_bit, (
            f"cw {codeword} col {col} inner: got {matrix[1][col]}, expected {inner_bit}"
        )
        assert matrix[0][col] == outer_bit, (
            f"cw {codeword} col {col} outer: got {matrix[0][col]}, expected {outer_bit}"
        )
