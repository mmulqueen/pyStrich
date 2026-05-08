"""Unit test for EAN-13 barcode encoder"""

import filecmp
from pathlib import Path

import pytest

from pystrich.ean13 import EAN13Encoder

TEST_IMG_DIR = Path(__file__).parent / "test_img"


@pytest.mark.parametrize("code, check_digit", [
    ("012345678901", 2),
    ("007567816412", 5),
    ("750103131130", 9),
    ("000000000000", 0),
    ("000000010101", 1),
    ("000000001111", 2),
    ("000000000111", 3),
    ("000000000101", 4),
    ("000000001011", 5),
    ("000000001001", 6),
    ("000000000001", 7),
    ("000000001010", 8),
    ("000000000010", 9),
])
def test_check_digit(code, check_digit):
    """Check digit calculation covers the full 0-9 range."""
    assert EAN13Encoder(code).check_digit == check_digit


def test_parity():
    assert EAN13Encoder("750103131130").get_parity() == (1, 0, 1, 0, 1, 0)


def test_encoding():
    """Left and right halves match the known bit patterns for 750103131130."""
    enc = EAN13Encoder("750103131130")
    left, right = enc.encode()
    assert left == "011000101001110011001010011101111010110011"
    assert right == "100001011001101100110100001011100101110100"


@pytest.mark.parametrize("string, reference", [
    ("012345678901", "1.png"),
    ("007567816412", "2.png"),
    ("750103131130", "3.png"),
])
def test_against_generated(string, reference, tmp_path):
    """Output bytes match the checked-in reference image."""
    generated = tmp_path / "barcode.png"
    EAN13Encoder(string).save(str(generated))
    assert filecmp.cmp(str(generated), str(TEST_IMG_DIR / reference), shallow=False)


@pytest.mark.parametrize("string, decoded", [
    ("012345678901", "0123456789012"),
    ("007567816412", "0075678164125"),
    ("750103131130", "7501031311309"),
])
def test_zbarimg_round_trip(string, decoded, tmp_path, zbarimg):
    """zbarimg decodes the saved image to the input plus its check digit."""
    img = tmp_path / "ean13.png"
    EAN13Encoder(string).save(str(img))
    assert zbarimg(img) == decoded


def test_first_digit_y_offset_zero(tmp_path, zbarimg):
    """Setting the option does not break scanner decoding."""
    img = tmp_path / "ean13.png"
    EAN13Encoder(
        "750103131130", options={"first_digit_y_offset": 0}
    ).save(str(img))
    assert zbarimg(img) == "7501031311309"


@pytest.mark.parametrize("bar_width", [3, 5])
@pytest.mark.parametrize("string, decoded", [
    ("012345678901", "0123456789012"),
    ("007567816412", "0075678164125"),
    ("750103131130", "7501031311309"),
])
def test_svg_round_trip(string, decoded, bar_width, tmp_path, svg_to_png, zbarimg):
    """SVG output rasterised with ImageMagick decodes to the input plus check digit."""
    svg = tmp_path / "ean13.svg"
    png = tmp_path / "ean13.png"
    EAN13Encoder(string).save_svg(str(svg), bar_width)
    svg_to_png(svg, png)
    assert zbarimg(png) == decoded


@pytest.mark.parametrize("bar_width", [3, 5])
@pytest.mark.parametrize("string, decoded", [
    ("012345678901", "0123456789012"),
    ("007567816412", "0075678164125"),
    ("750103131130", "7501031311309"),
])
def test_eps_round_trip(string, decoded, bar_width, tmp_path, eps_to_png, zbarimg):
    """EPS output rasterised with Ghostscript decodes to the input plus check digit."""
    eps = tmp_path / "ean13.eps"
    png = tmp_path / "ean13.png"
    EAN13Encoder(string).save_eps(str(eps), bar_width)
    eps_to_png(eps, png)
    assert zbarimg(png) == decoded
