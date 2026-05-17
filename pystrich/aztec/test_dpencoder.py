"""Tests for the high-level encoder.

The "Code 2D!" worked example anchors the encoder: it should produce a
56-bit stream matching the spec's table-by-table encoding. Other cases
check specific transitions, digraph compression, byte-mode bracketing and
ECI emission.
"""

import pytest

from pystrich.aztec.dpencoder import encode_high_level


def _bits_to_str(bits: list[int]) -> str:
    return "".join(str(b) for b in bits)


def test_code_2d_excl_matches_spec_worked_example():
    """'Code 2D!' encodes to the 56-bit stream worked through in the spec.

    Path: C in Upper, Lower-Latch, o/d/e in Lower, Digit-Latch, SP/2 in Digit,
    Upper-Shift+D, Punct-Shift+! returning to Digit. Total 56 bits.
    """
    expected = (
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
    assert len(expected) == 56
    bits = encode_high_level(b"Code 2D!", eci=None)
    assert len(bits) == 56
    assert _bits_to_str(bits) == expected


@pytest.mark.parametrize(
    "payload, expected_bits",
    [
        pytest.param(b"A", "00010", id="A-upper-direct"),
        pytest.param(b"5", "11110" + "0111", id="digit-via-latch"),  # D/L + "5"
    ],
)
def test_single_char_encodings(payload, expected_bits):
    assert _bits_to_str(encode_high_level(payload)) == expected_bits


def test_byte_mode_for_high_byte():
    """A non-encodable byte (e.g. 0x80) forces Byte mode from Upper."""
    bits = encode_high_level(b"\x80")
    # B/S (31, 5 bits) + length (1, 5 bits) + byte (0x80, 8 bits) = 18 bits.
    assert len(bits) == 18
    expected = "11111" + "00001" + "10000000"
    assert _bits_to_str(bits) == expected


def test_byte_mode_splits_50_bytes_into_two_short_runs():
    """50 bytes of high-bit data: DP picks two short runs (25 + 25), one bit
    cheaper than the single extended-length encoding (21 + 8*50 = 421)."""
    payload = b"\x80" * 50
    bits = encode_high_level(payload)
    assert len(bits) == 2 * (5 + 5 + 25 * 8)


def test_byte_mode_uses_extended_length_for_long_unsplittable_run():
    """For 63 bytes the extended-length encoding wins; no 2-split fits in 31 each."""
    payload = b"\x80" * 63
    bits = encode_high_level(payload)
    # B/S (5) + length-prefix 0 (5) + extended length 63-31=32 (11) + 63*8 = 525 bits.
    assert len(bits) == 5 + 5 + 11 + 63 * 8


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param(b". ", id="period-space"),
        pytest.param(b", ", id="comma-space"),
        pytest.param(b": ", id="colon-space"),
        pytest.param(b"\r\n", id="CR-LF"),
    ],
)
def test_punct_digraph_compression(payload):
    """Each Punct digraph encodes as P/S (5) + 5-bit digraph value = 10 bits.

    Alternatives are longer: e.g. P/S + ``"."`` + space-in-Upper = 5+5+5 = 15 bits.
    """
    bits = encode_high_level(payload)
    assert len(bits) == 10


def test_lower_to_digit_via_d_latch_is_short():
    """'a1' encodes Lower-Latch + 'a' + Digit-Latch + '1'."""
    # L/L (5) + a (5) + D/L (5) + 1 (4) = 19 bits.
    bits = encode_high_level(b"a1")
    assert len(bits) == 19


@pytest.mark.parametrize(
    "eci, prologue_bits",
    [
        # FLG header is P/S (5) + FLG (5) + n (3) + n x Digit (4 each).
        pytest.param(3, 17, id="eci-3-one-digit"),
        pytest.param(26, 21, id="eci-26-two-digits"),
        pytest.param(123456, 37, id="eci-six-digits-upper-bound"),
    ],
)
def test_eci_emission_prepends_flg_sequence(eci, prologue_bits):
    """The FLG(n) prologue scales with the digit count, then encoding returns to Upper."""
    bits = encode_high_level(b"A", eci=eci)
    assert len(bits) == prologue_bits + 5  # +5 for 'A' in Upper after auto-return


def test_empty_payload():
    """Empty input yields no bits (no ECI)."""
    assert encode_high_level(b"") == []


def test_all_uppercase_run():
    """A run of uppercase letters stays in Upper with no transitions."""
    bits = encode_high_level(b"HELLO")
    assert len(bits) == 5 * 5  # 5 letters x 5 bits each


def test_long_digit_run_efficient():
    """A long digit run uses D/L + 4 bits per digit."""
    bits = encode_high_level(b"1234567890")
    # D/L (5) + 10 digits * 4 = 45 bits.
    assert len(bits) == 45


@pytest.mark.parametrize(
    "byte",
    [
        pytest.param(0x07, id="BEL-control-char"),
        pytest.param(0x40, id="at-sign"),
        pytest.param(0x5C, id="backslash"),
        pytest.param(0x7E, id="tilde"),
        pytest.param(0x7F, id="DEL"),
    ],
)
def test_mixed_mode_reaches_each_char_class(byte):
    """A Mixed-only character encodes via U/M latch + Mixed codeword = 10 bits.

    Liveness check across the four neighbourhoods of the Mixed table
    (control chars, ``@`` ``\\`` ``^`` ``_`` ``` ` ```, ``|`` ``~``, DEL).
    The Byte-mode alternative would cost 5 + 5 + 8 = 18 bits.
    """
    assert len(encode_high_level(bytes([byte]))) == 10


def test_embedded_digit_run_uses_latch_pair():
    """An embedded digit run wraps in U/D + D/U latches, not Byte mode."""
    # 3x5 (ABC) + 5 (U/D) + 3x4 (123) + 4 (D/U) + 3x5 (DEF) = 51 bits.
    # Byte-mode alternative for the digits would cost 5+5+24 = 34 vs the
    # latched 5+12+4 = 21 here.
    assert len(encode_high_level(b"ABC123DEF")) == 51


def test_multi_hop_latch_for_punct_run_after_upper():
    """A run of 3 Punct chars after Upper composes U/M + M/P, not 3 P/S shifts.

    No direct U/P latch exists. The only multi-char route into Punct is the
    two-hop path U->M->P, which the ``_close_latches`` fixed-point loop must
    find. Single P/S shifts win for 1-2 Punct chars; the latch path wins at 3+.
    """
    # 5 (A) + 5 (U/M) + 5 (M/P) + 3*5 (!!!) = 30 bits.
    # Three P/S shifts would cost 5 + 3*(5+5) = 35.
    assert len(encode_high_level(b"A!!!")) == 30
