"""Unit test for code128 barcode encoder"""

import filecmp
import warnings
from datetime import timedelta
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pystrich.code128 import FNC1, FNC2, Code128Data, Code128Encoder, Code128Marker
from pystrich.exceptions import (
    Code128MarkerBytesCompatWarning,
    PyStrichInvalidInput,
    PyStrichInvalidOption,
    PyStrichInvalidPayloadLength,
)
from pystrich.gs1 import GS1Fixed, GS1Variable

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
        # A leading FNC4 (codeword 100, same value as the switch to B) must
        # survive the start-code optimisation.
        pytest.param(
            Code128Data("é", auto_encoding=True),
            [104, 100, 73],
            id="leading-latin1-keeps-fnc4",
        ),
        # Streams shorter than the start-code optimisation patterns.
        pytest.param(Code128Data("", encoding="ascii"), [104], id="empty"),
        pytest.param(Code128Data(FNC1, encoding="ascii"), [104, 102], id="lone-fnc1"),
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
@pytest.mark.png
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
@pytest.mark.png
def test_scanner_round_trip(string, tmp_path, decode_barcode):
    """A real scanner decodes this library's output back to the original string."""
    img = tmp_path / "code128.png"
    Code128Encoder(string).save(str(img))
    assert decode_barcode(img) == string


@st.composite
def _code128_payload(draw):
    parts = draw(
        st.lists(
            st.one_of(
                # Short digit runs sweep the 4-digit charset-C switch
                # threshold and the odd-run leftover-digit flush.
                st.text(alphabet="0123456789", min_size=1, max_size=6),
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=8),
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
                st.text(alphabet="!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~ ", min_size=1, max_size=4),
                # Charset A territory; zxing round-trips \t literally.
                st.text(alphabet="\t", min_size=1, max_size=2),
                # Latin-1 via FNC4 shifts; 0xA0+ skips the C1 control block.
                st.text(
                    st.characters(min_codepoint=0xA0, max_codepoint=0xFF),
                    min_size=1,
                    max_size=4,
                ),
            ),
            min_size=1,
            max_size=6,
        )
    )
    return "".join(parts)


@given(text=_code128_payload())
@settings(
    max_examples=100,
    deadline=timedelta(seconds=2),
    print_blob=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.png
def test_property_roundtrip(text, tmp_path, decode_barcode):
    """Class-banded payloads roundtrip through encode + render + decode."""
    img = tmp_path / "code128-property.png"
    Code128Encoder(Code128Data(text, auto_encoding=True)).save(str(img))
    assert decode_barcode(img) == text


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


def test_unencodable_character_raises():
    with pytest.raises(PyStrichInvalidInput, match="encoding ASCII cannot encode the input"):
        Code128Encoder("café")


@pytest.mark.parametrize("fmt", ["svg", "eps"])
def test_charset_a_control_chars_dropped_from_label(fmt):
    """Charset-A control chars have no embedded glyph and must not crash the vector renderer."""
    encoder = Code128Encoder("a\tb\x01c")
    output = getattr(encoder, f"get_{fmt}")(3)
    for printable in "abc":
        assert f"g_{ord(printable):02X}" in output
    for control in "\t\x01":
        assert f"g_{ord(control):02X}" not in output


def test_code128_marker_unknown_name_raises():
    with pytest.raises(ValueError, match="unknown Code128 marker name"):
        Code128Marker("FNC5")


@pytest.mark.parametrize(
    "expr, expected_segments",
    [
        # marker.__add__(str) chain — marker on the left
        pytest.param(
            FNC1 + "10ABC" + FNC1 + "21XYZ",
            (FNC1, "10ABC", FNC1, "21XYZ"),
            id="marker-leading",
        ),
        # str + marker exercises marker.__radd__
        pytest.param(
            "lead" + FNC1 + "mid" + FNC2 + "tail",
            ("lead", FNC1, "mid", FNC2, "tail"),
            id="str-leading-with-radd",
        ),
    ],
)
def test_marker_concatenation_builds_code128data(expr, expected_segments):
    """``+`` between markers and strs returns a Code128Data with the segments
    in order. The two cases cover ``__add__`` and ``__radd__`` entry points."""
    assert isinstance(expr, Code128Data)
    assert expr.segments == expected_segments
    assert expr.encoding == "ascii"


@pytest.mark.parametrize(
    "byte, marker_name, hint_fragment",
    [
        pytest.param("\xf1", "FNC1", "FNC1 marker constant", id="fnc1"),
        pytest.param("\xf2", "FNC2", "FNC2 marker constant", id="fnc2"),
        pytest.param("\xf3", "FNC3", "FNC3 marker constant", id="fnc3"),
        pytest.param("\xf4", "FNC4", "encoding='iso-8859-1'", id="fnc4-latin1"),
    ],
)
def test_code128data_rejects_legacy_marker_bytes(byte, marker_name, hint_fragment):
    """Magic bytes in ASCII-mode str segments are rejected with a message
    pointing at the typed marker constant (FNC1-3) or the Latin-1 path (FNC4)."""
    with pytest.raises(PyStrichInvalidInput) as exc:
        Code128Data(byte, encoding="ascii")
    assert f"legacy magic-byte form of {marker_name}" in str(exc.value)
    assert hint_fragment in str(exc.value)


@pytest.mark.parametrize(
    "encoding, payload",
    [
        pytest.param("ascii", "café", id="ascii-rejects-high-byte"),
        pytest.param("iso-8859-1", "€", id="iso-8859-1-rejects-above-0xff"),
    ],
)
def test_code128data_rejects_out_of_range(encoding, payload):
    """Each encoding's codec rejects codepoints it can't represent."""
    with pytest.raises(PyStrichInvalidInput, match="cannot encode"):
        Code128Data(payload, encoding=encoding)


def test_legacy_marker_bytes_in_str_path_matches_typed():
    """The legacy bare-str path warns and produces byte-identical codewords,
    checksum and bars compared to the typed Code128Data form."""
    with pytest.warns(Code128MarkerBytesCompatWarning, match="legacy FNC marker shortcut"):
        legacy = Code128Encoder("\xf110ABC\xf121XYZ")
    typed = Code128Encoder(FNC1 + "10ABC" + FNC1 + "21XYZ")
    assert (legacy.encoded_text, legacy.checksum, legacy.bars) == (
        typed.encoded_text,
        typed.checksum,
        typed.bars,
    )


@pytest.mark.parametrize("text", ["hello world", "12345"])
def test_str_without_marker_bytes_does_not_warn(text):
    """Plain str without marker bytes passes through with no warning —
    we don't want to spam users on every encode."""
    with warnings.catch_warnings():
        warnings.simplefilter("error", Code128MarkerBytesCompatWarning)
        Code128Encoder(text)


@pytest.mark.parametrize(
    "payload, expected_decoded",
    [
        # FNC1 in position 1 → GS1-128 symbol (AIM ID ]C1); zxing-cpp prints AIs in parens.
        pytest.param(
            FNC1 + "10ABC" + FNC1 + "21XYZ",
            "(10)ABC(21)XYZ",
            id="gs1-fnc1-first",
        ),
        # FNC1 mid-data (AIM ID ]C0) surfaces as <GS>; placement mid-digit-run also
        # exercises the charset-C digit-buffer flush before the marker is emitted.
        pytest.param(
            "12345" + FNC1 + "TAIL",
            "12345<GS>TAIL",
            id="fnc1-mid-digit-run",
        ),
        # Latin-1 supplement chars via explicit encoding — FNC4 single-shifts on the wire.
        pytest.param(
            Code128Data("HELLO café", encoding="iso-8859-1"),
            "HELLO café",
            id="latin1-explicit",
        ),
        # auto_encoding=True picks iso-8859-1 for the same payload.
        pytest.param(
            Code128Data("café", auto_encoding=True),
            "café",
            id="latin1-auto",
        ),
        # FNC1 between Latin-1 segments — exercises marker + iso-8859-1 mixing.
        pytest.param(
            Code128Data("12345", encoding="iso-8859-1")
            + FNC1
            + Code128Data("café", encoding="iso-8859-1"),
            "12345<GS>café",
            id="fnc1-between-latin1",
        ),
    ],
)
@pytest.mark.png
def test_round_trip_code128data(payload, expected_decoded, tmp_path, decode_barcode):
    """End-to-end: encode payload → PNG → zxing-cpp → expected string."""
    img = tmp_path / "rt.png"
    Code128Encoder(payload).save(str(img))
    assert decode_barcode(img) == expected_decoded


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
def test_code128data_gs1_segment_structure(fields, expected_segments):
    data = Code128Data.gs1(*fields)
    assert data.segments == expected_segments
    assert data.encoding == "ascii"


@pytest.mark.png
def test_code128data_gs1_round_trip(tmp_path, decode_barcode):
    """Real scanner decodes the .gs1() output as a GS1-128 with the AIs in parens."""
    data = Code128Data.gs1(
        GS1Fixed("01", "09501234543213"),
        GS1Fixed("17", "261231"),
        GS1Variable("10", "BF07"),
    )
    img = tmp_path / "gs1.png"
    Code128Encoder(data).save(str(img))
    assert decode_barcode(img) == "(01)09501234543213(17)261231(10)BF07"


@pytest.mark.parametrize(
    "fields, reason",
    [
        pytest.param((), "at least one", id="empty"),
        pytest.param(("01", "x"), "GS1Fixed or GS1Variable", id="bare-str"),
        pytest.param((GS1Fixed("01", "x"), "extra"), "GS1Fixed or GS1Variable", id="mixed-str"),
    ],
)
def test_code128data_gs1_rejects_bad_arguments(fields, reason):
    with pytest.raises(PyStrichInvalidOption, match=reason):
        Code128Data.gs1(*fields)


def test_code128data_gs1_accepts_48_data_characters():
    Code128Data.gs1(GS1Variable("10", "x" * 46))


@pytest.mark.parametrize(
    "fields",
    [
        pytest.param((GS1Variable("10", "x" * 47),), id="single-field-49"),
        pytest.param(
            (GS1Variable("10", "x" * 23), GS1Variable("21", "x" * 21)),
            id="separator-tips-over-48",
        ),
    ],
)
def test_code128data_gs1_rejects_over_48_data_characters(fields):
    with pytest.raises(PyStrichInvalidPayloadLength, match="49 data characters"):
        Code128Data.gs1(*fields)


def test_latin1_marker_in_digit_run():
    """Latin-1 char arriving mid-charset-C run forces a switch to B (FNC4
    isn't representable in C), spills the leftover digit, then shifts."""
    encoder = Code128Encoder(Code128Data("12345" + chr(0xE9), encoding="iso-8859-1"))
    cw = encoder.encoded_text
    assert cw[0] == 105  # START_C
    assert cw[1:3] == [12, 34]  # '12','34' digit pairs
    assert cw[3] == 100  # TO_B
    assert cw[4] == 21  # leftover '5' in B
    assert cw[5] == 100  # FNC4 (codeword 100 in B)
    assert cw[6] == 73  # 'i' — the ASCII counterpart of é (0xE9 - 0x80)


def test_latin1_c1_control_routes_to_charset_a():
    """A Latin-1 C1 control (0x80-0x9F) shifts to its ASCII counterpart in
    0x00-0x1F, which lives in charset A only — the encoder must pick A, not
    B, so the table lookup finds the counterpart."""
    encoder = Code128Encoder(Code128Data("\x82", encoding="iso-8859-1"))
    cw = encoder.encoded_text
    # START_B + TO_A optimizes to START_A; then FNC4 in A (101) + STX (66).
    assert cw[0] == 103  # START_A
    assert cw[1] == 101  # FNC4 in A
    assert cw[2] == 66  # '\x02' (STX) — counterpart of '\x82' in charset A
