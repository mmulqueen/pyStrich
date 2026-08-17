"""Tests for the Mode Message construction.

Anchors on the spec's worked example for "Code 2D!": the mode message for a
compact L1 symbol with 10 datawords is the nibble sequence
``[0, 9, 12, 2, 3, 1, 9]``. Other sizes are validated via the defining
property of a Reed-Solomon codeword — ``c(2^i) = 0`` at every generator
root — which is non-circular: it doesn't rely on this encoder's own output.
"""

import pytest

from pystrich.aztec.modemessage import build_mode_message
from pystrich.exceptions import PyStrichInvalidOption
from pystrich.reedsolomon import GF16_0x13


def _bits_to_nibbles(bits, count):
    return [sum(bits[i + j] << (3 - j) for j in range(4)) for i in range(0, count * 4, 4)]


def test_compact_l1_10_datawords_matches_spec_worked_example():
    """The 'Code 2D!' worked example produces this exact mode message."""
    bits = build_mode_message("compact", layers=1, data_codewords=10)
    assert len(bits) == 28
    assert _bits_to_nibbles(bits, 7) == [0, 9, 12, 2, 3, 1, 9]


def _eval_poly_gf16(coeffs, x):
    result = 0
    for c in coeffs:
        result = GF16_0x13.mul(result, x) ^ c
    return result


@pytest.mark.parametrize(
    "kind, layers, data_codewords, total_bits, total_nibbles, num_ec",
    [
        pytest.param("compact", 1, 10, 28, 7, 5, id="compact-L1-10dw"),
        pytest.param("compact", 1, 64, 28, 7, 5, id="compact-L1-max-dw"),
        pytest.param("compact", 4, 1, 28, 7, 5, id="compact-L4-1dw"),
        pytest.param("compact", 4, 50, 28, 7, 5, id="compact-L4-50dw"),
        pytest.param("full", 1, 1, 40, 10, 6, id="full-L1-1dw"),
        pytest.param("full", 1, 21, 40, 10, 6, id="full-L1-max-dw"),
        pytest.param("full", 22, 700, 40, 10, 6, id="full-L22-700dw"),
        pytest.param("full", 32, 1500, 40, 10, 6, id="full-L32-1500dw"),
    ],
)
def test_codeword_is_zero_at_generator_roots(
    kind, layers, data_codewords, total_bits, total_nibbles, num_ec
):
    """The packed codeword evaluates to zero at every generator root."""
    bits = build_mode_message(kind, layers=layers, data_codewords=data_codewords)
    assert len(bits) == total_bits
    nibbles = _bits_to_nibbles(bits, total_nibbles)
    for k in range(num_ec):
        root = GF16_0x13._exp[(1 + k) % (GF16_0x13.size - 1)]
        assert _eval_poly_gf16(nibbles, root) == 0, (
            f"codeword non-zero at root 2^{1 + k}={root} for {kind} L{layers} {data_codewords}dw"
        )


@pytest.mark.parametrize(
    "kind, layers, data_codewords",
    [
        pytest.param("compact", 0, 1, id="compact-L0"),
        pytest.param("compact", 5, 1, id="compact-L5"),
        pytest.param("compact", 1, 0, id="zero-datawords"),
        pytest.param("compact", 1, 65, id="compact-too-many-datawords"),
        pytest.param("full", 0, 1, id="full-L0"),
        pytest.param("full", 33, 1, id="full-L33"),
        pytest.param("full", 1, 2049, id="full-too-many-datawords"),
    ],
)
def test_invalid_inputs_raise(kind, layers, data_codewords):
    with pytest.raises(PyStrichInvalidOption):
        build_mode_message(kind, layers=layers, data_codewords=data_codewords)
