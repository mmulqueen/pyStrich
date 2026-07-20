"""Aztec encoder roundtrip via zxing-cpp."""

from __future__ import annotations

from datetime import timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pystrich.aztec import AZTEC_DEFAULT_QUIET_ZONE, AztecData, AztecEncoder
from pystrich.aztec.dpencoder import encode_high_level
from pystrich.aztec.modemessage import max_data_codewords
from pystrich.aztec.symbol import codeword_bits, total_codewords
from pystrich.aztec.textencoder import TextEncoder, _min_ec_needed
from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Hello", id="ascii-short"),
        pytest.param("HELLO WORLD", id="ascii-letters-spaces"),
        pytest.param("Code 2D!", id="spec-example"),
        pytest.param("https://github.com/mmulqueen/pyStrich", id="github-url"),
        pytest.param("5050070007664", id="digits-only"),
    ],
)
@pytest.mark.png
def test_ascii_roundtrip_compact(tmp_path, decode_barcode, text):
    encoder = AztecEncoder(text)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


@pytest.mark.png
def test_auto_encoding_picks_iso8859_1_for_latin1(tmp_path, decode_barcode):
    text = "café"  # 'é' is Latin-1.
    encoder = AztecEncoder(text)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


@pytest.mark.png
def test_auto_encoding_picks_utf8_for_unicode(tmp_path, decode_barcode):
    text = "日本語"
    encoder = AztecEncoder(text)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


@pytest.mark.png
def test_explicit_ascii_data_class(tmp_path, decode_barcode):
    data = AztecData("Plain ASCII", encoding="ascii")
    encoder = AztecEncoder(data)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == "Plain ASCII"


@pytest.mark.parametrize(
    "ecc",
    [
        pytest.param(5, id="ecc-5"),
        pytest.param(23, id="ecc-23-default"),
        pytest.param(50, id="ecc-50"),
        pytest.param(95, id="ecc-95"),
    ],
)
@pytest.mark.png
def test_ecc_levels_roundtrip(tmp_path, decode_barcode, ecc):
    text = "Code 2D!"
    encoder = AztecEncoder(text, ecc=ecc)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


@pytest.mark.parametrize(
    "kind, layers",
    [
        pytest.param("compact", 1, id="compact-L1"),
        pytest.param("compact", 2, id="compact-L2"),
        pytest.param("compact", 3, id="compact-L3"),
        pytest.param("compact", 4, id="compact-L4"),
        pytest.param("full", 1, id="full-L1"),
        pytest.param("full", 5, id="full-L5"),
        pytest.param("full", 10, id="full-L10"),
    ],
)
@pytest.mark.png
def test_explicit_size_roundtrip(tmp_path, decode_barcode, kind, layers):
    # Use a short payload so it fits the smallest symbols at the default ECC.
    text = "Hi!"
    encoder = AztecEncoder(text, symbol_kind=kind, layers=layers)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


# Validation


def test_ecc_below_range_raises():
    with pytest.raises(PyStrichInvalidOption, match="ecc"):
        AztecEncoder("hello", ecc=4)


def test_ecc_above_range_raises():
    with pytest.raises(PyStrichInvalidOption, match="ecc"):
        AztecEncoder("hello", ecc=96)


def test_layers_without_kind_raises():
    with pytest.raises(PyStrichInvalidOption, match="symbol_kind"):
        AztecEncoder("hello", layers=1)


def test_layers_out_of_range_raises():
    with pytest.raises(PyStrichInvalidOption):
        AztecEncoder("hello", symbol_kind="compact", layers=99)


def test_payload_too_large_for_fixed_size_raises():
    with pytest.raises(PyStrichInvalidInput, match="capacity"):
        AztecEncoder("X" * 1000, symbol_kind="compact", layers=1)


def test_str_input_uses_auto_encoding():
    """A bare str passed to AztecEncoder is wrapped in AztecData(auto_encoding=True)."""
    assert AztecEncoder("café").matrix == AztecEncoder(AztecData("café", auto_encoding=True)).matrix


def test_default_quiet_zone_adds_two_module_border():
    """The renderer wraps the matrix in a 2-module quiet zone by default."""
    encoder = AztecEncoder("Hello")  # compact L1 -> 15x15 matrix
    renderer = encoder.init_renderer()
    assert renderer.width == 15 + 2 * AZTEC_DEFAULT_QUIET_ZONE
    assert renderer.height == 15 + 2 * AZTEC_DEFAULT_QUIET_ZONE


@pytest.mark.parametrize("quiet_zone", [0, 5])
def test_custom_quiet_zone_resizes_rendered_matrix(quiet_zone):
    """Passing ``quiet_zone=`` overrides the default border width."""
    encoder = AztecEncoder("Hello", quiet_zone=quiet_zone)
    renderer = encoder.init_renderer()
    assert renderer.width == 15 + 2 * quiet_zone


@pytest.mark.png
def test_custom_quiet_zone_roundtrips(tmp_path, decode_barcode):
    """A wider quiet zone does not break decoding."""
    text = "Code 2D!"
    encoder = AztecEncoder(text, quiet_zone=6)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


@st.composite
def _aztec_payload(draw):
    parts = draw(
        st.lists(
            st.one_of(
                st.text(alphabet="0123456789", min_size=1, max_size=8),
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=8),
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
                st.text(alphabet=" .,-+/:;!?", min_size=1, max_size=4),
                st.sampled_from([". ", ", ", ": ", "\r\n"]),
                st.text(alphabet="\\@^_`{|}~", min_size=1, max_size=4),
                st.text(alphabet="\t\n\r", min_size=1, max_size=2),
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


@given(text=_aztec_payload(), ecc=st.sampled_from([5, 23, 50, 95]))
@settings(
    max_examples=100,
    deadline=timedelta(seconds=2),
    print_blob=True,
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.data_too_large,
        HealthCheck.filter_too_much,
    ],
)
@pytest.mark.png
def test_property_roundtrip(text, ecc, tmp_path, decode_barcode):
    """Class-banded payloads roundtrip through encode + render + decode."""
    path = tmp_path / "aztec-property.png"
    AztecEncoder(text, ecc=ecc).save(path, cellsize=8)
    assert decode_barcode(path) == text


# Compact symbols, the smaller full-range symbols, and full L23 -- the first
# 12-bit-codeword symbol, otherwise unreached by any test. Combos where the
# ECC percentage leaves no room for data are dropped.
_BOUNDARY_SYMBOLS = [("compact", n) for n in range(1, 5)] + [
    ("full", n) for n in (*range(1, 13), 23)
]
_BOUNDARY_COMBOS = [
    (kind, layers, ecc)
    for kind, layers in _BOUNDARY_SYMBOLS
    for ecc in (5, 23, 50, 95)
    if total_codewords(kind, layers) - _min_ec_needed(total_codewords(kind, layers), ecc) >= 1
]


@st.composite
def _boundary_payload(draw):
    """Single-mode filler sized to land the bit stream within two characters
    of a symbol's data capacity at the drawn ECC percentage, sweeping the
    padding and layer-selection edges that uniformly random payloads rarely
    reach.

    Returns ``(text, ecc, kind, layers, fits)``; ``fits`` is whether the
    payload still fits the drawn symbol.
    """
    kind, layers, ecc = draw(st.sampled_from(_BOUNDARY_COMBOS))
    total = total_codewords(kind, layers)
    capacity_cw = min(total - _min_ec_needed(total, ecc), max_data_codewords(kind))
    capacity_bits = capacity_cw * codeword_bits(kind, layers)
    if draw(st.booleans()):
        # Digit mode: 5-bit latch from Upper, then 4 bits per digit.
        n0 = (capacity_bits - 5) // 4
        char = "0"
    else:
        # Upper mode: 5 bits per character, no latch.
        n0 = capacity_bits // 5
        char = "A"
    n = max(1, n0 + draw(st.integers(-2, 2)))
    return char * n, ecc, kind, layers, n <= n0


@given(payload=_boundary_payload())
@settings(
    max_examples=300,
    deadline=timedelta(seconds=2),
    print_blob=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.png
def test_property_roundtrip_capacity_boundaries(payload, tmp_path, decode_barcode):
    """Boundary-biased payloads roundtrip under auto symbol selection."""
    text, ecc, _, _, _ = payload
    path = tmp_path / "aztec-boundary.png"
    AztecEncoder(text, ecc=ecc).save(path, cellsize=4)
    assert decode_barcode(path) == text


@given(payload=_boundary_payload())
@settings(max_examples=300, deadline=timedelta(seconds=2), print_blob=True)
def test_boundary_payloads_fill_their_target(payload):
    """Guards the strategy's bit arithmetic on pinned symbols: an in-capacity
    payload must fit and a just-over payload must overflow cleanly. If the
    encoder's cost model drifts, this fails instead of the sweeps silently
    going blunt. Exercises size selection only, skipping the Reed-Solomon
    and matrix-placement work the assertion never inspects."""
    text, ecc, kind, layers, fits = payload
    bits = encode_high_level(text.encode("ascii"), eci=None)
    if fits:
        chosen = TextEncoder()._choose_size(bits, ecc, kind, layers)
        assert chosen[:2] == (kind, layers)
    else:
        with pytest.raises(PyStrichInvalidInput, match="capacity"):
            TextEncoder()._choose_size(bits, ecc, kind, layers)


def test_low_ecc_compact_payload_respects_mode_message_cap():
    """Data that fits compact L4's codeword budget but not the 64 data
    codewords its mode message can describe selects the next symbol."""
    AztecEncoder("0" * 130, ecc=5)


@pytest.mark.png
def test_aztec_smudge_tolerance(tmp_path, decode_barcode):
    """The smudged Aztec rendered for ``docs/printing.rst`` still decodes."""
    from pystrich._simulate_damage import aztec_smudge_demo

    text = "https://github.com/mmulqueen/pyStrich"
    path = tmp_path / "aztec-damaged.png"
    aztec_smudge_demo(text).save(path)
    assert decode_barcode(path) == text
