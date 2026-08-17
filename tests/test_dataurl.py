from __future__ import annotations

from urllib.request import urlopen

import pytest

from pystrich.aztec import AztecEncoder
from pystrich.bar_encoder import Bar1DEncoder
from pystrich.code39 import Code39Encoder
from pystrich.code128 import Code128Encoder
from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder
from pystrich.ean13 import EAN13Encoder
from pystrich.matrix_encoder import Matrix2DEncoder
from pystrich.pdf417 import PDF417Encoder
from pystrich.qrcode import QRCodeEncoder

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

ENCODER_CASES = [
    pytest.param(AztecEncoder("hello"), id="aztec"),
    pytest.param(Code39Encoder("HELLO"), id="code39"),
    pytest.param(Code128Encoder("hello"), id="code128"),
    pytest.param(
        DataMatrixEncoder(DataMatrixData("hello", auto_encoding=True)),
        id="datamatrix",
    ),
    pytest.param(EAN13Encoder("5050070007664"), id="ean13"),
    pytest.param(PDF417Encoder("hello"), id="pdf417"),
    pytest.param(QRCodeEncoder("hello"), id="qrcode"),
]


@pytest.mark.parametrize("encoder", ENCODER_CASES)
def test_svg_dataurl(encoder: Bar1DEncoder | Matrix2DEncoder) -> None:
    with urlopen(encoder.svg_dataurl()) as resp:
        assert resp.headers.get_content_type() == "image/svg+xml"
        body = resp.read()
    assert body.lstrip().startswith(b"<svg")


@pytest.mark.parametrize("encoder", ENCODER_CASES)
@pytest.mark.png
def test_png_dataurl(encoder: Bar1DEncoder | Matrix2DEncoder) -> None:
    with urlopen(encoder.png_dataurl()) as resp:
        assert resp.headers.get_content_type() == "image/png"
        body = resp.read()
    assert body.startswith(PNG_SIGNATURE)
