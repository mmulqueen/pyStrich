"""Unit test for code128 barcode encoder"""

import filecmp
from pathlib import Path

import pytest

from pystrich.code128 import Code128Encoder

TEST_IMG_DIR = Path(__file__).parent / "test_img"


@pytest.mark.parametrize(
    "text, expected_codewords",
    [
        pytest.param("1234", [105, 12, 34], id="dense-C"),
        pytest.param("hello", [104, 72, 69, 76, 76, 79], id="B-only"),
        pytest.param("HI345678", [104, 40, 41, 99, 34, 56, 78], id="B-to-C"),
        pytest.param("BarCode 1", [104, 34, 65, 82, 35, 79, 68, 69, 0, 17], id="B-mixed"),
        pytest.param("HI34567A", [104, 40, 41, 99, 34, 56, 100, 23, 33], id="B-C-B-leftover"),
        # https://github.com/hudora/huBarcode/issues/issue/11
        pytest.param("12345", [105, 12, 34, 100, 21], id="C-leftover-digit"),
    ],
)
def test_charset_encoding(text, expected_codewords):
    """Charset selection, code switching, and optimization produce known-good codewords."""
    assert Code128Encoder(text).encoded_text == expected_codewords


@pytest.mark.parametrize(
    "text, checksum",
    [
        ("HI345678", 68),
        ("BarCode 1", 33),
    ],
)
def test_check_sum(text, checksum):
    assert Code128Encoder(text).checksum == checksum


def test_bar_encoding():
    bars = (
        "11010010000"
        + "11000101000"
        + "11000100010"
        + "10111011110"
        + "10001011000"
        + "11100010110"
        + "11000010100"
        + "10000100110"
        + "11000111010"
        + "11"
    )
    assert Code128Encoder("HI345678").bars == bars


@pytest.mark.parametrize(
    "string, reference",
    [
        ("banana", "1.png"),
        ("wer das liest ist 31337", "2.png"),
        ("http://hudora.de/", "3.png"),
        ("http://hudora.de/artnr/12345/12/", "4.png"),
        ("http://hudora.de/track/00340059980000001319/", "5.png"),
        ("12345678", "6.png"),
        ("123456789", "7.png"),
    ],
)
def test_against_generated(string, reference, tmp_path):
    """Output bytes match the checked-in reference image."""
    generated = tmp_path / "barcode.png"
    Code128Encoder(string).save(str(generated))
    assert filecmp.cmp(str(generated), str(TEST_IMG_DIR / reference), shallow=False)


@pytest.mark.parametrize(
    "string",
    [
        pytest.param("1234", id="dense-C"),
        pytest.param("hello", id="B-only"),
        pytest.param("HI345678", id="B-to-C"),
        pytest.param("BarCode 1", id="B-mixed"),
        pytest.param("HI34567A", id="B-C-B-leftover"),
        # https://github.com/hudora/huBarcode/issues/issue/11
        pytest.param("12345", id="C-leftover-digit"),
    ],
)
def test_scanner_round_trip(string, tmp_path, decode_barcode):
    """A real scanner decodes this library's output back to the original string."""
    img = tmp_path / "code128.png"
    Code128Encoder(string).save(str(img))
    assert decode_barcode(img) == string


@pytest.mark.parametrize("bar_width", [3, 5])
@pytest.mark.parametrize(
    "string",
    [
        pytest.param("1234", id="dense-C"),
        pytest.param("hello", id="B-only"),
        pytest.param("HI345678", id="B-to-C"),
        pytest.param("BarCode 1", id="B-mixed"),
    ],
)
@pytest.mark.parametrize("options", [{}, {"show_label": False}])
def test_svg_round_trip(string, bar_width, options, tmp_path, svg_to_png, decode_barcode):
    """SVG output rasterised with librsvg decodes back to the original string."""
    svg = tmp_path / "code128.svg"
    png = tmp_path / "code128.png"
    Code128Encoder(string, options=options).save_svg(str(svg), bar_width)
    svg_to_png(svg, png)
    assert decode_barcode(png) == string


@pytest.mark.parametrize("bar_width", [3, 5])
@pytest.mark.parametrize(
    "string",
    [
        pytest.param("1234", id="dense-C"),
        pytest.param("hello", id="B-only"),
        pytest.param("HI345678", id="B-to-C"),
        pytest.param("BarCode 1", id="B-mixed"),
    ],
)
@pytest.mark.parametrize("options", [{}, {"show_label": False}])
def test_eps_round_trip(string, bar_width, options, tmp_path, eps_to_png, decode_barcode):
    """EPS output rasterised with Ghostscript decodes back to the original string."""
    eps = tmp_path / "code128.eps"
    png = tmp_path / "code128.png"
    Code128Encoder(string, options=options).save_eps(str(eps), bar_width)
    eps_to_png(eps, png)
    assert decode_barcode(png) == string


@pytest.mark.parametrize(
    "string",
    [
        pytest.param("1234", id="dense-C"),
        pytest.param("hello", id="B-only"),
        pytest.param("BarCode 1", id="B-mixed"),
    ],
)
def test_svg_label_glyphs(string):
    """SVG output defines one ``<symbol>`` per unique label char and ``<use>``-s it once per occurrence."""
    svg = Code128Encoder(string).get_svg(3)
    for char in set(string):
        assert f'id="g_{ord(char):02X}"' in svg
    assert svg.count("<use href=") == len(string)


@pytest.mark.parametrize(
    "string",
    [
        pytest.param("1234", id="dense-C"),
        pytest.param("hello", id="B-only"),
        pytest.param("BarCode 1", id="B-mixed"),
    ],
)
def test_eps_label_glyphs(string):
    """EPS output defines one ``/g_NN`` proc per unique label char and invokes it once per occurrence."""
    eps = Code128Encoder(string).get_eps(3)
    for char in set(string):
        assert f"/g_{ord(char):02X} " in eps
    invocations = sum(
        eps.count(f"g_{ord(c):02X}") - eps.count(f"/g_{ord(c):02X}") for c in set(string)
    )
    assert invocations == len(string)


@pytest.mark.parametrize("fmt", ["svg", "eps"])
def test_charset_a_control_chars_dropped_from_label(fmt):
    """Charset-A control chars have no embedded glyph and must not crash the vector renderer."""
    encoder = Code128Encoder("a\tb\x01c")
    output = getattr(encoder, f"get_{fmt}")(3)
    for printable in "abc":
        assert f"g_{ord(printable):02X}" in output
    for control in "\t\x01":
        assert f"g_{ord(control):02X}" not in output
