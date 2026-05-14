"""Tests for the PDF417 high-level encoding pipeline.

These tests cover, in order of dependency:

1. The three compaction modes against their worked examples in the spec.
2. The greedy mode-switching that chooses between modes.
3. The top-level :func:`encode` pipeline against the spec's full worked
   codeword example, including the SLD, padding, and Reed-Solomon steps.
4. An algebraic roundtrip: any encoded stream satisfies the defining
   Reed-Solomon equation, regardless of the input text.
"""

from __future__ import annotations

import pytest

from pystrich.exceptions import PyStrichInvalidInput
from pystrich.pdf417 import textencoder
from pystrich.pdf417.tables import (
    LATCH_BYTE,
    LATCH_BYTE_MULT6,
    LATCH_NUMERIC,
    LATCH_TEXT,
    SUB_ALPHA,
    SUB_MIXED,
)
from pystrich.pdf417.textencoder import (
    PAD_CODEWORD,
    _byte_compact,
    _compact,
    _numeric_compact,
    _text_compact,
    encode,
)


def test_text_compact_pdf417_example_matches_spec_worked_example():
    """Spec example: 'PDF417' encodes to codewords [453, 178, 121, 239].

    Base-30 sequence: P(15) D(3) F(5) ml(28) 4(4) 1(1) 7(7) ps(29 pad).
    Pairs combine as h*30 + l: (15,3)=453, (5,28)=178, (4,1)=121, (7,29)=239.
    """
    cws, ending = _text_compact("PDF417", start_submode=SUB_ALPHA)
    assert cws == [453, 178, 121, 239]
    # The ml latch in the middle leaves the encoder in Mixed sub-mode.
    assert ending == SUB_MIXED


def test_text_compact_single_char_pads_to_even():
    """A single character produces one codeword: value*30 + 29 (ps pad)."""
    cws, _ = _text_compact("A", start_submode=SUB_ALPHA)
    assert cws == [0 * 30 + 29]


def test_text_compact_alpha_to_lower_uses_latch():
    """'Ab' switches Alpha to Lower via the ll latch (slot 27)."""
    cws, ending = _text_compact("Ab", start_submode=SUB_ALPHA)
    # Base-30 stream: A(0), ll(27), b(1), pad ps(29). Codewords: 27, 59.
    assert cws == [0 * 30 + 27, 1 * 30 + 29]
    assert ending == "lower"


def test_text_compact_punctuation_via_shift():
    """'A?B' uses a ps shift from Alpha for one Punctuation character then reverts."""
    cws, ending = _text_compact("A?B", start_submode=SUB_ALPHA)
    # Base-30 stream: A(0), ps(29), ?(25), B(1). Codewords: (0,29)=29, (25,1)=751.
    assert cws == [0 * 30 + 29, 25 * 30 + 1]
    assert ending == SUB_ALPHA


def test_numeric_compact_spec_worked_example():
    """Spec example: '000213298174000' compacts to [1, 624, 434, 632, 282, 200]."""
    assert _numeric_compact("000213298174000") == [1, 624, 434, 632, 282, 200]


def test_numeric_compact_44_digits_yields_15_codewords():
    """A full 44-digit group compacts to exactly 15 codewords."""
    cws = _numeric_compact("1" * 44)
    assert len(cws) == 15


def test_numeric_compact_splits_long_runs_into_44_digit_groups():
    """A 60-digit input becomes two groups (44 + 16) encoded back to back."""
    cws = _numeric_compact("1" * 60)
    expected = _numeric_compact("1" * 44) + _numeric_compact("1" * 16)
    assert cws == expected


def test_byte_compact_spec_worked_example():
    """Spec example: bytes (231,101,11,97,205,2) compact to [387, 700, 208, 213, 302]."""
    data = bytes([231, 101, 11, 97, 205, 2])
    assert _byte_compact(data) == [387, 700, 208, 213, 302]


def test_byte_compact_trailing_bytes_emitted_one_per_codeword():
    """When length isn't a multiple of 6, leftover bytes are one byte per codeword."""
    data = bytes([231, 101, 11, 97, 205, 2, 42, 200])  # one full group + 2 trailing
    cws = _byte_compact(data)
    assert cws == [387, 700, 208, 213, 302, 42, 200]


def test_compact_stays_in_text_when_digits_are_few():
    """Twelve digits or fewer encode in Text/Mixed; no Numeric latch is emitted."""
    cws = _compact("ABC123456789012")  # 3 letters + 12 digits
    assert LATCH_NUMERIC not in cws


def test_compact_switches_to_numeric_for_long_digit_runs():
    """A run of 13 or more digits triggers a Numeric latch (902)."""
    cws = _compact("ABC1234567890123")  # 3 letters + 13 digits
    assert LATCH_NUMERIC in cws


def test_compact_switches_to_byte_for_non_text_characters():
    """Characters Text Compaction can't represent trigger Byte mode."""
    cws = _compact("ABC\x80\x81")
    assert LATCH_BYTE in cws or LATCH_BYTE_MULT6 in cws


def test_compact_uses_mult6_latch_when_byte_run_is_multiple_of_six():
    """Byte runs of length divisible by 6 use the 924 latch, not 901."""
    cws = _compact("\x80\x81\x82\x83\x84\x85")
    assert LATCH_BYTE_MULT6 in cws
    assert LATCH_BYTE not in cws


def test_compact_returns_back_to_text_after_byte_run():
    """A latch back to Text mode (900) appears after a byte run preceding text."""
    cws = _compact("ABC\x80\x81DEF")
    assert LATCH_TEXT in cws


def test_compact_promotes_non_latin1_to_utf8():
    """A plain ``str`` containing non-Latin-1 auto-promotes to UTF-8 with an ECI prefix."""
    from pystrich.pdf417.tables import ECI_SMALL

    cws = _compact("™")
    # First two codewords are the ECI prefix: 927 (small ECI) + 26 (UTF-8).
    assert cws[0] == ECI_SMALL
    assert cws[1] == 26


def test_compact_rejects_non_ascii_when_pinned_to_ascii():
    """An explicit ``encoding='ascii'`` pin raises on non-ASCII input."""
    from pystrich.pdf417 import PDF417Data

    with pytest.raises(PyStrichInvalidInput, match="ASCII"):
        PDF417Data("™", encoding="ascii")


def test_encode_spec_worked_example():
    """Spec worked example: 'PDF417' at ECL 1, columns 3 produces the full stream."""
    cws = encode("PDF417", ecl=1, columns=3)
    assert cws == [5, 453, 178, 121, 239, 452, 327, 657, 619]


def test_encode_sld_equals_data_codeword_count():
    """The Symbol Length Descriptor equals ``n = c*r - k``."""
    cws = encode("PDF417", ecl=1, columns=3)
    n = cws[0]
    k = 4  # 2 ** (1 + 1)
    rows = len(cws) // 3
    assert n == 3 * rows - k


def test_encode_pads_with_900_when_data_short_of_capacity():
    """When ``c*r - k`` exceeds ``m + 1``, the difference is filled with 900s."""
    cws = encode("AB", ecl=0, columns=2)  # one source codeword, two EC codewords
    # Pad codewords sit between the source data and the EC tail.
    assert PAD_CODEWORD in cws[1:-2]


def test_encode_rejects_data_exceeding_chosen_symbol_size():
    """If the data needs more rows than ``columns`` allows, encoding errors out."""
    with pytest.raises(PyStrichInvalidInput, match="max 90"):
        encode("A" * 2000, ecl=0, columns=1)


def test_encode_auto_sizes_when_columns_omitted():
    """Without an explicit ``columns``, the result still factors as a valid c x r stream."""
    cws = encode("Hello, World!", ecl=2)
    n = len(cws)
    assert any(1 <= c <= 30 and 3 <= n // c <= 90 and c * (n // c) == n for c in range(1, 31))


@pytest.mark.parametrize("total_codewords", [13, 30, 92, 200, 500, 928])
def test_auto_columns_yields_roughly_square_symbol(total_codewords):
    """``_auto_columns`` picks ``c`` close to the closed-form for a square symbol.

    For ``c`` data columns and a row count near ``total_codewords / c``, the
    rendered width in modules is ``17 c + 69`` and the rendered height at
    the default ``row_height=3`` is ``3 * total_codewords / c``. Setting
    these equal gives the closed-form ``c`` -- the picked column count
    should land within one of that ideal.
    """
    c = textencoder._auto_columns(total_codewords)
    width = 17 * c + 69
    height = 3 * total_codewords / c
    # The ideal column count puts width = height. Anything that turns the
    # symbol into a long strip (aspect > 4 in either direction) means the
    # quadratic was solved wrong.
    assert 0.25 <= width / height <= 4


@pytest.mark.parametrize(
    "text, ecl, columns",
    [
        ("PDF417", 1, 3),
        ("Hello, World!", 2, 6),
        ("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdef", 3, 8),
        ("1234567890" * 10, 4, 10),
    ],
)
def test_encoded_codeword_polynomial_is_zero_at_generator_roots(text, ecl, columns):
    """Every encoded stream is divisible by the Reed-Solomon generator.

    This is the defining Reed-Solomon property: independent of how the
    encoder produced the EC bytes, the codeword polynomial evaluates to
    zero at every root of the generator. Catches both compaction errors
    that mutate the data and RS bugs that produce non-orthogonal EC.
    """
    cws = encode(text, ecl=ecl, columns=columns)
    k = 2 ** (ecl + 1)
    for j in range(1, k + 1):
        root = pow(3, j, 929)
        acc = 0
        for c in cws:
            acc = (acc * root + c) % 929
        assert acc == 0, f"non-zero at root 3^{j}={root} for ECL{ecl}/{text!r}"


def test_pick_rows_rejects_columns_out_of_range():
    """Columns outside 1..30 are rejected before sizing."""
    with pytest.raises(PyStrichInvalidInput, match=r"1\.\.30"):
        textencoder._pick_rows(source_count=10, ecl=0, columns=0)
    with pytest.raises(PyStrichInvalidInput, match=r"1\.\.30"):
        textencoder._pick_rows(source_count=10, ecl=0, columns=31)


def test_pick_rows_clamps_to_minimum_three():
    """The spec requires at least 3 rows even for tiny payloads."""
    assert textencoder._pick_rows(source_count=0, ecl=0, columns=10) == 3
