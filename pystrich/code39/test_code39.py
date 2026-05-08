"""Unit test for Code39 barcode encoder"""

import filecmp
from pathlib import Path

import pytest

from pystrich.code39 import Code39Encoder

TEST_IMG_DIR = Path(__file__).parent / "test_img"


@pytest.mark.parametrize("string, reference", [
    ("1234567890", "1.png"),
    ("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "2.png"),
    ("THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG", "3.png"),
])
def test_against_generated(string, reference, tmp_path):
    """Output bytes match the checked-in reference image."""
    generated = tmp_path / "barcode.png"
    Code39Encoder(string).save(str(generated))
    assert filecmp.cmp(str(generated), str(TEST_IMG_DIR / reference), shallow=False)


@pytest.mark.parametrize("string", [
    "1234567890",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG",
    # Exercises the Code 39 special symbols ($ . / + - %).
    "INVOICE-5/2024 $A+B%",
])
def test_zbarimg_round_trip(string, tmp_path, zbarimg):
    """zbarimg can decode this library's output back to the original string."""
    img = tmp_path / "code39.png"
    Code39Encoder(string).save(str(img))
    assert zbarimg(img) == string


@pytest.mark.parametrize("bar_width", [3, 5])
@pytest.mark.parametrize("string", [
    "1234567890",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "INVOICE-5/2024 $A+B%",
])
def test_svg_round_trip(string, bar_width, tmp_path, svg_to_png, zbarimg):
    """SVG output rasterised with ImageMagick decodes back to the original string."""
    svg = tmp_path / "code39.svg"
    png = tmp_path / "code39.png"
    Code39Encoder(string).save_svg(str(svg), bar_width)
    svg_to_png(svg, png)
    assert zbarimg(png) == string


@pytest.mark.parametrize("bar_width", [3, 5])
@pytest.mark.parametrize("string", [
    "1234567890",
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "INVOICE-5/2024 $A+B%",
])
def test_eps_round_trip(string, bar_width, tmp_path, eps_to_png, zbarimg):
    """EPS output rasterised with Ghostscript decodes back to the original string."""
    eps = tmp_path / "code39.eps"
    png = tmp_path / "code39.png"
    Code39Encoder(string).save_eps(str(eps), bar_width)
    eps_to_png(eps, png)
    assert zbarimg(png) == string
