"""Unit test for QR Code barcode encoder"""

import subprocess
import unittest
from shutil import which

import pytest

from pystrich.qrcode import QRCodeEncoder

zbarimg_path = which("zbarimg")


def zbarimg(image_path: str) -> str:
    """Read a QR code from an image file using zbarimg"""
    if not zbarimg_path:
        raise RuntimeError("zbarimg not found")
    output = subprocess.check_output(
        [zbarimg_path, "--quiet", "--raw", image_path]
    ).decode()
    return output.rstrip("\n")


class QRTest(unittest.TestCase):
    """Unit test class for QR Code encoder"""

    test_strings = ("banana",
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
                    "http://www.hudora.de/track/0034")

    def test_against_generated(self):
        """Compare the output of this library with generated barcodes"""

        i = 1
        for string in QRTest.test_strings:
            encoder = QRCodeEncoder(string, 'M')
            encoder.save('test.png', 3)

            import filecmp
            self.assertTrue(filecmp.cmp('test.png',
                                        'pystrich/qrcode/test_img/%d.png' % i))
            i += 1

    def test_encoding(self):
        """Test that text is correctly encoded, and also that padding
        and error codewords are correctly added"""

        correct_encodings = {
            "hi": [64, 38, 134, 144, 236, 17, 236, 17, 236, 17, 236,
                   17, 236, 17, 236, 17, 17, 160, 77, 193, 121, 155,
                   5, 133, 245, 218],

            "banana": [64, 102, 38, 22, 230, 22, 230, 16, 236, 17, 236,
                       17, 236, 17, 236, 17, 5, 142, 20, 56, 215, 125,
                       137, 131, 106, 125, 0],

            "wer das liest ist 31337": [
                65, 119, 118, 87, 34, 6, 70, 23, 50, 6, 198, 150,
                87, 55, 66, 6, 151, 55, 66, 3, 51, 19, 51, 51, 112,
                236, 17, 236, 124, 222, 181, 177, 208, 193, 45, 100,
                155, 47, 28, 28, 88, 55, 156, 59, 0, 0]}

        from pystrich.qrcode.textencoder import TextEncoder
        enc = TextEncoder()
        for key, value in correct_encodings.items():
            enc.encode(key, ecl='M')
            self.assertEqual(enc.codewords, value)


_xfail_unscannable = pytest.mark.xfail(
    raises=subprocess.CalledProcessError,
    reason="zbarimg cannot decode output",
    strict=True,
)
_xfail_indexerror = pytest.mark.xfail(
    raises=IndexError,
    reason="encoder raises IndexError (issue #8)",
    strict=True,
)


@pytest.mark.skipif(not zbarimg_path, reason="zbarimg not installed")
@pytest.mark.parametrize("string", [
    pytest.param("banana"),
    pytest.param("wer das liest ist 31337"),
    pytest.param("http://hudora.de/"),
    pytest.param("http://hudora.de/artnr/12345/12/"),
    pytest.param("http://hudora.de/track/00340059980000001319/"),
    pytest.param("http://www.hudora.de/track/00340059980000001319/", marks=_xfail_unscannable),
    pytest.param("http://www.hudora.de/track/00340059980000001319"),
    pytest.param("http://www.hudora.de/track/0034005998000000131", marks=_xfail_unscannable),
    pytest.param("http://www.hudora.de/track/003400599800000013"),
    pytest.param("http://www.hudora.de/track/00340059980000001", marks=_xfail_unscannable),
    pytest.param("http://www.hudora.de/track/0034005998000000", marks=_xfail_unscannable),
    pytest.param("http://www.hudora.de/track/003400599800000"),
    pytest.param("http://www.hudora.de/track/00340059980000"),
    pytest.param("http://www.hudora.de/track/0034005998000"),
    pytest.param("http://www.hudora.de/track/003400599800"),
    pytest.param("http://www.hudora.de/track/00340059980"),
    pytest.param("http://www.hudora.de/track/0034005998"),
    pytest.param("http://www.hudora.de/track/003400599"),
    pytest.param("http://www.hudora.de/track/00340059"),
    pytest.param("http://www.hudora.de/track/0034005"),
    pytest.param("http://www.hudora.de/track/003400"),
    pytest.param("http://www.hudora.de/track/00340"),
    pytest.param("http://www.hudora.de/track/0034"),
    # https://github.com/mmulqueen/pyStrich/issues/8
    pytest.param("B-4-1-20170805-6", marks=_xfail_indexerror),
    pytest.param("b-4-1-20170805-6"),
    pytest.param("00231872347699829949", marks=_xfail_indexerror),
    pytest.param("00231872347699829948"),
])
def test_encode_decode(string, tmp_path):
    """zbarimg can decode this library's output back to the original string"""
    img = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, "M").save(str(img), 3)
    assert zbarimg(str(img)) == string
