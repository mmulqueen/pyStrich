"""Tests for the symbol-geometry table.

The spec values are hardcoded here, and the implementation in
``symbol.py`` is asserted against them. The duplication is deliberate: a
typo in either file is caught.
"""

import pytest

from pystrich.aztec.symbol import (
    COMPACT_LAYERS,
    FULL_LAYERS,
    codeword_bits,
    module_count,
    total_bits,
    total_codewords,
)
from pystrich.exceptions import PyStrichInvalidOption

_SPEC_ROWS = [
    pytest.param("compact", 1, 15, 17, 6, id="compact-L1"),
    pytest.param("compact", 2, 19, 40, 6, id="compact-L2"),
    pytest.param("compact", 3, 23, 51, 8, id="compact-L3"),
    pytest.param("compact", 4, 27, 76, 8, id="compact-L4"),
    pytest.param("full", 1, 19, 21, 6, id="full-L1"),
    pytest.param("full", 2, 23, 48, 6, id="full-L2"),
    pytest.param("full", 3, 27, 60, 8, id="full-L3"),
    pytest.param("full", 4, 31, 88, 8, id="full-L4"),
    pytest.param("full", 5, 37, 120, 8, id="full-L5"),
    pytest.param("full", 6, 41, 156, 8, id="full-L6"),
    pytest.param("full", 7, 45, 196, 8, id="full-L7"),
    pytest.param("full", 8, 49, 240, 8, id="full-L8"),
    pytest.param("full", 9, 53, 230, 10, id="full-L9"),
    pytest.param("full", 10, 57, 272, 10, id="full-L10"),
    pytest.param("full", 11, 61, 316, 10, id="full-L11"),
    pytest.param("full", 12, 67, 364, 10, id="full-L12"),
    pytest.param("full", 13, 71, 416, 10, id="full-L13"),
    pytest.param("full", 14, 75, 470, 10, id="full-L14"),
    pytest.param("full", 15, 79, 528, 10, id="full-L15"),
    pytest.param("full", 16, 83, 588, 10, id="full-L16"),
    pytest.param("full", 17, 87, 652, 10, id="full-L17"),
    pytest.param("full", 18, 91, 720, 10, id="full-L18"),
    pytest.param("full", 19, 95, 790, 10, id="full-L19"),
    pytest.param("full", 20, 101, 864, 10, id="full-L20"),
    pytest.param("full", 21, 105, 940, 10, id="full-L21"),
    pytest.param("full", 22, 109, 1020, 10, id="full-L22"),
    pytest.param("full", 23, 113, 920, 12, id="full-L23"),
    pytest.param("full", 24, 117, 992, 12, id="full-L24"),
    pytest.param("full", 25, 121, 1066, 12, id="full-L25"),
    pytest.param("full", 26, 125, 1144, 12, id="full-L26"),
    pytest.param("full", 27, 131, 1224, 12, id="full-L27"),
    pytest.param("full", 28, 135, 1306, 12, id="full-L28"),
    pytest.param("full", 29, 139, 1392, 12, id="full-L29"),
    pytest.param("full", 30, 143, 1480, 12, id="full-L30"),
    pytest.param("full", 31, 147, 1570, 12, id="full-L31"),
    pytest.param("full", 32, 151, 1664, 12, id="full-L32"),
]


@pytest.mark.parametrize(
    "kind, layers, expected_modules, expected_codewords, expected_bits",
    _SPEC_ROWS,
)
def test_symbol_attributes_match_spec(
    kind, layers, expected_modules, expected_codewords, expected_bits
):
    """``module_count``, ``total_codewords`` and ``codeword_bits`` agree with the spec."""
    assert module_count(kind, layers) == expected_modules
    assert total_codewords(kind, layers) == expected_codewords
    assert codeword_bits(kind, layers) == expected_bits


def test_total_bits_is_product():
    """``total_bits`` equals codeword count times codeword bit-width."""
    assert total_bits("compact", 1) == 17 * 6
    assert total_bits("full", 32) == 1664 * 12


def test_layer_range_constants():
    """Layer ranges cover 1..4 (compact) and 1..32 (full)."""
    assert list(COMPACT_LAYERS) == [1, 2, 3, 4]
    assert list(FULL_LAYERS) == list(range(1, 33))


@pytest.mark.parametrize(
    "kind, layers",
    [
        pytest.param("compact", 0, id="compact-L0"),
        pytest.param("compact", 5, id="compact-L5"),
        pytest.param("full", 0, id="full-L0"),
        pytest.param("full", 33, id="full-L33"),
        pytest.param("auto", 1, id="auto-L1"),
    ],
)
def test_invalid_kind_or_layers_raises(kind, layers):
    """Out-of-range layers or unknown kinds raise ``PyStrichInvalidOption``."""
    with pytest.raises(PyStrichInvalidOption):
        module_count(kind, layers)
