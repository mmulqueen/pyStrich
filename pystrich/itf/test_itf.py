"""Unit tests for the Interleaved 2 of 5 / ITF-14 barcode encoders."""

import pytest

from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption
from pystrich.itf import ITF14Encoder, ITFEncoder
from pystrich.itf.encoding import encode_digits


@pytest.mark.parametrize(
    "code, check_digit",
    [
        ("1540141453698", 7),
        ("0000000000000", 0),
        ("0012345678905", 0),
        ("9780201379624", 8),
        ("1111111111111", 3),
    ],
)
def test_check_digit(code, check_digit):
    encoder = ITF14Encoder(code)
    assert encoder.check_digit == check_digit
    assert encoder.full_code == code + str(check_digit)


def test_14_digit_input_recomputes_check_digit():
    """A supplied check digit is discarded and recomputed."""
    assert ITF14Encoder("15401414536980").full_code == "15401414536987"


@pytest.mark.parametrize("code", ["154014145369", "154014145369812", "154014145369A"])
def test_itf14_rejects_bad_input(code):
    with pytest.raises(PyStrichInvalidInput, match="13 or 14 digits"):
        ITF14Encoder(code)


@pytest.mark.parametrize("digits", ["12345", "12345A", ""])
def test_itf_rejects_non_even_or_non_digit(digits):
    with pytest.raises(PyStrichInvalidInput, match="even-length"):
        ITFEncoder(digits)


def test_encoding():
    """Bar pattern for a known even-length input, start and stop included."""
    bars = encode_digits("1234567890")
    assert bars.startswith("1010")
    assert bars.endswith("11101")
    assert bars == (
        "1010110100101011001101101001010011010011001010100101011001101011010011001011101"
    )


def test_itf14_defaults_to_a_bearer_but_itf_does_not():
    digits = "15401414536987"
    assert ITF14Encoder(digits).init_renderer()._bar_layout(3).bearer_width > 0
    assert ITFEncoder(digits).init_renderer()._bar_layout(3).bearer_width == 0


def test_bearer_width_option_overrides_defaults():
    """The option turns a bearer on for plain ITF and off for ITF-14."""
    assert (
        ITFEncoder("1234567890", options={"bearer_width": 3})
        .init_renderer()
        ._bar_layout(3)
        .bearer_width
        > 0
    )
    assert (
        ITF14Encoder("15401414536987", options={"bearer_width": 0})
        .init_renderer()
        ._bar_layout(3)
        .bearer_width
        == 0
    )


def test_show_label_false_drops_label_but_keeps_bearer():
    """A caller can suppress the label to render their own; the frame stays."""
    layout = (
        ITF14Encoder("15401414536987", options={"show_label": False}).init_renderer()._bar_layout(3)
    )
    assert layout.labels == ()
    assert layout.bearer_width > 0


def test_height_too_small_is_rejected():
    with pytest.raises(PyStrichInvalidOption, match="too small"):
        ITF14Encoder("15401414536987", options={"height": 10}).get_svg(3)


@pytest.mark.parametrize(
    "code, decoded",
    [
        ("1540141453698", "15401414536987"),
        ("9780201379624", "97802013796248"),
    ],
)
@pytest.mark.png
def test_scanner_round_trip(code, decoded, tmp_path, decode_barcode):
    """A real scanner decodes the saved image to the 14-digit code."""
    img = tmp_path / "itf14.png"
    ITF14Encoder(code).save(str(img))
    assert decode_barcode(img) == decoded


@pytest.mark.parametrize("bar_width", [3, 5])
def test_svg_round_trip(bar_width, tmp_path, svg_to_png, decode_barcode):
    """SVG output rasterised with librsvg decodes to the 14-digit code."""
    svg = tmp_path / "itf14.svg"
    png = tmp_path / "itf14.png"
    ITF14Encoder("1540141453698").save_svg(str(svg), bar_width)
    svg_to_png(svg, png)
    assert decode_barcode(png) == "15401414536987"


@pytest.mark.parametrize("bar_width", [3, 5])
def test_eps_round_trip(bar_width, tmp_path, eps_to_png, decode_barcode):
    """EPS output rasterised with Ghostscript decodes to the 14-digit code."""
    eps = tmp_path / "itf14.eps"
    png = tmp_path / "itf14.png"
    ITF14Encoder("1540141453698").save_eps(str(eps), bar_width)
    eps_to_png(eps, png)
    assert decode_barcode(png) == "15401414536987"


@pytest.mark.png
def test_general_itf_round_trip(tmp_path, decode_barcode):
    """A plain (bearer-less) Interleaved 2 of 5 symbol scans back."""
    img = tmp_path / "itf.png"
    ITFEncoder("1234567890").save(str(img))
    assert decode_barcode(img) == "1234567890"
