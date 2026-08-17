"""End-to-end roundtrip tests for the PDF417 encoder.

Encodes a string, renders it to a PNG, then decodes that PNG via the
shared ``decode_barcode`` fixture (zxing-cpp). The decoded payload must
match the input exactly. This exercises every part of the pipeline --
compaction, error correction, layout and rendering -- against a real
decoder, catching mistakes pure unit tests can miss (an off-by-one in
the row indicator formulas, for example).
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pystrich.exceptions import PyStrichInvalidInput
from pystrich.pdf417 import PDF417Encoder
from pystrich.pdf417.tables import ec_codeword_count
from pystrich.pdf417.textencoder import (
    NUMERIC_RUN_THRESHOLD,
    _compact,
    _max_rows,
    _numeric_compact,
)


def _save(text: str, tmp_path, **kwargs) -> str:
    out = tmp_path / "p417.png"
    PDF417Encoder(text, **kwargs).save(str(out), cellsize=4)
    return str(out)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("PDF417", id="text-mixed-submode"),
        pytest.param("Hello, World!", id="text-with-punctuation"),
        pytest.param("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", id="alpha-and-lower"),
        pytest.param("1234567890" * 5, id="numeric-long-run"),
        pytest.param("abc\x80\x81\x82\x83\x84\x85def", id="byte-mult6"),
        pytest.param("abc\x80def", id="byte-single"),
        pytest.param("Mixed: ABC 123 def 4567890123456789012345 end.", id="mixed-mode-switching"),
    ],
)
@pytest.mark.png
def test_roundtrip_decodes_to_input(tmp_path, text, decode_barcode):
    """Every compaction mode roundtrips through encoder, renderer and scanner."""
    assert decode_barcode(_save(text, tmp_path)) == text


@pytest.mark.parametrize("ecl", [0, 1, 2, 3, 4, 5])
@pytest.mark.png
def test_roundtrip_at_every_ecl_decodes_correctly(tmp_path, ecl, decode_barcode):
    """All error correction levels produce decodable symbols on clean renders."""
    text = "the quick brown fox jumps over the lazy dog"
    assert decode_barcode(_save(text, tmp_path, ecl=ecl)) == text


@pytest.mark.parametrize("columns", [1, 3, 6, 10, 20, 30])
@pytest.mark.png
def test_roundtrip_at_various_column_counts(tmp_path, columns, decode_barcode):
    """Different column counts produce decodable symbols."""
    text = "abcdef0123456789"
    assert decode_barcode(_save(text, tmp_path, columns=columns)) == text


@pytest.mark.parametrize("row_height", [2, 3, 4, 6])
@pytest.mark.png
def test_roundtrip_at_various_row_heights(tmp_path, row_height, decode_barcode):
    """Above the spec minimum Y/X >= 2 the symbol decodes; row_height=3 is the default."""
    text = "PDF417 row-height test"
    assert decode_barcode(_save(text, tmp_path, row_height=row_height)) == text


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Ich dachte, Sie wären kräftiger", id="latin1"),
        # Short high-byte payloads gave zxing's charset heuristics nothing to
        # work with before the explicit ECI designator was emitted.
        pytest.param("¡", id="latin1-short"),
        pytest.param("€5 親切にしろ 🐻‍❄️", id="utf8-mixed"),
    ],
)
@pytest.mark.png
def test_roundtrip_non_ascii_decodes_via_eci(tmp_path, text, decode_barcode):
    """Non-ASCII payloads roundtrip via the appropriate character interpretation.

    Latin-1 input emits codeword 927 + 3 (ECI 000003) and UTF-8 input
    927 + 26 (ECI 000026) once at the start of the symbol. zxing-cpp
    picks up both automatically.
    """
    assert decode_barcode(_save(text, tmp_path)) == text


@st.composite
def _pdf417_payload(draw):
    parts = draw(
        st.lists(
            st.one_of(
                st.text(alphabet="0123456789", min_size=1, max_size=8),
                # Runs past the threshold latch Numeric Compaction.
                st.text(alphabet="0123456789", min_size=13, max_size=20),
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=8),
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
                # Mixed and Punctuation sub-mode bands.
                st.text(alphabet="&\r\t,:#-.$/+%*=^ ", min_size=1, max_size=4),
                st.text(alphabet=";<>@[\\]_`~!\n|(){}'\"", min_size=1, max_size=4),
                # 0xA0+ skips the C1 control block (0x80-0x9F).
                st.text(
                    st.characters(min_codepoint=0xA0, max_codepoint=0xFF),
                    min_size=1,
                    max_size=4,
                ),
                st.text(
                    st.characters(
                        min_codepoint=0x0100,
                        max_codepoint=0x2FFF,
                        exclude_categories=("Cs", "Cc"),
                    ),
                    min_size=1,
                    max_size=4,
                ),
            ),
            min_size=1,
            max_size=6,
        )
    )
    return "".join(parts)


@given(
    text=_pdf417_payload(),
    ecl=st.sampled_from([None, 0, 1, 2, 3, 4, 5]),
    columns=st.sampled_from([None, 2, 10, 30]),
)
@settings(
    max_examples=100,
    deadline=timedelta(seconds=2),
    print_blob=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.png
def test_property_roundtrip(text, ecl, columns, tmp_path, decode_barcode):
    """Class-banded payloads roundtrip through encode + render + decode."""
    assert decode_barcode(_save(text, tmp_path, ecl=ecl, columns=columns)) == text


# (columns, rows, ecl) combos with room for at least a few data codewords,
# within the format's 928-codeword total. Rows are not pinnable through the
# API, so payloads are sized to make the encoder pick them.
_BOUNDARY_COMBOS = [
    (columns, rows, ecl)
    for columns in (1, 2, 3, 5, 10, 30)
    for rows in (3, 5, 10, 20, 90)
    for ecl in range(9)
    if rows <= _max_rows(columns) and columns * rows - ec_codeword_count(ecl) - 1 >= 4
]

# Smallest digit count whose Numeric Compaction cost is each codeword count,
# derived from the encoder's own arithmetic (descending, so the smallest
# digit count wins each cost).
_DIGITS_FOR_NUMERIC_COST = {
    len(_numeric_compact("0" * digits)): digits for digits in range(44, 0, -1)
}


@st.composite
def _boundary_payload(draw):
    """Single-mode filler constructed to land the source codeword stream on
    or within two codewords of a (columns, rows, ecl) capacity, sweeping the
    padding and row-count edges that uniformly random payloads rarely reach.

    Returns ``(text, columns, ecl, target, fits)``; ``fits`` is whether the
    payload still fits any symbol at the pinned columns.
    """
    columns, rows, ecl = draw(st.sampled_from(_BOUNDARY_COMBOS))
    target = columns * rows - ec_codeword_count(ecl) - 1 + draw(st.integers(-2, 2))
    fits = target <= columns * _max_rows(columns) - ec_codeword_count(ecl) - 1
    arm = draw(st.sampled_from(["upper", "digits", "bytes"]))
    if arm == "digits":
        # Numeric mode: latch + 15 codewords per full 44-digit group.
        full_groups, rem = divmod(target - 1, 15)
        digits = 44 * full_groups + (_DIGITS_FOR_NUMERIC_COST[rem] if rem else 0)
        if digits >= NUMERIC_RUN_THRESHOLD:
            return "0" * digits, columns, ecl, target, fits
        arm = "upper"  # too short to latch Numeric; Text-mode costs differ
    if arm == "bytes" and target >= 4:
        # Byte mode: ECI 3 prefix + latch + 5 codewords per 6-byte group +
        # 1 per leftover.
        full_groups, rem = divmod(target - 3, 5)
        return "\x80" * (6 * full_groups + rem), columns, ecl, target, fits
    # Text mode, Alpha sub-mode: two characters per codeword, no latch.
    return "A" * (2 * target - draw(st.integers(0, 1))), columns, ecl, target, fits


@given(payload=_boundary_payload())
@settings(
    max_examples=300,
    deadline=timedelta(seconds=2),
    print_blob=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.png
def test_property_roundtrip_capacity_boundaries(payload, tmp_path, decode_barcode):
    """Boundary-biased payloads roundtrip at pinned columns and error level;
    draws past the row limit must overflow cleanly instead."""
    text, columns, ecl, _, fits = payload
    try:
        path = _save(text, tmp_path, columns=columns, ecl=ecl)
    except PyStrichInvalidInput:
        assert not fits
        return
    assert decode_barcode(path) == text


@given(payload=_boundary_payload())
@settings(max_examples=300, deadline=timedelta(seconds=2), print_blob=True)
def test_boundary_payloads_hit_their_target(payload):
    """Guards the strategy's cost model: if the compactor drifts, the sweep
    would otherwise silently stop reaching the capacity edges."""
    text, _, _, target, _ = payload
    assert len(_compact(text)) == target


def test_payload_past_symbol_limit_raises():
    """A payload needing more than 928 total codewords fits no symbol."""
    with pytest.raises(PyStrichInvalidInput):
        PDF417Encoder("A" * 2000)
