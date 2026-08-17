"""Tests for the bit-stuffing codeword chunker.

Aztec forbids codewords of all-zeros or all-ones (they're treated as
erasures during decoding). When the first ``width - 1`` bits of a candidate
codeword are all 0, a dummy 1 is inserted at the LSB; when they're all 1, a
dummy 0 is inserted. The displaced bit pushes back into the stream. The
final partial codeword is padded with 1s; if that produces an all-1 value,
the LSB flips to 0.
"""

import pytest

from pystrich.aztec.bitstuff import to_codewords


@pytest.mark.parametrize("width", [6, 8, 10, 12])
def test_empty_input_returns_no_codewords(width):
    assert to_codewords([], width) == []


@pytest.mark.parametrize(
    "bits, width, expected",
    [
        pytest.param([1, 0, 0, 0, 0, 0], 6, [0b100000], id="width6-single"),
        pytest.param(
            [1, 0, 1, 0, 1, 0, 0, 0, 1, 1, 1, 1], 6, [0b101010, 0b001111], id="width6-two"
        ),
        pytest.param([1, 0, 0, 1, 0, 0, 1, 0], 8, [0b10010010], id="width8-single"),
        pytest.param([1, 1, 1, 1, 0, 0, 0, 0, 1, 0], 10, [0b1111000010], id="width10-single"),
        pytest.param(
            [1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 0], 12, [0b100110000010], id="width12-single"
        ),
    ],
)
def test_normal_chunks_have_no_stuffing(bits, width, expected):
    assert to_codewords(bits, width) == expected


def test_all_zero_prefix_stuffs_one():
    """First width-1 zeros trigger a dummy 1 at the LSB; the next bit starts the next codeword."""
    # 6 zeros at width 6: first 5 → stuff a 1 (codeword = 0b000001 = 1).
    # 6th zero starts next codeword; padded with 5 ones → 0b011111 = 31.
    assert to_codewords([0] * 6, 6) == [0b000001, 0b011111]


def test_all_one_prefix_stuffs_zero():
    """First width-1 ones trigger a dummy 0 at the LSB; the next bit starts the next codeword."""
    # 6 ones at width 6: first 5 → stuff a 0 (codeword = 0b111110 = 62).
    # 6th one starts the next codeword; padded with 5 ones → all-1 → escape → 62.
    assert to_codewords([1] * 6, 6) == [62, 62]


def test_final_codeword_pads_with_ones():
    """A final partial codeword is right-padded with 1s."""
    # 3 bits at width 6: [1, 0, 1] padded with [1, 1, 1] → 0b101111 = 47.
    assert to_codewords([1, 0, 1], 6) == [0b101111]


def test_final_codeword_all_ones_escapes():
    """A final partial codeword that would pad to all-1s flips its LSB to 0."""
    # Single 1 at width 6: pad → [1,1,1,1,1,1] = 63 (all-1) → escape → 62.
    assert to_codewords([1], 6) == [62]


@pytest.mark.parametrize("width", [6, 8, 10, 12])
def test_no_output_codeword_is_all_zero(width):
    """Across a sweep of inputs, no codeword is ever all-zero (forbidden value)."""
    # Adversarial inputs likely to expose mistakes: long runs of zeros at
    # various offsets.
    cases = [
        [0] * width,
        [0] * (width - 1) + [1, 1, 1, 1, 1, 1, 1, 1],
        [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1],
        [0, 0, 1] * 6,
    ]
    forbidden = 0
    for bits in cases:
        for cw in to_codewords(bits, width):
            assert cw != forbidden, f"all-zero codeword for input {bits} at width {width}"


@pytest.mark.parametrize("width", [6, 8, 10, 12])
def test_no_output_codeword_is_all_ones(width):
    """Across a sweep of inputs, no codeword is ever all-1s (forbidden value)."""
    forbidden = (1 << width) - 1
    cases = [
        [1] * width,
        [1] * (width - 1) + [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0],
        [1, 1, 0] * 6,
    ]
    for bits in cases:
        for cw in to_codewords(bits, width):
            assert cw != forbidden, f"all-1 codeword for input {bits} at width {width}"


@pytest.mark.parametrize("width", [6, 8, 10, 12])
def test_all_zero_run_at_width_minus_one_does_not_eat_following_one(width):
    """The bit displaced by stuffing must end up in the next codeword, not be lost.

    With width-1 zeros followed by a 1, the stuffed codeword is all-zeros + dummy-1,
    and the trailing 1 starts the next codeword.
    """
    bits = [0] * (width - 1) + [1]
    result = to_codewords(bits, width)
    # First codeword is the stuffed [0]*(width-1) + [1] = 1
    assert result[0] == 1
    # Second codeword starts with that pushed-back 1, then pads with 1s -> all-1 → escape
    assert result[1] == (1 << width) - 2


def test_codewords_pack_msb_first():
    """Bit 0 of the input is the MSB of the first codeword."""
    # [1,0,1,1,0,0] at width 6 → MSB=1, then 0, 1, 1, 0, 0 → 0b101100 = 44.
    assert to_codewords([1, 0, 1, 1, 0, 0], 6) == [0b101100]


def test_code_2d_excl_matches_spec_worked_example():
    """The spec's 56-bit stream chunks into the spec's 10 codewords.

    The dummy bits the spec calls out (after the all-zero prefix in cw#3
    and after the all-zero prefix in cw#9) are produced by the stuffing
    rule; the trailing two 1s pad the final partial codeword.
    """
    bits = [
        int(b)
        for b in (
            "00100"
            + "11100"
            + "10000"
            + "00101"
            + "00110"
            + "11110"
            + "0001"
            + "0100"
            + "1111"
            + "00101"
            + "0000"
            + "00110"
        )
    ]
    assert len(bits) == 56
    expected = [9, 50, 1, 41, 47, 2, 39, 37, 1, 27]
    assert to_codewords(bits, 6) == expected
