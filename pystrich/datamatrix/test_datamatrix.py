"""Unit test for 2D datamatrix barcode encoder"""

import warnings

import pytest

from pystrich.datamatrix import (
    DataMatrixCodeword,
    DataMatrixData,
    DataMatrixEncoder,
    FNC1,
)
from pystrich.datamatrix.data import fnc1_workaround_compat
from pystrich.datamatrix.renderer import DATAMATRIX_DEFAULT_QUIET_ZONE
from pystrich.datamatrix.textencoder import TextEncoder
from pystrich.exceptions import (
    DataMatrixNonAsciiWarning,
    Fnc1WorkaroundCompatWarning,
    PyStrichInvalidInput,
    PyStrichInvalidOption,
    PyStrichWarning,
)


_API_FORMS = [
    pytest.param(lambda s: s, id="compat"),
    pytest.param(lambda s: DataMatrixData(s, encoding="ascii"), id="modern"),
]


@pytest.mark.parametrize("wrap", _API_FORMS)
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
def test_encode_decode(string, wrap, tmp_path, dmtxread):
    img = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(wrap(string)).save(str(img))
    assert dmtxread(img) == string


@pytest.mark.parametrize("wrap", _API_FORMS)
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
def test_encoding(text, wrap, expected_codewords):
    enc = TextEncoder()
    assert [ord(c) for c in enc.encode(wrap(text))] == expected_codewords


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
    # quiet_zone=0 is excluded because dmtxread fails to detect the symbol without padding.
    img = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder("test", quiet_zone=10).save(str(img))
    assert dmtxread(img) == "test"


def test_get_imagedata_matches_save(tmp_path):
    img = tmp_path / "datamatrix-test.png"
    encoder = DataMatrixEncoder("Hello world")
    encoder.save(str(img))
    assert img.read_bytes() == encoder.get_imagedata()


def test_gs1_fnc1_workaround(tmp_path, dmtxread):
    """A leading chr(231) is translated to a real FNC1 codeword via the compat shim.

    Kept working as a bug-as-feature so existing users of the workaround don't
    break; new code should use the FNC1 marker constant instead.

    See https://github.com/mmulqueen/pyStrich/issues/13.
    """
    payload = "0100312345678901"
    img = tmp_path / "gs1.png"
    with pytest.warns(Fnc1WorkaroundCompatWarning):
        DataMatrixEncoder(chr(231) + payload).save(str(img))
    assert dmtxread(img, gs1="|") == "|" + payload


@pytest.mark.parametrize("payload, expected", [
    pytest.param(FNC1 + "0100312345678901", "|0100312345678901", id="simple_gs1"),
    pytest.param(FNC1 + "10ABC" + FNC1 + "21XYZ", "|10ABC|21XYZ", id="separated"),
    pytest.param(FNC1 + "1" + FNC1 + "21XYZ", "|1|21XYZ", id="unpaired_digit"),
])
def test_gs1_fnc1(payload, expected, tmp_path, dmtxread):
    """The FNC1 marker emits codeword 232 directly (no chr(231) trick)."""
    img = tmp_path / "gs1.png"
    DataMatrixEncoder(payload).save(str(img))
    assert dmtxread(img, gs1="|") == expected


@pytest.mark.parametrize("data, expected_encoding", [
    pytest.param(FNC1 + "abc", "ascii", id="codeword-then-str"),
    pytest.param("abc" + FNC1, "ascii", id="str-then-codeword"),
    pytest.param(FNC1 + FNC1, "ascii", id="codeword-then-codeword"),
    pytest.param(
        FNC1 + DataMatrixData("abc", encoding="compat"),
        "compat",
        id="codeword-preserves-compat-data-encoding",
    ),
    pytest.param(
        DataMatrixData() + "abc" + FNC1, "compat", id="compat-data-then-str-then-codeword"
    ),
    pytest.param(
        DataMatrixData("abc", encoding="ascii") + "def", "ascii", id="ascii-data-then-str"
    ),
    pytest.param(
        DataMatrixData("a", encoding="ascii") + DataMatrixData("b", encoding="ascii"),
        "ascii",
        id="ascii-data-then-ascii-data",
    ),
])
def test_concat_returns_datamatrix_data(data, expected_encoding):
    assert isinstance(data, DataMatrixData)
    assert data.encoding == expected_encoding


@pytest.mark.parametrize("lhs_encoding, rhs_encoding", [
    ("compat", "ascii"),
    ("ascii", "compat"),
])
def test_concat_with_mismatched_encodings_raises(lhs_encoding, rhs_encoding):
    with pytest.raises(PyStrichInvalidOption):
        DataMatrixData("a", encoding=lhs_encoding) + DataMatrixData("b", encoding=rhs_encoding)


@pytest.mark.parametrize("text", ["café", "naïve", "tést", "é", "€"])
def test_datamatrix_data_warns_on_non_ascii_in_compat(text):
    with pytest.warns(DataMatrixNonAsciiWarning):
        DataMatrixData(text)


@pytest.mark.parametrize("text", ["café", "naïve", "tést", "é", "€"])
def test_datamatrix_data_raises_on_non_ascii_in_ascii(text):
    with pytest.raises(PyStrichInvalidInput):
        DataMatrixData(text, encoding="ascii")


def test_datamatrix_data_unknown_encoding_raises():
    with pytest.raises(PyStrichInvalidOption):
        DataMatrixData("abc", encoding="bogus")


@pytest.mark.parametrize("bad_segment", [
    pytest.param(123, id="int"),
    pytest.param(["abc"], id="list"),
    pytest.param(b"abc", id="bytes"),
    pytest.param(None, id="none"),
])
def test_datamatrix_data_rejects_non_str_segments(bad_segment):
    with pytest.raises(TypeError):
        DataMatrixData(bad_segment)


def test_datamatrix_data_equality_distinguishes_encoding():
    compat = DataMatrixData("abc", encoding="compat")
    strict = DataMatrixData("abc", encoding="ascii")
    assert compat != strict
    assert hash(compat) != hash(strict)


def test_datamatrix_data_concat_warns_on_non_ascii():
    with pytest.warns(DataMatrixNonAsciiWarning):
        DataMatrixData("abc") + "café"


def test_encoder_warns_on_non_ascii():
    with pytest.warns(DataMatrixNonAsciiWarning):
        DataMatrixEncoder("café")


def test_fnc1_concat_with_non_ascii_raises():
    """Modern path (FNC1 + ...) raises on non-ASCII, no compat-warn fallback."""
    with pytest.raises(PyStrichInvalidInput):
        FNC1 + "café"


@pytest.mark.parametrize("text, expected_segments, expected_warning_cls", [
    pytest.param("hello", ("hello",), None, id="ascii-only"),
    pytest.param("\xe7", (FNC1,), Fnc1WorkaroundCompatWarning, id="just-chr231"),
    pytest.param("\xe7hello", (FNC1, "hello"), Fnc1WorkaroundCompatWarning, id="leading-chr231"),
    pytest.param("\xe7a\xe7b", (FNC1, "a", FNC1, "b"), Fnc1WorkaroundCompatWarning, id="leading-and-middle"),
    pytest.param("\xe7\xe7", (FNC1, FNC1), Fnc1WorkaroundCompatWarning, id="leading-consecutive"),
    pytest.param("hello\xe7", ("hello\xe7",), DataMatrixNonAsciiWarning, id="trailing-chr231-passthrough"),
    pytest.param("a\xe7b", ("a\xe7b",), DataMatrixNonAsciiWarning, id="middle-chr231-passthrough"),
    pytest.param("a\xe7\xe7b", ("a\xe7\xe7b",), DataMatrixNonAsciiWarning, id="middle-consecutive-passthrough"),
    pytest.param("café", ("café",), DataMatrixNonAsciiWarning, id="non-ascii-no-chr231"),
])
def test_fnc1_workaround_compat(text, expected_segments, expected_warning_cls):
    if expected_warning_cls is None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", PyStrichWarning)
            result = fnc1_workaround_compat(text)
    else:
        with pytest.warns(expected_warning_cls):
            result = fnc1_workaround_compat(text)
    assert result.segments == expected_segments
