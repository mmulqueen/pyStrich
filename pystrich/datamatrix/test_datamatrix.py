"""Unit test for 2D datamatrix barcode encoder"""

import warnings

import pytest

from pystrich.datamatrix import (
    FNC1,
    DataMatrixData,
    DataMatrixEncoder,
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
from pystrich.marks import MarkShape

_API_FORMS = [
    pytest.param(lambda s: s, id="compat"),
    pytest.param(lambda s: DataMatrixData(s, encoding="ascii"), id="modern"),
]


@pytest.mark.parametrize("wrap", _API_FORMS)
@pytest.mark.parametrize(
    "string",
    [
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
    ],
)
def test_encode_decode(string, wrap, tmp_path, dmtxread):
    img = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(wrap(string)).save(str(img))
    assert dmtxread(img) == string


@pytest.mark.parametrize("cellsize", [5, 10])
@pytest.mark.parametrize("wrap", _API_FORMS)
@pytest.mark.parametrize(
    "string",
    [
        "banana",
        "http://www.hudora.de/track/00340059980000001319/",
        "This sentence will need multiple datamatrix regions. Tests to see whether bug 2 is fixed.",
    ],
)
def test_svg_round_trip(string, wrap, cellsize, tmp_path, svg_to_png, dmtxread):
    """SVG output rasterised with librsvg decodes back to the original string."""
    svg = tmp_path / "datamatrix-test.svg"
    png = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(wrap(string)).save_svg(str(svg), cellsize=cellsize)
    svg_to_png(svg, png)
    assert dmtxread(png) == string


@pytest.mark.parametrize("cellsize", [5, 10])
@pytest.mark.parametrize("wrap", _API_FORMS)
@pytest.mark.parametrize(
    "string",
    [
        "banana",
        "http://www.hudora.de/track/00340059980000001319/",
        "This sentence will need multiple datamatrix regions. Tests to see whether bug 2 is fixed.",
    ],
)
def test_eps_round_trip(string, wrap, cellsize, tmp_path, eps_to_png, dmtxread):
    """EPS output rasterised with Ghostscript decodes back to the original string."""
    eps = tmp_path / "datamatrix-test.eps"
    png = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(wrap(string)).save_eps(str(eps), cellsize=cellsize)
    eps_to_png(eps, png)
    assert dmtxread(png) == string


def test_svg_round_trip_circular_cells(tmp_path, svg_to_png, dmtxread):
    """Circular-cell SVG output rasterises and decodes back to the original string."""
    string = "banana"
    svg = tmp_path / "datamatrix-test.svg"
    png = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(string).save_svg(str(svg), mark_shape=MarkShape.CIRCULAR_CELLS)
    svg_to_png(svg, png)
    assert dmtxread(png) == string


def test_eps_round_trip_circular_cells(tmp_path, eps_to_png, dmtxread):
    """Circular-cell EPS output rasterises and decodes back to the original string."""
    string = "banana"
    eps = tmp_path / "datamatrix-test.eps"
    png = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(string).save_eps(str(eps), mark_shape=MarkShape.CIRCULAR_CELLS)
    eps_to_png(eps, png)
    assert dmtxread(png) == string


def test_dxf_round_trip_circular_cells(tmp_path, dxf_to_svg, svg_to_png, dmtxread):
    """Circular-cell DXF output (HATCH entities) round-trips through ezdxf."""
    # cellsize=2: ezdxf renders modelspace in mm, so a 30-module symbol with
    # cellsize=5 rasterises at ~880 px and the crisp inter-circle gaps defeat
    # the decoder; cellsize=2 keeps the antialiasing soft enough.
    string = "banana"
    cellsize = 2
    dxf = tmp_path / "datamatrix-test.dxf"
    svg = tmp_path / "datamatrix-test.svg"
    png = tmp_path / "datamatrix-test.png"
    dxf.write_text(
        DataMatrixEncoder(string).get_dxf(
            cellsize=cellsize, inverse=False, mark_shape=MarkShape.CIRCULAR_CELLS
        ),
        encoding="ascii",
    )
    dxf_to_svg(dxf, svg, inverse=False, margin_mm=2 * cellsize)
    svg_to_png(svg, png)
    assert dmtxread(png) == string


@pytest.mark.parametrize("inverse", [True, False])
@pytest.mark.parametrize("wrap", _API_FORMS)
@pytest.mark.parametrize(
    "string",
    [
        "banana",
        "http://www.hudora.de/track/00340059980000001319/",
        "This sentence will need multiple datamatrix regions. Tests to see whether bug 2 is fixed.",
    ],
)
def test_dxf_round_trip(string, wrap, inverse, tmp_path, dxf_to_svg, svg_to_png, dmtxread):
    """DXF output rendered to SVG via ezdxf, rasterised, decodes back to the original string."""
    cellsize = 5
    dxf = tmp_path / "datamatrix-test.dxf"
    svg = tmp_path / "datamatrix-test.svg"
    png = tmp_path / "datamatrix-test.png"
    dxf.write_text(
        DataMatrixEncoder(wrap(string)).get_dxf(cellsize=cellsize, inverse=inverse),
        encoding="ascii",
    )
    if inverse:
        dxf_to_svg(dxf, svg, inverse=True)
    else:
        # inverse=False emits no geometry for the light quiet-zone cells, so
        # the SVG bounding box hugs the dark modules; pad a 2-module margin
        # back in for the decoder.
        dxf_to_svg(dxf, svg, inverse=False, margin_mm=2 * cellsize)
    svg_to_png(svg, png)
    assert dmtxread(png) == string


@pytest.mark.parametrize("wrap", _API_FORMS)
@pytest.mark.parametrize(
    "text, expected_codewords",
    [
        pytest.param("hi", [105, 106, 129, 74, 235, 130, 61, 159], id="hi"),
        pytest.param(
            "banana",
            [99, 98, 111, 98, 111, 98, 129, 56, 227, 236, 237, 109, 16, 221, 163, 60, 171, 76],
            id="banana",
        ),
        pytest.param(
            "wer das liest ist 31337",
            [
                120,
                102,
                115,
                33,
                101,
                98,
                116,
                33,
                109,
                106,
                102,
                116,
                117,
                33,
                106,
                116,
                117,
                33,
                161,
                163,
                56,
                129,
                83,
                116,
                244,
                3,
                40,
                16,
                79,
                220,
                144,
                76,
                17,
                186,
                175,
                211,
                244,
                84,
                59,
                71,
            ],
            id="wer-das-liest",
        ),
    ],
)
def test_encoding(text, wrap, expected_codewords):
    enc = TextEncoder()
    assert [ord(c) for c in enc.encode(wrap(text))] == expected_codewords


@pytest.mark.parametrize(
    "quiet_zone, expected_diff",
    [
        pytest.param(0, -DATAMATRIX_DEFAULT_QUIET_ZONE * 2, id="zero"),
        pytest.param(10, (10 - DATAMATRIX_DEFAULT_QUIET_ZONE) * 2, id="ten"),
    ],
)
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


@pytest.mark.parametrize(
    "payload, expected",
    [
        pytest.param(FNC1 + "0100312345678901", "|0100312345678901", id="simple_gs1"),
        pytest.param(FNC1 + "10ABC" + FNC1 + "21XYZ", "|10ABC|21XYZ", id="separated"),
        pytest.param(FNC1 + "1" + FNC1 + "21XYZ", "|1|21XYZ", id="unpaired_digit"),
    ],
)
def test_gs1_fnc1(payload, expected, tmp_path, dmtxread):
    """The FNC1 marker emits codeword 232 directly (no chr(231) trick)."""
    img = tmp_path / "gs1.png"
    DataMatrixEncoder(payload).save(str(img))
    assert dmtxread(img, gs1="|") == expected


@pytest.mark.parametrize(
    "data, expected_encoding",
    [
        pytest.param(FNC1 + "abc", "ascii", id="codeword-then-str"),
        pytest.param("abc" + FNC1, "ascii", id="str-then-codeword"),
        pytest.param(FNC1 + FNC1, "ascii", id="codeword-then-codeword"),
        pytest.param(
            FNC1 + DataMatrixData("abc", encoding="compat"),
            "compat",
            id="codeword-preserves-compat-data-encoding",
        ),
        pytest.param(
            DataMatrixData(encoding="compat") + "abc" + FNC1,
            "compat",
            id="compat-data-then-str-then-codeword",
        ),
        pytest.param(
            DataMatrixData("abc", encoding="ascii") + "def", "ascii", id="ascii-data-then-str"
        ),
        pytest.param(
            DataMatrixData("a", encoding="ascii") + DataMatrixData("b", encoding="ascii"),
            "ascii",
            id="ascii-data-then-ascii-data",
        ),
        pytest.param(
            DataMatrixData("a", encoding="iso-8859-1") + DataMatrixData("b", encoding="iso-8859-1"),
            "iso-8859-1",
            id="latin1-data-then-latin1-data",
        ),
    ],
)
def test_concat_returns_datamatrix_data(data, expected_encoding):
    assert isinstance(data, DataMatrixData)
    assert data.encoding == expected_encoding


@pytest.mark.parametrize(
    "lhs_encoding, rhs_encoding",
    [
        ("compat", "ascii"),
        ("ascii", "compat"),
    ],
)
def test_concat_with_mismatched_encodings_raises(lhs_encoding, rhs_encoding):
    with pytest.raises(PyStrichInvalidOption):
        DataMatrixData("a", encoding=lhs_encoding) + DataMatrixData("b", encoding=rhs_encoding)


@pytest.mark.parametrize("text", ["café", "naïve", "tést", "é", "€"])
def test_datamatrix_data_warns_on_non_ascii_in_compat(text):
    with pytest.warns(DataMatrixNonAsciiWarning):
        DataMatrixData(text, encoding="compat")


@pytest.mark.parametrize("text", ["café", "naïve", "tést", "é", "€"])
def test_datamatrix_data_raises_on_non_ascii_in_ascii(text):
    with pytest.raises(PyStrichInvalidInput):
        DataMatrixData(text, encoding="ascii")


def test_datamatrix_data_unknown_encoding_raises():
    with pytest.raises(PyStrichInvalidOption):
        DataMatrixData("abc", encoding="bogus")


@pytest.mark.parametrize(
    "encoding, text, expected_suggestion",
    [
        pytest.param("ascii", "café", "iso-8859-1", id="ascii-fits-latin1"),
        pytest.param("ascii", "中文", "utf-8", id="ascii-needs-utf8"),
        pytest.param("iso-8859-1", "中文", "utf-8", id="latin1-needs-utf8"),
    ],
)
def test_validation_error_suggests_encoding(encoding, text, expected_suggestion):
    with pytest.raises(PyStrichInvalidInput) as exc_info:
        DataMatrixData(text, encoding=encoding)
    msg = str(exc_info.value)
    assert f"DataMatrixData({text!r}, encoding={expected_suggestion!r})" in msg
    assert "auto_encoding=True" in msg


@pytest.mark.parametrize(
    "bad_segment",
    [
        pytest.param(123, id="int"),
        pytest.param(["abc"], id="list"),
        pytest.param(b"abc", id="bytes"),
        pytest.param(None, id="none"),
    ],
)
def test_datamatrix_data_rejects_non_str_segments(bad_segment):
    with pytest.raises(TypeError):
        DataMatrixData(bad_segment, encoding="compat")


def test_datamatrix_data_equality_distinguishes_encoding():
    compat = DataMatrixData("abc", encoding="compat")
    strict = DataMatrixData("abc", encoding="ascii")
    assert compat != strict
    assert hash(compat) != hash(strict)


def test_datamatrix_data_concat_warns_on_non_ascii():
    with pytest.warns(DataMatrixNonAsciiWarning):
        DataMatrixData("abc", encoding="compat") + "café"


def test_encoder_warns_on_non_ascii():
    with pytest.warns(DataMatrixNonAsciiWarning):
        DataMatrixEncoder("café")


def test_fnc1_concat_with_non_ascii_raises():
    """Modern path (FNC1 + ...) raises on non-ASCII, no compat-warn fallback."""
    with pytest.raises(PyStrichInvalidInput):
        FNC1 + "café"


@pytest.mark.parametrize(
    "text, expected_segments, expected_warning_cls",
    [
        pytest.param("hello", ("hello",), None, id="ascii-only"),
        pytest.param("\xe7", (FNC1,), Fnc1WorkaroundCompatWarning, id="just-chr231"),
        pytest.param(
            "\xe7hello", (FNC1, "hello"), Fnc1WorkaroundCompatWarning, id="leading-chr231"
        ),
        pytest.param(
            "\xe7a\xe7b",
            (FNC1, "a", FNC1, "b"),
            Fnc1WorkaroundCompatWarning,
            id="leading-and-middle",
        ),
        pytest.param(
            "\xe7\xe7", (FNC1, FNC1), Fnc1WorkaroundCompatWarning, id="leading-consecutive"
        ),
        pytest.param(
            "hello\xe7", ("hello\xe7",), DataMatrixNonAsciiWarning, id="trailing-chr231-passthrough"
        ),
        pytest.param(
            "a\xe7b", ("a\xe7b",), DataMatrixNonAsciiWarning, id="middle-chr231-passthrough"
        ),
        pytest.param(
            "a\xe7\xe7b",
            ("a\xe7\xe7b",),
            DataMatrixNonAsciiWarning,
            id="middle-consecutive-passthrough",
        ),
        pytest.param("café", ("café",), DataMatrixNonAsciiWarning, id="non-ascii-no-chr231"),
    ],
)
def test_fnc1_workaround_compat(text, expected_segments, expected_warning_cls):
    if expected_warning_cls is None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", PyStrichWarning)
            result = fnc1_workaround_compat(text)
    else:
        with pytest.warns(expected_warning_cls):
            result = fnc1_workaround_compat(text)
    assert result.segments == expected_segments


def test_encoding_latin1_upper_shift():
    """Latin-1 chars >127 emit codeword 235 (Upper Shift) followed by the offset char."""
    enc = TextEncoder()
    codewords = [ord(c) for c in enc.encode(DataMatrixData("café", encoding="iso-8859-1"))]
    # 'c'->100, 'a'->98, 'f'->103, 'é' (ord 233) -> 235 then chr(105)+1 = 106
    assert codewords[:5] == [100, 98, 103, 235, 106]


def test_compat_does_not_emit_upper_shift():
    """Compat-mode latin-1 chars keep the legacy +1 offset (broken), no Upper Shift gating."""
    enc = TextEncoder()
    with pytest.warns(DataMatrixNonAsciiWarning):
        codewords = [ord(c) for c in enc.encode("café")]
    # 'é' under compat falls through append_ascii_char -> chr(234), no leading 235.
    assert codewords[:4] == [100, 98, 103, 234]


@pytest.mark.parametrize(
    "text",
    [
        "café",
        "naïve",
        "tést",
        "é",
        "à",
        "ça",
        "façade",
        "ç",
        "plain",
        "1²34",
    ],
)
def test_encode_decode_latin1(text, tmp_path, dmtxread):
    """Latin-1 strings round-trip through DataMatrixEncoder + dmtxread."""
    img = tmp_path / "latin1.png"
    DataMatrixEncoder(DataMatrixData(text, encoding="iso-8859-1")).save(str(img))
    assert dmtxread(img, encoding="iso-8859-1") == text


@pytest.mark.parametrize("text", ["€", "中文", "🙂"])
def test_datamatrix_data_raises_on_non_latin1_in_latin1(text):
    with pytest.raises(PyStrichInvalidInput):
        DataMatrixData(text, encoding="iso-8859-1")


def test_encoding_utf8_eci_prefix():
    """UTF-8 mode emits the ECI 26 prefix (codewords 241, 27) once at the start."""
    enc = TextEncoder()
    codewords = [ord(c) for c in enc.encode(DataMatrixData("hi", encoding="utf-8"))]
    assert codewords[:2] == [241, 27]


def test_encoding_utf8_byte_iteration():
    """Each UTF-8 byte > 127 emits Upper Shift; ASCII bytes pass through unchanged."""
    enc = TextEncoder()
    codewords = [ord(c) for c in enc.encode(DataMatrixData("é", encoding="utf-8"))]
    # 'é' UTF-8 -> bytes 0xC3, 0xA9.
    # 0xC3 (195) -> 235, (195-128)+1 = 68; 0xA9 (169) -> 235, (169-128)+1 = 42.
    assert codewords[:6] == [241, 27, 235, 68, 235, 42]


@pytest.mark.parametrize(
    "text",
    [
        "café",
        "€",
        "中文",
        "🙂",
        "naïve",
        "plain ascii",
        "ça",
    ],
)
def test_encode_decode_utf8(text, tmp_path, dmtxread):
    """UTF-8 strings round-trip through DataMatrixEncoder + dmtxread."""
    img = tmp_path / "utf8.png"
    DataMatrixEncoder(DataMatrixData(text, encoding="utf-8")).save(str(img))
    # libdmtx prefixes ECI-encoded output with a raw byte equal to the ECI
    # value (0x1A = 26 for UTF-8); no dmtxread flag suppresses it.
    assert dmtxread(img, encoding="utf-8").removeprefix("\x1a") == text


def test_datamatrix_data_requires_encoding_choice():
    with pytest.raises(PyStrichInvalidOption) as exc_info:
        DataMatrixData("hello")
    msg = str(exc_info.value)
    assert "encoding=" in msg
    assert "auto_encoding=True" in msg


@pytest.mark.parametrize(
    "text, expected_encoding",
    [
        pytest.param("hello", "ascii", id="ascii-fits"),
        pytest.param("café", "iso-8859-1", id="escalates-to-latin1"),
        pytest.param("中文", "utf-8", id="escalates-to-utf8"),
        pytest.param("🙂", "utf-8", id="emoji-escalates-to-utf8"),
    ],
)
def test_auto_encoding_picks_narrowest_fit(text, expected_encoding):
    assert DataMatrixData(text, auto_encoding=True).encoding == expected_encoding


def test_auto_encoding_survives_concat():
    """auto_encoding propagates through concat and re-derives for the combined segments."""
    parent = DataMatrixData("a", auto_encoding=True)
    assert parent.encoding == "ascii"
    child = parent + "café"
    assert child.auto_encoding is True
    assert child.encoding == "iso-8859-1"


def test_auto_encoding_concat_with_two_auto_re_derives():
    """Two auto-encoded values combine and re-derive against the merged segments."""
    ascii_auto = DataMatrixData("a", auto_encoding=True)
    latin1_auto = DataMatrixData("é", auto_encoding=True)
    assert ascii_auto.encoding == "ascii"
    assert latin1_auto.encoding == "iso-8859-1"
    combined = ascii_auto + latin1_auto
    assert combined.auto_encoding is True
    assert combined.encoding == "iso-8859-1"
