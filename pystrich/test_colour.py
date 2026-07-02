"""Unit tests for pystrich.colour and per-format colour rendering."""

from __future__ import annotations

import io

import pytest

from pystrich.aztec import AztecEncoder
from pystrich.code39 import Code39Encoder
from pystrich.code128 import Code128Encoder
from pystrich.colour import RGBA, pil_mode, pil_value, require_opaque, resolve_pil_palette
from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder
from pystrich.ean13 import EAN13Encoder
from pystrich.eps import _eps_colour
from pystrich.exceptions import PyStrichInvalidOption
from pystrich.pdf417 import PDF417Encoder
from pystrich.qrcode import QRCodeEncoder
from pystrich.svg import _svg_fill, matrix_to_svg
from pystrich.test_svg import get_rects_in_group_with_fill

# The conservative navy-on-light-grey pair the docs use throughout.
_NAVY = "#1b3a5c"
_LIGHT_GREY = "#e8e8e8"


@pytest.mark.parametrize(
    "value, expected",
    [
        pytest.param("#000", RGBA(0, 0, 0, 255), id="hash-3"),
        pytest.param("000", RGBA(0, 0, 0, 255), id="bare-3"),
        pytest.param("f0a", RGBA(255, 0, 170, 255), id="shorthand-expands"),
        pytest.param("#1b3a5c", RGBA(27, 58, 92, 255), id="hash-6"),
        pytest.param("ABC", RGBA(170, 187, 204, 255), id="uppercase"),
        pytest.param("#ffffff00", RGBA(255, 255, 255, 0), id="8-digit-alpha"),
    ],
)
def test_parse_hex_colour_valid(value, expected):
    assert RGBA.parse_hex(value) == expected


@pytest.mark.parametrize("channels", [(256, 0, 0), (-1, 0, 0), (0, 0, 0, 256)])
def test_rgba_rejects_out_of_range_channels(channels):
    with pytest.raises(PyStrichInvalidOption, match="0-255"):
        RGBA(*channels)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("12", id="too-short"),
        pytest.param("#12345", id="five-digits"),
        pytest.param("1234567", id="seven-digits"),
        pytest.param("gg00ff", id="non-hex"),
        pytest.param("", id="empty"),
        pytest.param("#", id="hash-only"),
    ],
)
def test_parse_hex_colour_invalid(value):
    with pytest.raises(PyStrichInvalidOption, match="3, 6 or 8 hex digits"):
        RGBA.parse_hex(value)


@pytest.mark.parametrize(
    "value",
    [
        pytest.param("#1b3a5c", id="6-digit"),
        pytest.param("#1b3a5cff", id="8-digit-opaque"),
    ],
)
def test_require_opaque_allows_opaque(value):
    require_opaque(RGBA.parse_hex(value))


def test_require_opaque_rejects_alpha():
    with pytest.raises(PyStrichInvalidOption, match="transparent"):
        require_opaque(RGBA.parse_hex("#ffffff00"))


def test_coerce_passes_through_rgba():
    rgba = RGBA(27, 58, 92, 128)
    assert RGBA.coerce(rgba) is rgba


def test_coerce_parses_hex_string():
    assert RGBA.coerce("#1b3a5c") == RGBA(27, 58, 92)


def test_rgba_argument_matches_equivalent_hex():
    via_rgba = QRCodeEncoder("hi").get_svg(dark_hex=RGBA(27, 58, 92), light_hex=RGBA(238, 238, 238))
    via_hex = QRCodeEncoder("hi").get_svg(dark_hex="#1b3a5c", light_hex="#eee")
    assert via_rgba == via_hex


@pytest.mark.parametrize(
    "rgba, expected",
    [
        pytest.param(RGBA(0, 0, 0), 'fill="#000"', id="black-collapses"),
        pytest.param(RGBA(255, 255, 255), 'fill="#fff"', id="white-collapses"),
        pytest.param(RGBA(27, 58, 92), 'fill="#1b3a5c"', id="opaque-6-digit"),
        pytest.param(RGBA(255, 255, 255, 0), 'fill="#fff" fill-opacity="0"', id="transparent"),
        pytest.param(
            RGBA(27, 58, 92, 128), 'fill="#1b3a5c" fill-opacity="0.502"', id="translucent"
        ),
    ],
)
def test_svg_fill(rgba, expected):
    assert _svg_fill(rgba) == expected


@pytest.mark.parametrize(
    "rgba, expected",
    [
        pytest.param(RGBA(0, 0, 0), "0 setgray", id="black"),
        pytest.param(RGBA(255, 255, 255), "1 setgray", id="white"),
        pytest.param(RGBA(128, 128, 128), "0.502 setgray", id="grey-uses-setgray"),
        pytest.param(RGBA(27, 58, 92), "0.1059 0.2275 0.3608 setrgbcolor", id="colour-uses-rgb"),
    ],
)
def test_eps_colour(rgba, expected):
    assert _eps_colour(rgba) == expected


@pytest.mark.parametrize(
    "dark, light, mode, dark_fill, light_fill",
    [
        pytest.param(RGBA(0, 0, 0), RGBA(255, 255, 255), "L", 0, 255, id="greyscale-opaque-L"),
        pytest.param(
            RGBA(27, 58, 92),
            RGBA(255, 255, 255),
            "RGB",
            (27, 58, 92),
            (255, 255, 255),
            id="colour-opaque-RGB",
        ),
        pytest.param(
            RGBA(0, 0, 0),
            RGBA(255, 255, 255, 0),
            "RGBA",
            (0, 0, 0, 255),
            (255, 255, 255, 0),
            id="alpha-RGBA",
        ),
    ],
)
def test_pil_mode_and_fills(dark, light, mode, dark_fill, light_fill):
    assert pil_mode(dark, light) == mode
    assert pil_value(dark, mode) == dark_fill
    assert pil_value(light, mode) == light_fill


def test_resolve_pil_palette_defaults_to_black_on_white():
    assert resolve_pil_palette(None, None) == ("L", 0, 255)


def test_resolve_pil_palette_returns_mode_then_dark_then_light():
    assert resolve_pil_palette("#1b3a5c", "#fff") == ("RGB", (27, 58, 92), (255, 255, 255))


def test_svg_uses_custom_colours():
    svg = matrix_to_svg([[1, 0, 1]], cellsize=5, dark_hex="#1b3a5c", light_hex="#eee")
    assert get_rects_in_group_with_fill(svg, "#1b3a5c")
    assert 'fill="#eee"' in svg


def test_svg_alpha_emits_fill_opacity():
    svg = QRCodeEncoder("hi").get_svg(light_hex="#ffffff00")
    assert 'fill="#fff" fill-opacity="0"' in svg


def test_eps_transparency_rejected_end_to_end():
    with pytest.raises(PyStrichInvalidOption, match="transparent"):
        QRCodeEncoder("hi").get_eps(light_hex="#ffffff00")


@pytest.mark.png
def test_png_default_bytes_unchanged():
    image = pytest.importorskip("PIL.Image")
    qr = QRCodeEncoder("hello")
    assert qr.get_imagedata() == qr.get_imagedata(dark_hex=None, light_hex=None)
    assert image.open(io.BytesIO(qr.get_imagedata())).mode == "L"


@pytest.mark.png
def test_png_background_pixel_takes_light_colour():
    # Code 128's top-left corner is quiet zone, i.e. background.
    img = Code128Encoder("ABC123").get_pilimage(dark_hex="#1b3a5c", light_hex="#ffe9c7")
    assert img.mode == "RGB"
    assert img.getpixel((0, 0)) == (255, 233, 199)


_ROUND_TRIP_CASES = [
    pytest.param(lambda: Code39Encoder("COLOUR"), 3, "COLOUR", id="code39"),
    pytest.param(lambda: Code128Encoder("colour"), 3, "colour", id="code128"),
    pytest.param(lambda: EAN13Encoder("5050070007664"), 3, "5050070007664", id="ean13"),
    pytest.param(lambda: QRCodeEncoder("colour"), 5, "colour", id="qrcode"),
    pytest.param(
        lambda: DataMatrixEncoder(DataMatrixData("colour", auto_encoding=True)),
        5,
        "colour",
        id="datamatrix",
    ),
    pytest.param(lambda: PDF417Encoder("colour"), 5, "colour", id="pdf417"),
    pytest.param(lambda: AztecEncoder("colour"), 5, "colour", id="aztec"),
]


@pytest.mark.png
@pytest.mark.parametrize("make_encoder, size, decoded", _ROUND_TRIP_CASES)
def test_non_bw_round_trip_png(make_encoder, size, decoded, tmp_path, decode_barcode):
    """A navy-on-light-grey symbol still decodes as PNG."""
    png = tmp_path / "out.png"
    make_encoder().save(str(png), size, dark_hex=_NAVY, light_hex=_LIGHT_GREY)
    assert decode_barcode(png) == decoded


@pytest.mark.parametrize("make_encoder, size, decoded", _ROUND_TRIP_CASES)
def test_non_bw_round_trip_svg(make_encoder, size, decoded, tmp_path, svg_to_png, decode_barcode):
    """A navy-on-light-grey symbol still decodes as SVG rasterised with librsvg."""
    svg = tmp_path / "out.svg"
    png = tmp_path / "out.png"
    make_encoder().save_svg(str(svg), size, dark_hex=_NAVY, light_hex=_LIGHT_GREY)
    svg_to_png(svg, png)
    assert decode_barcode(png) == decoded


@pytest.mark.parametrize("make_encoder, size, decoded", _ROUND_TRIP_CASES)
def test_non_bw_round_trip_eps(make_encoder, size, decoded, tmp_path, eps_to_png, decode_barcode):
    """A navy-on-light-grey symbol still decodes as EPS rasterised with Ghostscript."""
    eps = tmp_path / "out.eps"
    png = tmp_path / "out.png"
    make_encoder().save_eps(str(eps), size, dark_hex=_NAVY, light_hex=_LIGHT_GREY)
    eps_to_png(eps, png)
    assert decode_barcode(png) == decoded
