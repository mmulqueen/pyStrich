"""Tests for the PDF417 module-matrix layout.

The layout step turns a codeword stream into a 0/1 matrix where each
cell is one module. These tests pin down (a) the spec-fixed start, stop
and codeword widths; (b) the row-indicator formulas; and (c) the
structural shape of the assembled matrix.
"""

from __future__ import annotations

import pytest

from pystrich.pdf417 import layout
from pystrich.pdf417._cluster_patterns import CLUSTER_0, CLUSTER_3, CLUSTER_6
from pystrich.pdf417.layout import (
    CODEWORD_WIDTH,
    START_PATTERN,
    START_WIDTH,
    STOP_PATTERN,
    STOP_WIDTH,
    _bits,
    build_module_matrix,
    left_row_indicator,
    right_row_indicator,
    row_modules,
)


def test_start_pattern_matches_spec_widths():
    """Start pattern widths 8,1,1,1,1,1,1,3 sum to 17 modules."""
    assert START_WIDTH == 17
    # bar(8) + space(1) + bar(1) + space(1) + bar(1) + space(1) + bar(1) + space(3)
    expected = int("11111111" + "0" + "1" + "0" + "1" + "0" + "1" + "000", 2)
    assert START_PATTERN == expected


def test_stop_pattern_matches_spec_widths():
    """Stop pattern widths 7,1,1,3,1,1,1,2,1 sum to 18 modules."""
    assert STOP_WIDTH == 18
    # bar(7)+space(1)+bar(1)+space(3)+bar(1)+space(1)+bar(1)+space(2)+bar(1)
    expected = int("1111111" + "0" + "1" + "000" + "1" + "0" + "1" + "00" + "1", 2)
    assert STOP_PATTERN == expected


def test_codeword_width_is_seventeen_modules():
    """Every PDF417 codeword spans exactly 17 modules."""
    assert CODEWORD_WIDTH == 17


def test_bits_expansion_is_msb_first():
    """Patterns expand to lists of 0/1 with the high bit at position 0."""
    assert _bits(0b10101, 5) == [1, 0, 1, 0, 1]
    assert _bits(START_PATTERN, START_WIDTH)[0] == 1
    assert _bits(START_PATTERN, START_WIDTH)[-1] == 0


@pytest.mark.parametrize(
    "row, rows, columns, ecl, expected_left",
    [
        # K = 0 rows: base + (r-1)//3
        (1, 3, 5, 2, 0),
        (1, 9, 5, 2, 2),
        (4, 9, 5, 2, 32),
        # K = 3 rows: base + ecl*3 + (r-1)%3
        (2, 3, 5, 2, 8),
        (2, 5, 5, 4, 13),
        # K = 6 rows: base + (c-1)
        (3, 3, 5, 2, 4),
        (6, 9, 8, 2, 37),
    ],
)
def test_left_row_indicator_matches_spec_formula(row, rows, columns, ecl, expected_left):
    """Left-indicator codewords match the spec formula at every K value."""
    assert left_row_indicator(row, rows, columns, ecl) == expected_left


@pytest.mark.parametrize(
    "row, rows, columns, ecl, expected_right",
    [
        # K = 0: base + (c-1)
        (1, 3, 5, 2, 4),
        (4, 9, 8, 2, 37),
        # K = 3: base + (r-1)//3
        (2, 9, 5, 2, 2),
        (5, 9, 5, 2, 32),
        # K = 6: base + ecl*3 + (r-1)%3
        (3, 3, 5, 2, 8),
        (6, 9, 5, 2, 38),
    ],
)
def test_right_row_indicator_matches_spec_formula(row, rows, columns, ecl, expected_right):
    """Right-indicator codewords match the spec formula at every K value."""
    assert right_row_indicator(row, rows, columns, ecl) == expected_right


def test_build_module_matrix_has_correct_dimensions():
    """Matrix shape is ``(rows * row_height, c*17 + 69)``."""
    codewords = [0] * 9
    matrix = build_module_matrix(codewords, rows=3, columns=3, ecl=1, row_height=3)
    assert len(matrix) == 9
    assert len(matrix[0]) == row_modules(3) == 3 * 17 + 69


def test_build_module_matrix_row_modules_formula():
    """row_modules(c) = start(17) + (c+2)*17 + stop(18) = c*17 + 69."""
    for c in [1, 3, 10, 30]:
        assert row_modules(c) == c * 17 + 69


def test_build_module_matrix_replicates_each_codeword_row():
    """row_height=3 means three identical matrix rows per codeword row."""
    codewords = [0, 1, 2, 3, 4, 5, 6, 7, 8]  # 3 rows x 3 cols
    matrix = build_module_matrix(codewords, rows=3, columns=3, ecl=1, row_height=3)
    # Rows 0/1/2 are the same codeword row; 3/4/5 are the next; etc.
    assert matrix[0] == matrix[1] == matrix[2]
    assert matrix[3] == matrix[4] == matrix[5]
    assert matrix[6] == matrix[7] == matrix[8]
    # Distinct codeword rows produce distinct matrix rows.
    assert matrix[0] != matrix[3]


def test_build_module_matrix_starts_each_row_with_start_pattern():
    """Every row begins with the 17-module start pattern."""
    codewords = [0] * 9
    matrix = build_module_matrix(codewords, rows=3, columns=3, ecl=1, row_height=1)
    start_bits = _bits(START_PATTERN, START_WIDTH)
    for row in matrix:
        assert row[:START_WIDTH] == start_bits


def test_build_module_matrix_ends_each_row_with_stop_pattern():
    """Every row ends with the 18-module stop pattern."""
    codewords = [0] * 9
    matrix = build_module_matrix(codewords, rows=3, columns=3, ecl=1, row_height=1)
    stop_bits = _bits(STOP_PATTERN, STOP_WIDTH)
    for row in matrix:
        assert row[-STOP_WIDTH:] == stop_bits


def test_build_module_matrix_uses_correct_cluster_per_row():
    """Row F uses cluster ((F-1) % 3) * 3.

    Three rows, three columns, all codewords = 0. Each row's first data
    codeword is the same value (0) but encoded with a different cluster,
    so the bars differ per row.
    """
    matrix = build_module_matrix([0] * 9, rows=3, columns=3, ecl=1, row_height=1)
    data_start = START_WIDTH + CODEWORD_WIDTH
    end = data_start + CODEWORD_WIDTH
    assert matrix[0][data_start:end] == _bits(CLUSTER_0[0], CODEWORD_WIDTH)
    assert matrix[1][data_start:end] == _bits(CLUSTER_3[0], CODEWORD_WIDTH)
    assert matrix[2][data_start:end] == _bits(CLUSTER_6[0], CODEWORD_WIDTH)


def test_build_module_matrix_rejects_wrong_codeword_count():
    """A codeword stream that doesn't equal rows*columns is a programmer error."""
    with pytest.raises(ValueError, match="expected"):
        build_module_matrix([0] * 8, rows=3, columns=3, ecl=1)


def test_build_module_matrix_rejects_zero_row_height():
    """row_height must be at least 1; zero would produce an empty matrix."""
    with pytest.raises(ValueError, match=">= 1"):
        build_module_matrix([0] * 9, rows=3, columns=3, ecl=1, row_height=0)


def test_each_cluster_table_has_929_codewords():
    """All three cluster tables index codewords 0..928."""
    assert len(CLUSTER_0) == 929
    assert len(CLUSTER_3) == 929
    assert len(CLUSTER_6) == 929


@pytest.mark.parametrize("cluster_table, k", [(CLUSTER_0, 0), (CLUSTER_3, 3), (CLUSTER_6, 6)])
def test_cluster_patterns_satisfy_k_constraint(cluster_table, k):
    """Each entry decodes to bar widths whose K equals the cluster label.

    ``K = (b1 - b2 + b3 - b4 + 9) mod 9``. This is the property that lets
    decoders identify row transitions, so getting the cluster assignment
    right is structurally essential.
    """
    for pattern in cluster_table:
        widths = []
        current = (pattern >> 16) & 1
        run = 0
        for i in range(16, -1, -1):
            bit = (pattern >> i) & 1
            if bit == current:
                run += 1
            else:
                widths.append(run)
                current = bit
                run = 1
        widths.append(run)
        b1, _, b2, _, b3, _, b4, _ = widths
        assert (b1 - b2 + b3 - b4 + 9) % 9 == k


def test_layout_module_constants_round_trip_via_str():
    """``_bits`` agrees with the binary-string form of the start pattern."""
    bits = layout._bits(START_PATTERN, START_WIDTH)
    assert "".join(str(b) for b in bits) == "11111111010101000"
