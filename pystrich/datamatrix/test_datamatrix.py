"""Unit test for 2D datamatrix barcode encoder"""

import warnings
from datetime import timedelta

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pystrich.datamatrix import (
    FNC1,
    DataMatrixData,
    DataMatrixEncoder,
)
from pystrich.datamatrix.data import fnc1_workaround_compat
from pystrich.datamatrix.placement import DataMatrixPlacer
from pystrich.datamatrix.renderer import DATAMATRIX_DEFAULT_QUIET_ZONE
from pystrich.datamatrix.textencoder import (
    DataTooLongForImplementation,
    TextEncoder,
    _randomise_pad,
)
from pystrich.exceptions import (
    DataMatrixNonAsciiWarning,
    Fnc1WorkaroundCompatWarning,
    PyStrichInvalidInput,
    PyStrichInvalidOption,
    PyStrichWarning,
)
from pystrich.gs1 import GS1Fixed, GS1Variable
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
        # C40-picking payload (uppercase + digits + dashes): DP picks C40 prefix + ASCII tail.
        "ROUTE-AB1234-DESTINATION-CD5678",
        # X12-picking payload (CR-delimited record shape that X12 exists for).
        "ABCDEFG\rHIJKLMN\rOPQRST",
    ],
)
@pytest.mark.png
def test_encode_decode(string, wrap, tmp_path, dmtxread, decode_barcode):
    img = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder(wrap(string)).save(str(img))
    assert dmtxread(img) == string
    assert decode_barcode(img) == string


@st.composite
def _datamatrix_payload(draw):
    parts = draw(
        st.lists(
            st.one_of(
                st.text(alphabet="0123456789", min_size=1, max_size=8),
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=8),
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
                st.text(alphabet="!\"#$%&'()*+,-./:;<=>?@[\\]^_", min_size=1, max_size=4),
                st.text(alphabet="`{|}~", min_size=1, max_size=2),
                # zxing-cpp renders C0 controls outside \t\n\r as <NAME> escapes in `.text`.
                # \r lives in the X12 trigger band so it clusters with * and >.
                st.text(alphabet="\t\n", min_size=1, max_size=2),
                st.text(alphabet="\r*>", min_size=1, max_size=2),
                # 0xA0+ skips the C1 control block (0x80-0x9F).
                st.text(
                    st.characters(min_codepoint=0xA0, max_codepoint=0xFF),
                    min_size=1,
                    max_size=4,
                ),
                st.text(
                    st.characters(
                        min_codepoint=0x0100,
                        max_codepoint=0x2FFF,
                        exclude_categories=("Cs", "Cc"),
                    ),
                    min_size=1,
                    max_size=4,
                ),
            ),
            min_size=1,
            max_size=6,
        )
    )
    return "".join(parts)


@given(text=_datamatrix_payload())
@settings(
    max_examples=100,
    deadline=timedelta(seconds=2),
    print_blob=True,
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.data_too_large,
        HealthCheck.filter_too_much,
    ],
)
@pytest.mark.png
def test_property_roundtrip(text, tmp_path, decode_barcode):
    """Class-banded payloads roundtrip through encode + render + decode."""
    img = tmp_path / "datamatrix-property.png"
    DataMatrixEncoder(DataMatrixData(text, auto_encoding=True)).save(str(img))
    assert decode_barcode(img) == text


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


@pytest.mark.parametrize(
    "quiet_zone, expected_diff",
    [
        pytest.param(0, -DATAMATRIX_DEFAULT_QUIET_ZONE * 2, id="zero"),
        pytest.param(10, (10 - DATAMATRIX_DEFAULT_QUIET_ZONE) * 2, id="ten"),
    ],
)
@pytest.mark.png
def test_quiet_zone_changes_width(quiet_zone, expected_diff):
    """Width differs from the default by 2 * (quiet_zone - default) on each axis."""
    # .width is populated by the renderer, so each encoder must render before comparison.
    default_encoder = DataMatrixEncoder("test")
    default_encoder.get_imagedata()
    custom_encoder = DataMatrixEncoder("test", quiet_zone=quiet_zone)
    custom_encoder.get_imagedata()
    assert custom_encoder.width - default_encoder.width == expected_diff


@pytest.mark.png
def test_quiet_zone_round_trip(tmp_path, dmtxread):
    # quiet_zone=0 is excluded because dmtxread fails to detect the symbol without padding.
    img = tmp_path / "datamatrix-test.png"
    DataMatrixEncoder("test", quiet_zone=10).save(str(img))
    assert dmtxread(img) == "test"


@pytest.mark.png
def test_get_imagedata_matches_save(tmp_path):
    img = tmp_path / "datamatrix-test.png"
    encoder = DataMatrixEncoder("Hello world")
    encoder.save(str(img))
    assert img.read_bytes() == encoder.get_imagedata()


@pytest.mark.png
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
@pytest.mark.png
def test_gs1_fnc1(payload, expected, tmp_path, dmtxread):
    """The FNC1 marker emits codeword 232 directly (no chr(231) trick)."""
    img = tmp_path / "gs1.png"
    DataMatrixEncoder(payload).save(str(img))
    assert dmtxread(img, gs1="|") == expected


@pytest.mark.parametrize(
    "fields, expected_segments",
    [
        pytest.param(
            (GS1Fixed("01", "09501234543213"),),
            (FNC1, "0109501234543213"),
            id="single-fixed",
        ),
        pytest.param(
            (GS1Variable("10", "BF07"),),
            (FNC1, "10BF07"),
            id="single-variable-last-no-trailing-fnc1",
        ),
        pytest.param(
            (
                GS1Fixed("01", "09501234543213"),
                GS1Fixed("17", "261231"),
                GS1Variable("10", "BF07"),
            ),
            (FNC1, "01095012345432131726123110BF07"),
            id="fixed-fixed-variable-no-separators",
        ),
        pytest.param(
            (GS1Variable("10", "BF07"), GS1Variable("21", "19890519")),
            (FNC1, "10BF07", FNC1, "2119890519"),
            id="variable-not-last-gets-separator",
        ),
    ],
)
def test_datamatrix_data_gs1_segment_structure(fields, expected_segments):
    data = DataMatrixData.gs1(*fields)
    assert data.segments == expected_segments
    assert data.encoding == "ascii"


@pytest.mark.png
def test_datamatrix_data_gs1_round_trip(tmp_path, dmtxread):
    data = DataMatrixData.gs1(
        GS1Fixed("01", "09501234543213"),
        GS1Fixed("17", "261231"),
        GS1Variable("10", "BF07"),
    )
    img = tmp_path / "gs1.png"
    DataMatrixEncoder(data).save(str(img))
    assert dmtxread(img, gs1="|") == "|0109501234543213" + "17261231" + "10BF07"


@pytest.mark.parametrize(
    "fields, reason",
    [
        pytest.param((), "at least one", id="empty"),
        pytest.param(("01", "x"), "GS1Fixed or GS1Variable", id="bare-str"),
        pytest.param((GS1Fixed("01", "x"), "extra"), "GS1Fixed or GS1Variable", id="mixed-str"),
    ],
)
def test_datamatrix_data_gs1_rejects_bad_arguments(fields, reason):
    with pytest.raises(PyStrichInvalidOption, match=reason):
        DataMatrixData.gs1(*fields)


@pytest.mark.parametrize(
    "data, expected_encoding",
    [
        pytest.param(FNC1 + "abc", "ascii", id="codeword-then-str"),
        pytest.param("abc" + FNC1, "ascii", id="str-then-codeword"),
        pytest.param(FNC1 + FNC1, "ascii", id="codeword-then-codeword"),
        pytest.param(
            FNC1 + DataMatrixData("abc", encoding="compat"),
            "ascii",
            id="codeword-preserves-compat-data-encoding",
        ),
        pytest.param(
            DataMatrixData(encoding="compat") + "abc" + FNC1,
            "ascii",
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
        ("ascii", "iso-8859-1"),
        ("iso-8859-1", "utf-8"),
        ("ascii", "utf-8"),
    ],
)
def test_concat_with_mismatched_encodings_raises(lhs_encoding, rhs_encoding):
    with pytest.raises(PyStrichInvalidOption):
        DataMatrixData("a", encoding=lhs_encoding) + DataMatrixData("b", encoding=rhs_encoding)


@pytest.mark.parametrize("text", ["café", "naïve", "tést", "é"])
def test_datamatrix_data_warns_on_non_ascii_in_compat(text):
    with pytest.warns(DataMatrixNonAsciiWarning):
        DataMatrixData(text, encoding="compat")


def test_datamatrix_data_compat_rejects_codepoint_above_254():
    """Compat replaces each high codepoint with ``DataMatrixCodeword(ord + 1)``;
    codepoints whose ``ord + 1`` exceeds 255 (e.g. '€') aren't representable."""
    with pytest.warns(DataMatrixNonAsciiWarning), pytest.raises(ValueError, match="codeword"):
        DataMatrixData("€", encoding="compat")


@pytest.mark.parametrize("text", ["café", "naïve", "tést", "é", "€"])
def test_datamatrix_data_raises_on_non_ascii_in_ascii(text):
    with pytest.raises(PyStrichInvalidInput):
        DataMatrixData(text, encoding="ascii")


def test_datamatrix_data_unknown_encoding_raises():
    with pytest.raises(PyStrichInvalidOption):
        DataMatrixData("abc", encoding="bogus")  # type: ignore[arg-type]


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


def test_compat_resolves_to_ascii_after_init():
    """Compat is a one-shot init option: post-construction the data is
    indistinguishable from encoding='ascii' (for ASCII-only input)."""
    compat = DataMatrixData("abc", encoding="compat")
    strict = DataMatrixData("abc", encoding="ascii")
    assert compat == strict
    assert hash(compat) == hash(strict)
    assert compat.encoding == "ascii"


def test_compat_init_then_concat_non_ascii_raises():
    """Compat doesn't survive __add__: after the legacy transform runs at
    init, the result is ASCII-encoded and further non-ASCII raises."""
    with pytest.raises(PyStrichInvalidInput):
        DataMatrixData("abc", encoding="compat") + "café"


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
        pytest.param("hello\xe7", ("hello\xe7",), None, id="trailing-chr231-passthrough"),
        pytest.param("a\xe7b", ("a\xe7b",), None, id="middle-chr231-passthrough"),
        pytest.param("a\xe7\xe7b", ("a\xe7\xe7b",), None, id="middle-consecutive-passthrough"),
        pytest.param("café", ("café",), None, id="non-ascii-no-chr231"),
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
    """Latin-1 emits ECI 3 prologue then codeword 235 (Upper Shift) for high bytes."""
    enc = TextEncoder()
    codewords = enc.encode(DataMatrixData("café", encoding="iso-8859-1"))
    # ECI 3 -> [241, 4]; 'c'->100, 'a'->98, 'f'->103, 'é' (ord 233) -> 235 then chr(105)+1 = 106
    assert codewords[:7] == [241, 4, 100, 98, 103, 235, 106]


def test_compat_does_not_emit_upper_shift():
    """Compat-mode latin-1 chars keep the legacy +1 offset (broken), no Upper Shift gating."""
    enc = TextEncoder()
    with pytest.warns(DataMatrixNonAsciiWarning):
        data = DataMatrixData("café", encoding="compat")
    codewords = enc.encode(data)
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
@pytest.mark.png
def test_encode_decode_latin1(text, tmp_path, dmtxread):
    """Latin-1 strings round-trip through DataMatrixEncoder + dmtxread."""
    img = tmp_path / "latin1.png"
    DataMatrixEncoder(DataMatrixData(text, encoding="iso-8859-1")).save(str(img))
    # libdmtx prefixes ECI-encoded output with a raw byte equal to the ECI
    # value (0x03 = 3 for ISO-8859-1); no dmtxread flag suppresses it.
    assert dmtxread(img, encoding="iso-8859-1").removeprefix("\x03") == text


@pytest.mark.parametrize("text", ["€", "中文", "🙂"])
def test_datamatrix_data_raises_on_non_latin1_in_latin1(text):
    with pytest.raises(PyStrichInvalidInput):
        DataMatrixData(text, encoding="iso-8859-1")


def test_encoding_utf8_eci_prefix():
    """UTF-8 mode emits the ECI 26 prefix (codewords 241, 27) once at the start."""
    enc = TextEncoder()
    codewords = enc.encode(DataMatrixData("hi", encoding="utf-8"))
    assert codewords[:2] == [241, 27]


def test_encoding_utf8_byte_iteration():
    """Each UTF-8 byte > 127 emits Upper Shift; ASCII bytes pass through unchanged."""
    enc = TextEncoder()
    codewords = enc.encode(DataMatrixData("é", encoding="utf-8"))
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
        # Mixed payloads where the DP picks a non-ASCII mode for the bulk
        # then switches back to ASCII to encode the UTF-8 high bytes.
        "café BATCH-A1234-DESTINATION-XYZ",  # C40 run between high-byte ASCII
        "wer das liest ist 31337 — café",  # TEXT run, em-dash + 'é' in tail
        "ORDER\rITEM\rQTY\rPRICE\rcafé",  # X12 can't carry 'é' — DP closes for tail
    ],
)
@pytest.mark.png
def test_encode_decode_utf8(text, tmp_path, dmtxread, decode_barcode):
    """UTF-8 strings round-trip through DataMatrixEncoder + dmtxread + zxing-cpp."""
    img = tmp_path / "utf8.png"
    DataMatrixEncoder(DataMatrixData(text, encoding="utf-8")).save(str(img))
    # libdmtx prefixes ECI-encoded output with a raw byte equal to the ECI
    # value (0x1A = 26 for UTF-8); no dmtxread flag suppresses it.
    assert dmtxread(img, encoding="utf-8").removeprefix("\x1a") == text
    assert decode_barcode(img) == text


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


@pytest.mark.parametrize(
    "position, expected",
    [
        pytest.param(1, 25, id="P1-sum-overflow"),
        pytest.param(2, 175, id="P2-sum-fits"),
        pytest.param(27, 104, id="P27-sum-overflow"),
        pytest.param(28, 254, id="P28-boundary-bug-case"),
        pytest.param(29, 150, id="P29-sum-fits"),
    ],
)
def test_pad_randomisation_matches_spec(position, expected):
    """Subtract 254 only when sum exceeds 254; the boundary at sum==254 must keep 254."""
    assert _randomise_pad(position) == expected


def test_set_corner_module_applies_pattern_when_corner_unset():
    placer = DataMatrixPlacer()
    placer.matrix = [[None] * 4 for _ in range(4)]
    placer.rows, placer.cols = 4, 4
    placer._set_corner_module()
    assert (placer.matrix[3][3], placer.matrix[2][2]) == (1, 1)
    assert (placer.matrix[3][2], placer.matrix[2][3]) == (0, 0)


def test_set_corner_module_noop_when_corner_already_placed():
    placer = DataMatrixPlacer()
    placer.matrix = [[None] * 4 for _ in range(4)]
    placer.matrix[3][3] = 0  # snake already placed something here
    placer.rows, placer.cols = 4, 4
    placer._set_corner_module()
    assert placer.matrix[3][3] == 0
    assert placer.matrix[2][2] is None


@pytest.mark.png
def test_corner_module_round_trip_at_12x12(tmp_path, dmtxread):
    """End-to-end check that the corner-fill is wired into place() at an affected size."""
    # 'a'*4 = 4 codewords, lands in size_index 1 (12x12), which the probe shows
    # is one of the sizes whose snake leaves the bottom-right corner untouched.
    payload = "aaaa"
    img = tmp_path / "corner.png"
    DataMatrixEncoder(payload).save(str(img))
    assert dmtxread(img) == payload


@pytest.mark.parametrize("payload_len", [400, 1000, 2000])
@pytest.mark.png
def test_large_payload_round_trip(payload_len, tmp_path, dmtxread):
    """Sizes >=52x52 use interleaved Reed-Solomon blocks; verify they decode."""
    payload = "a" * payload_len
    img = tmp_path / "large.png"
    DataMatrixEncoder(DataMatrixData(payload, encoding="ascii")).save(str(img))
    assert dmtxread(img) == payload


def test_capacity_overflow_raises():
    """Inputs exceeding the largest 144x144 symbol raise DataTooLongForImplementation."""
    enc = TextEncoder()
    with pytest.raises(DataTooLongForImplementation):
        enc.encode(DataMatrixData("A" * 3000, encoding="ascii"))


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("ABCDEFGHIJKLMNOP", id="uppercase-c40"),
        pytest.param("abcdefghijklmnop", id="lowercase-text"),
        pytest.param("\rABCDEFGH*>1234", id="x12-mix"),
        pytest.param("Hello, World! 12345 ABCDEFG", id="cross-mode-optimum"),
        pytest.param("ABCDEFGH 12345 abcdefgh", id="alternating-cases"),
    ],
)
@pytest.mark.png
def test_multi_mode_round_trip(text, tmp_path, dmtxread):
    """Inputs that exercise C40, Text or X12 paths still decode correctly."""
    img = tmp_path / "compact.png"
    DataMatrixEncoder(DataMatrixData(text, encoding="ascii")).save(str(img))
    assert dmtxread(img) == text


@pytest.mark.png
def test_trailing_unlatch_dropped_when_symbol_fits_exactly(tmp_path, dmtxread):
    """When dropping the trailing Unlatch lands on a valid symbol size, do so.

    ``"_ABCDEFGHI"`` encodes as 1 ASCII + C40 segment ending in Unlatch = 9 cw.
    Dropping the Unlatch fits size 8 (size_index=2) exactly; keeping it would
    spill into size 12 (size_index=3).
    """
    enc = TextEncoder()
    cws = enc.encode(DataMatrixData("_ABCDEFGHI", encoding="ascii"))
    assert enc.size_index == 2
    assert cws[:8] == [96, 230, 89, 233, 109, 36, 128, 95]
    img = tmp_path / "exact-fit.png"
    DataMatrixEncoder(DataMatrixData("_ABCDEFGHI", encoding="ascii")).save(str(img))
    assert dmtxread(img) == "_ABCDEFGHI"


def test_fnc1_routes_through_byte_by_byte():
    """FNC1 markers force the byte-by-byte path (the DP can't represent markers)."""
    enc = TextEncoder()
    cws = enc.encode(FNC1 + "10ABCDEFGH")
    # FNC1 codeword first, then ASCII-mode bytes (digit pair 10 + single bytes).
    assert cws[:7] == [232, 140, 66, 67, 68, 69, 70]


def test_force_byte_mode_true_skips_dp():
    """``force_byte_mode=True`` takes the byte-by-byte path even when the
    DP would otherwise pick a denser mode."""
    payload = "AAAAAAAAA"  # DP picks C40 (latch 230)
    enc = TextEncoder()
    dp_cws = enc.encode(DataMatrixData(payload, encoding="ascii"))
    enc = TextEncoder()
    byte_cws = enc.encode(DataMatrixData(payload, encoding="ascii"), force_byte_mode=True)
    assert 230 in dp_cws
    assert 230 not in byte_cws
    # Byte-by-byte in ASCII mode: codeword = byte + 1 for the first byte.
    assert byte_cws[0] == ord("A") + 1


@pytest.mark.png
def test_datamatrix_smudge_tolerance(tmp_path, decode_barcode):
    """The smudged Data Matrix rendered for ``docs/printing.rst`` still decodes."""
    from pystrich._simulate_damage import datamatrix_smudge_demo

    text = "https://github.com/mmulqueen/pyStrich"
    path = tmp_path / "datamatrix-damaged.png"
    datamatrix_smudge_demo(text).save(path)
    assert decode_barcode(path) == text
