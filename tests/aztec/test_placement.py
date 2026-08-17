"""Tests for the placement primitives — bullseye, orientation chevrons, reference grid.

Goldens are derived directly from the spec rules:
  - Finder: dark where ``(max(|x|, |y|) + 1) mod 2 == 1`` within the F-square.
  - Orientation bits: explicit cell coordinates in math (x, y) with y pointing up.
  - Reference grid: cells where ``x mod 16 == 0`` or ``y mod 16 == 0``,
    value ``(x + y + 1) mod 2``.

Math coords map to matrix coords as ``row = center - y``, ``col = center + x``.
"""

import pytest

from pystrich.aztec.placement import (
    build_matrix,
    draw_bullseye,
    draw_orientation_chevrons,
    draw_reference_grid,
    is_reference_cell,
    lay_mode_ring,
    reference_cell_value,
)

# fmt: off
COMPACT_CORE_GOLDEN = [
    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0],
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]

FULL_CORE_GOLDEN = [
    [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 0, 0, 0, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0],
    [0, 1, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 1, 0],
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0],
    [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
]
# fmt: on


@pytest.mark.parametrize(
    "kind, size, golden",
    [
        pytest.param("compact", 11, COMPACT_CORE_GOLDEN, id="compact-11x11"),
        pytest.param("full", 15, FULL_CORE_GOLDEN, id="full-15x15"),
    ],
)
def test_core_matches_golden(kind, size, golden):
    """``draw_bullseye`` + ``draw_orientation_chevrons`` reproduces the spec figures."""
    matrix = [[0] * size for _ in range(size)]
    draw_bullseye(matrix, (0, 0), kind)
    draw_orientation_chevrons(matrix, (0, 0), kind)
    assert matrix == golden


def test_bullseye_drawn_at_origin_offset():
    """The bullseye lands at the given origin, not at the matrix origin."""
    matrix = [[0] * 15 for _ in range(15)]
    draw_bullseye(matrix, (2, 2), "compact")
    # Bullseye center for compact lands at row 2 + 5 = 7, col 2 + 5 = 7 -> dark
    assert matrix[7][7] == 1
    # Outside the offset bullseye region stays light
    assert matrix[0][0] == 0
    assert matrix[14][14] == 0


def test_reference_cell_classification():
    """Cells whose center-relative x or y is a multiple of 16 are on the grid."""
    # Full-range L10: 57x57, center at (28, 28).
    # Reference rows: 12, 28, 44. Reference cols: same.
    size = 57
    assert is_reference_cell(28, 0, size)
    assert is_reference_cell(0, 28, size)
    assert is_reference_cell(12, 5, size)
    assert is_reference_cell(44, 30, size)
    assert is_reference_cell(12, 44, size)  # intersection
    assert not is_reference_cell(0, 0, size)
    assert not is_reference_cell(13, 5, size)
    assert not is_reference_cell(15, 15, size)


def test_reference_cell_value_alternates():
    """``(x + y + 1) mod 2`` alternates along each reference row/column."""
    size = 57
    # Center (28, 28): x=0, y=0 -> (0+0+1)%2 = 1 dark.
    assert reference_cell_value(28, 28, size) == 1
    # On reference row 12, walking across columns 0..3:
    # row 12 -> y_math = 28 - 12 = 16; col 0 -> x = -28; col 1 -> x = -27; ...
    # (x + y + 1) mod 2 = (-28 + 16 + 1) % 2 = -11 % 2 = 1 (dark)
    assert reference_cell_value(12, 0, size) == 1
    assert reference_cell_value(12, 1, size) == 0
    assert reference_cell_value(12, 2, size) == 1
    assert reference_cell_value(12, 3, size) == 0


def test_reference_cells_match_bullseye_where_they_overlap():
    """Spec invariant: reference grid values agree with the bullseye on overlap."""
    # Use a full-range symbol whose center column passes through the bullseye.
    size = 57
    center = 28
    # The center column inside the bullseye spans rows 22..34 (since F=6 puts the bullseye 6 rows above/below center).
    for row in range(22, 35):
        ref_val = reference_cell_value(row, center, size)
        # The bullseye at center column has rel_y = center - row, rel_x = 0.
        # Bullseye formula: (max(0, |rel_y|) + 1) % 2 = (|rel_y| + 1) % 2.
        rel_y = center - row
        bull_val = (abs(rel_y) + 1) % 2
        assert ref_val == bull_val


def test_draw_reference_grid_sets_grid_cells_to_value():
    """``draw_reference_grid`` writes grid values into all reference cells."""
    size = 57
    matrix = [[0] * size for _ in range(size)]
    draw_reference_grid(matrix, size)
    # Sample a few cells across the grid
    assert matrix[12][12] == reference_cell_value(12, 12, size)
    assert matrix[44][0] == reference_cell_value(44, 0, size)
    assert matrix[28][30] == reference_cell_value(28, 30, size)
    # And non-grid cells stay light
    assert matrix[13][13] == 0
    assert matrix[15][16] == 0


def test_draw_reference_grid_no_op_for_l1():
    """No reference rows or columns fall in the data area of full-range L1."""
    # Full-range L1 is 19x19, center at 9. Reference rows: y mod 16 == 0
    # means only y=0 (the center row) qualifies; ±16 would be at row -7 or 25.
    # So the grid touches only the bullseye and core, all of which the bullseye
    # and chevron painters will cover.
    size = 19
    matrix = [[0] * size for _ in range(size)]
    draw_reference_grid(matrix, size)
    # Center row and column are the only reference cells; all others light.
    for r in range(size):
        for c in range(size):
            if r == 9 or c == 9:
                # Reference cells along the center axis carry their grid value
                assert matrix[r][c] == reference_cell_value(r, c, size)
            else:
                assert matrix[r][c] == 0


# Mode message ring


def test_compact_mode_ring_bit_positions():
    """28 mode bits lay clockwise around the 11x11 core: top L-R, right T-B, bottom R-L, left B-T."""
    matrix = [[0] * 11 for _ in range(11)]
    # A 28-bit mode word: bits 0..27 = the value at that ring position.
    bits = [(i + 1) % 2 for i in range(28)]  # 1, 0, 1, 0, ...
    lay_mode_ring(matrix, bits, (0, 0), "compact")
    # bit 0 (=1) lands at (0, 2); bit 6 lands at (0, 8); bit 7 at (2, 10);
    # bit 13 at (8, 10); bit 14 at (10, 8); bit 20 at (10, 2);
    # bit 21 at (8, 0); bit 27 at (2, 0).
    assert matrix[0][2] == bits[0]
    assert matrix[0][8] == bits[6]
    assert matrix[2][10] == bits[7]
    assert matrix[8][10] == bits[13]
    assert matrix[10][8] == bits[14]
    assert matrix[10][2] == bits[20]
    assert matrix[8][0] == bits[21]
    assert matrix[2][0] == bits[27]


def test_full_mode_ring_skips_center_bit_of_each_side():
    """40 full-range mode bits skip the center cell of each side (reference grid)."""
    matrix = [[0] * 15 for _ in range(15)]
    bits = [1] * 40
    lay_mode_ring(matrix, bits, (0, 0), "full")
    # Top side: cols 2..6 and 8..12 are set (col 7 is the reference grid center, skipped).
    for c in (2, 3, 4, 5, 6, 8, 9, 10, 11, 12):
        assert matrix[0][c] == 1
    assert matrix[0][7] == 0  # center of top side -> skipped
    # Right side: rows 2..6 and 8..12 set; row 7 skipped.
    for r in (2, 3, 4, 5, 6, 8, 9, 10, 11, 12):
        assert matrix[r][14] == 1
    assert matrix[7][14] == 0
    # Bottom and left similarly
    assert matrix[14][7] == 0
    assert matrix[7][0] == 0


def test_full_mode_ring_clockwise_order():
    """40 bits lay clockwise: bit 0 at top-left, bit 39 at upper-left of left side going up."""
    matrix = [[0] * 15 for _ in range(15)]
    bits = list(
        range(40)
    )  # use values 0..39 (a few become 0 but doesn't matter for the position check)
    # Replace 0 with a unique sentinel so we can distinguish from an unset cell.
    # Instead, mark all cells with -1 to start, then check assignment.
    for r in range(15):
        for c in range(15):
            matrix[r][c] = -1
    lay_mode_ring(matrix, bits, (0, 0), "full")
    # bit 0 lands at top-left of top side (col 2)
    assert matrix[0][2] == 0
    # bit 4 at end of top first-half (col 6)
    assert matrix[0][6] == 4
    # bit 5 at start of top second-half (col 8)
    assert matrix[0][8] == 5
    # bit 9 at end of top (col 12)
    assert matrix[0][12] == 9
    # bit 10 at top of right side (row 2)
    assert matrix[2][14] == 10
    # bit 19 at bottom of right side (row 12)
    assert matrix[12][14] == 19
    # bit 20 at right end of bottom side (col 12, going right-to-left)
    assert matrix[14][12] == 20
    # bit 29 at left end of bottom (col 2)
    assert matrix[14][2] == 29
    # bit 30 at bottom of left side (row 12, going bottom-to-top)
    assert matrix[12][0] == 30
    # bit 39 at top of left side (row 2)
    assert matrix[2][0] == 39


# Full symbol assembly (compact L1, no reference grid)


def test_build_matrix_compact_l1_dimensions():
    """A compact L1 build returns a 15x15 matrix."""
    cw = [0] * 17  # placeholder codewords
    mode = [0] * 28
    matrix = build_matrix("compact", layers=1, codewords=cw, mode_word=mode)
    assert len(matrix) == 15
    assert all(len(row) == 15 for row in matrix)


def test_build_matrix_full_l1_dimensions():
    cw = [0] * 21
    mode = [0] * 40
    matrix = build_matrix("full", layers=1, codewords=cw, mode_word=mode)
    assert len(matrix) == 19
    assert all(len(row) == 19 for row in matrix)


def test_build_matrix_full_l10_dimensions_and_reference_grid_present():
    """A full L10 build returns 57x57 with the reference grid correctly placed."""
    # Layer 10 has 272 codewords of 10 bits.
    cw = [0] * 272
    mode = [0] * 40
    matrix = build_matrix("full", layers=10, codewords=cw, mode_word=mode)
    assert len(matrix) == 57
    # Reference grid sample: rows 12 and 44 should carry the alternating values.
    # E.g., (12, 0): rel y=16, rel x=-28 -> (16 - 28 + 1) % 2 = -11 % 2 = 1.
    assert matrix[12][0] == reference_cell_value(12, 0, 57)
    assert matrix[44][0] == reference_cell_value(44, 0, 57)
    # Off-grid cells in the data area are 0 here (codewords were all 0).
    assert matrix[2][0] == 0


def test_build_matrix_codeword_reversal():
    """Codewords are placed in reverse order.

    The spiral starts adjacent to the core's upper-left corner — column 2 in
    a compact L1 — so the last codeword's 6 bits fill (1,2), (0,2), (1,3),
    (0,3), (1,4), (0,4) (inner-then-outer per domino, L->R across the top).
    """
    cw = [0] * 17
    cw[16] = 0b111111  # last codeword: all 1s → produces 6 dark cells
    mode = [0] * 28
    matrix = build_matrix("compact", layers=1, codewords=cw, mode_word=mode)
    cells = [
        matrix[1][2],
        matrix[0][2],  # 1st domino: inner, outer
        matrix[1][3],
        matrix[0][3],  # 2nd domino
        matrix[1][4],
        matrix[0][4],  # 3rd domino
    ]
    assert cells == [1, 1, 1, 1, 1, 1], f"First 6 cells should be all 1 from cw[16], got {cells}"
