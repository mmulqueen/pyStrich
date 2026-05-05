"""Unit test for 2D datamatrix barcode encoder"""

import pytest

from pystrich.datamatrix import DataMatrixEncoder
from pystrich.datamatrix.renderer import DATAMATRIX_DEFAULT_QUIET_ZONE
from pystrich.datamatrix.textencoder import TextEncoder


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
    "This sentence will need multiple datamatrix regions. Tests to see whether bug 2 is fixed.",
])
def test_encode_decode(string, tmp_path, dmtxread):
    """dmtxread can decode this library's output back to the original string"""
    img = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(string).save(str(img))
    assert dmtxread(str(img)) == string


@pytest.mark.parametrize("text, expected_codewords", [
    pytest.param("hi", [105, 106, 129, 74, 235, 130, 61, 159], id="hi"),
    pytest.param(
        "banana",
        [99, 98, 111, 98, 111, 98, 129, 56,
         227, 236, 237, 109, 16, 221, 163, 60, 171, 76],
        id="banana",
    ),
    pytest.param(
        "wer das liest ist 31337",
        [120, 102, 115, 33, 101, 98, 116, 33, 109, 106,
         102, 116, 117, 33, 106, 116, 117, 33, 161, 163,
         56, 129, 83, 116, 244, 3, 40, 16, 79, 220, 144,
         76, 17, 186, 175, 211, 244, 84, 59, 71],
        id="wer-das-liest",
    ),
])
def test_encoding(text, expected_codewords):
    """Text is correctly encoded with padding and error codewords."""
    enc = TextEncoder()
    assert [ord(c) for c in enc.encode(text)] == expected_codewords


@pytest.mark.parametrize("quiet_zone, expected_diff", [
    pytest.param(0, -DATAMATRIX_DEFAULT_QUIET_ZONE * 2, id="zero"),
    pytest.param(10, (10 - DATAMATRIX_DEFAULT_QUIET_ZONE) * 2, id="ten"),
])
def test_quiet_zone_changes_width(quiet_zone, expected_diff):
    """Width differs from the default by 2 * (quiet_zone - default) on each axis."""
    # .width is populated by the renderer, so each encoder must render before comparison.
    default_encoder = DataMatrixEncoder("test")
    default_encoder.get_imagedata()
    custom_encoder = DataMatrixEncoder("test", quiet_zone=quiet_zone)
    custom_encoder.get_imagedata()
    assert custom_encoder.width - default_encoder.width == expected_diff


def test_quiet_zone_round_trip(tmp_path, dmtxread):
    """A non-default quiet_zone still produces a decodable image."""
    # quiet_zone=0 is excluded because dmtxread fails to detect the symbol without padding.
    img = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder("test", quiet_zone=10).save(str(img))
    assert dmtxread(str(img)) == "test"


def test_get_imagedata_matches_save(tmp_path):
    """get_imagedata() returns the same bytes that save() writes to disk."""
    img = tmp_path / "datamatrix-test.png"
    encoder = DataMatrixEncoder("Hello world")
    encoder.save(str(img))
    assert img.read_bytes() == encoder.get_imagedata()
