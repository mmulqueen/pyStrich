"""Aztec encoder roundtrip via zxing-cpp."""

from __future__ import annotations

import pytest

from pystrich.aztec import AZTEC_DEFAULT_QUIET_ZONE, AztecData, AztecEncoder
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
def test_ascii_roundtrip_compact(tmp_path, decode_barcode, text):
    encoder = AztecEncoder(text)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


def test_auto_encoding_picks_iso8859_1_for_latin1(tmp_path, decode_barcode):
    text = "café"  # 'é' is Latin-1.
    encoder = AztecEncoder(text)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


def test_auto_encoding_picks_utf8_for_unicode(tmp_path, decode_barcode):
    text = "日本語"
    encoder = AztecEncoder(text)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


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


def test_custom_quiet_zone_roundtrips(tmp_path, decode_barcode):
    """A wider quiet zone does not break decoding."""
    text = "Code 2D!"
    encoder = AztecEncoder(text, quiet_zone=6)
    path = tmp_path / "aztec.png"
    encoder.save(path, cellsize=8)
    assert decode_barcode(path) == text


def test_aztec_smudge_tolerance(tmp_path, decode_barcode):
    """The smudged Aztec rendered for ``docs/printing.rst`` still decodes."""
    from pystrich._simulate_damage import aztec_smudge_demo

    text = "https://github.com/mmulqueen/pyStrich"
    path = tmp_path / "aztec-damaged.png"
    aztec_smudge_demo(text).save(path)
    assert decode_barcode(path) == text
