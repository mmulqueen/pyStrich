"""Unit test for QR Code barcode encoder"""

import subprocess
from shutil import which

import pytest

from pystrich.qrcode import QRCodeEncoder, isodata
from pystrich.qrcode.textencoder import STR2ECL, TextEncoder

zbarimg_path = which("zbarimg")


def zbarimg(image_path: str) -> str:
    """Read a QR code from an image file using zbarimg"""
    if not zbarimg_path:
        raise RuntimeError("zbarimg not found")
    output = subprocess.check_output(
        [zbarimg_path, "--quiet", "--raw", image_path]
    ).decode()
    return output.rstrip("\n")


@pytest.mark.parametrize("text, expected_codewords", [
    (
        "hi",
        [64, 38, 134, 144, 236, 17, 236, 17, 236, 17, 236,
         17, 236, 17, 236, 17, 17, 160, 77, 193, 121, 155,
         5, 133, 245, 218],
    ),
    (
        "banana",
        [64, 102, 38, 22, 230, 22, 230, 16, 236, 17, 236,
         17, 236, 17, 236, 17, 5, 142, 20, 56, 215, 125,
         137, 131, 106, 125],
    ),
    (
        "wer das liest ist 31337",
        [65, 119, 118, 87, 34, 6, 70, 23, 50, 6, 198, 150,
         87, 55, 66, 6, 151, 55, 66, 3, 51, 19, 51, 51, 112,
         236, 17, 236, 124, 222, 181, 177, 208, 193, 45, 100,
         155, 47, 28, 28, 88, 55, 156, 59],
    ),
])
def test_encoding(text, expected_codewords):
    """Text is correctly encoded with padding and error codewords."""
    enc = TextEncoder()
    enc.encode(text, ecl="M")
    assert enc.codewords == expected_codewords


@pytest.mark.skipif(not zbarimg_path, reason="zbarimg not installed")
@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize("string", [
    "banana",
    "wer das liest ist 31337",
    "http://hudora.de/",
    "http://hudora.de/artnr/12345/12/",
    "http://hudora.de/track/00340059980000001319/",
    "http://www.hudora.de/track/00340059980000001319/",
    "http://www.hudora.de/track/00340059980000001319",
    "http://www.hudora.de/track/0034005998000000131",
    "http://www.hudora.de/track/003400599800000013",
    "http://www.hudora.de/track/00340059980000001",
    "http://www.hudora.de/track/0034005998000000",
    "http://www.hudora.de/track/003400599800000",
    "http://www.hudora.de/track/00340059980000",
    "http://www.hudora.de/track/0034005998000",
    "http://www.hudora.de/track/003400599800",
    "http://www.hudora.de/track/00340059980",
    "http://www.hudora.de/track/0034005998",
    "http://www.hudora.de/track/003400599",
    "http://www.hudora.de/track/00340059",
    "http://www.hudora.de/track/0034005",
    "http://www.hudora.de/track/003400",
    "http://www.hudora.de/track/00340",
    "http://www.hudora.de/track/0034",
    # https://github.com/mmulqueen/pyStrich/issues/8
    "B-4-1-20170805-6",
    "b-4-1-20170805-6",
    "00231872347699829949",
    "00231872347699829948",
])
def test_encode_decode(string, ecl, tmp_path):
    """zbarimg can decode this library's output back to the original string"""
    img = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, ecl).save(str(img), 3)
    assert zbarimg(str(img)) == string


@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize("text", [
    "hi",
    "A" * 78,
    # https://github.com/mmulqueen/pyStrich/issues/8
    "B-4-1-20170805-6",
    "00231872347699829949",
])
def test_total_codewords_equals_max_codewords(text, ecl):
    """After encoding, len(codewords) must equal MAX_CODEWORDS[version]."""
    enc = TextEncoder()
    enc.encode(text, ecl=ecl)
    assert len(enc.codewords) == isodata.MAX_CODEWORDS[enc.version]
