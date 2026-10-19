"""Tests for 2D raster output: PNG bit depth and the ``depth`` option."""

from __future__ import annotations

import io
from urllib.request import urlopen

import pytest

from pystrich.aztec import AztecEncoder
from pystrich.datamatrix import DataMatrixEncoder
from pystrich.exceptions import PyStrichInvalidOption
from pystrich.pdf417 import PDF417Encoder
from pystrich.qrcode import QRCodeEncoder

_NAVY = "#1b3a5c"
_LIGHT_GREY = "#e8e8e8"


@pytest.mark.png
@pytest.mark.parametrize(
    "dark_hex, light_hex, png_mode",
    [
        pytest.param(None, None, "1", id="black-on-white"),
        pytest.param("#ffffff", "#000000", "1", id="white-on-black"),
        pytest.param("#333333", "#eeeeee", "P", id="greys"),
        pytest.param(_NAVY, _LIGHT_GREY, "P", id="colours"),
        pytest.param("#000000", "#ffffff00", "P", id="transparent-light"),
    ],
)
@pytest.mark.parametrize(
    "make_encoder",
    [
        pytest.param(lambda: QRCodeEncoder("colour"), id="qrcode"),
        pytest.param(lambda: DataMatrixEncoder("colour"), id="datamatrix"),
        pytest.param(lambda: AztecEncoder("colour"), id="aztec"),
        pytest.param(lambda: PDF417Encoder("colour"), id="pdf417"),
    ],
)
def test_matrix_png_is_one_bit_with_same_pixels(make_encoder, dark_hex, light_hex, png_mode):
    image = pytest.importorskip("PIL.Image")
    encoder = make_encoder()
    png = encoder.get_imagedata(3, dark_hex=dark_hex, light_hex=light_hex)
    assert png[24] == 1  # IHDR bit depth
    decoded = image.open(io.BytesIO(png))
    assert decoded.mode == png_mode
    expected = encoder.get_pilimage(3, dark_hex=dark_hex, light_hex=light_hex)
    assert decoded.convert(expected.mode).tobytes() == expected.tobytes()
    bilevel = encoder.get_pilimage(3, dark_hex=dark_hex, light_hex=light_hex, depth="bilevel")
    assert bilevel.mode == png_mode


@pytest.mark.png
@pytest.mark.parametrize(
    "dark_hex, light_hex",
    [
        pytest.param(None, None, id="black-on-white"),
        pytest.param(_NAVY, _LIGHT_GREY, id="colours"),
        pytest.param("#000000", "#ffffff00", id="transparent-light"),
    ],
)
def test_matrix_png_full_depth_is_get_pilimage(dark_hex, light_hex):
    image = pytest.importorskip("PIL.Image")
    qr = QRCodeEncoder("colour")
    png = qr.get_imagedata(3, dark_hex=dark_hex, light_hex=light_hex, depth="full")
    assert png[24] == 8  # IHDR bit depth
    decoded = image.open(io.BytesIO(png))
    expected = qr.get_pilimage(3, dark_hex=dark_hex, light_hex=light_hex)
    assert (decoded.mode, decoded.tobytes()) == (expected.mode, expected.tobytes())


def test_matrix_rejects_unknown_depth():
    with pytest.raises(PyStrichInvalidOption, match="depth"):
        QRCodeEncoder("hello").get_pilimage(3, depth="1")  # type: ignore[arg-type]


@pytest.mark.png
@pytest.mark.parametrize("depth", ["bilevel", "full"])
def test_matrix_save_and_dataurl_match_imagedata(tmp_path, depth):
    pytest.importorskip("PIL.Image")
    qr = QRCodeEncoder("hello")
    options = {"dark_hex": _NAVY, "light_hex": _LIGHT_GREY, "depth": depth}
    png = qr.get_imagedata(3, **options)
    qr.save(str(tmp_path / "qr.png"), 3, **options)
    assert (tmp_path / "qr.png").read_bytes() == png
    with urlopen(qr.png_dataurl(3, **options)) as response:
        assert response.read() == png
