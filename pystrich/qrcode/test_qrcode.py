"""Unit test for QR Code barcode encoder"""

import pytest

from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption
from pystrich.qrcode import QRCodeData, QRCodeEncoder, isodata
from pystrich.qrcode.isodata import (
    _mask_penalty_n1,
    _mask_penalty_n2,
    _mask_penalty_n3,
    _mask_penalty_n4,
)
from pystrich.qrcode.textencoder import TextEncoder


@pytest.mark.parametrize(
    "text, expected_codewords",
    [
        (
            "hi",
            [
                64,
                38,
                134,
                144,
                236,
                17,
                236,
                17,
                236,
                17,
                236,
                17,
                236,
                17,
                236,
                17,
                17,
                160,
                77,
                193,
                121,
                155,
                5,
                133,
                245,
                218,
            ],
        ),
        (
            "banana",
            [
                64,
                102,
                38,
                22,
                230,
                22,
                230,
                16,
                236,
                17,
                236,
                17,
                236,
                17,
                236,
                17,
                5,
                142,
                20,
                56,
                215,
                125,
                137,
                131,
                106,
                125,
            ],
        ),
        (
            "wer das liest ist 31337",
            [
                65,
                119,
                118,
                87,
                34,
                6,
                70,
                23,
                50,
                6,
                198,
                150,
                87,
                55,
                66,
                6,
                151,
                55,
                66,
                3,
                51,
                19,
                51,
                51,
                112,
                236,
                17,
                236,
                124,
                222,
                181,
                177,
                208,
                193,
                45,
                100,
                155,
                47,
                28,
                28,
                88,
                55,
                156,
                59,
            ],
        ),
        # Latin-1: ECI 3 header (0111 00000011) before byte mode.
        # Bytes 112, 52, ... = 01110000 00110100 ... = ECI mode + designator + ...
        (
            "café",
            [
                112,
                52,
                4,
                99,
                97,
                102,
                233,
                0,
                236,
                17,
                236,
                17,
                236,
                17,
                236,
                17,
                186,
                45,
                82,
                50,
                110,
                13,
                249,
                90,
                95,
                165,
            ],
        ),
        # UTF-8: ECI 26 header (0111 00011010) before byte mode + 3-byte UTF-8.
        (
            "☕",
            [
                113,
                164,
                3,
                226,
                152,
                149,
                0,
                236,
                17,
                236,
                17,
                236,
                17,
                236,
                17,
                236,
                183,
                105,
                36,
                93,
                147,
                33,
                20,
                99,
                62,
                137,
            ],
        ),
    ],
)
def test_encoding(text, expected_codewords):
    """Text is correctly encoded with padding and error codewords."""
    enc = TextEncoder()
    enc.encode(QRCodeData(text, auto_encoding=True), ecl="M")
    assert enc.codewords == expected_codewords


@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
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
        # https://github.com/mmulqueen/pyStrich/issues/8
        "B-4-1-20170805-6",
        "b-4-1-20170805-6",
        "00231872347699829949",
        "00231872347699829948",
        # Latin-1 (auto-selected ECI 3 header).
        "café",
        "naïve",
        "Zürich",
        "½ + ½ = 1",
        # UTF-8 (auto-selected ECI 26 header).
        "中文",
        "☕",
        "Hello 🎉",
    ],
)
def test_encode_decode(string, ecl, tmp_path, zbarimg):
    """zbarimg can decode this library's output back to the original string"""
    img = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, ecl).save(str(img), 3)
    assert zbarimg(img) == string


@pytest.mark.parametrize("cellsize", [5, 10])
@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize(
    "string",
    [
        "banana",
        "http://www.hudora.de/track/00340059980000001319/",
        "B-4-1-20170805-6",
        "00231872347699829949",
    ],
)
def test_svg_round_trip(string, ecl, cellsize, tmp_path, svg_to_png, zbarimg):
    """SVG output rasterised with librsvg decodes back to the original string."""
    svg = tmp_path / "qrcode-test.svg"
    png = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, ecl).save_svg(str(svg), cellsize=cellsize)
    svg_to_png(svg, png)
    assert zbarimg(png) == string


@pytest.mark.parametrize("cellsize", [5, 10])
@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize(
    "string",
    [
        "banana",
        "http://www.hudora.de/track/00340059980000001319/",
        "B-4-1-20170805-6",
        "00231872347699829949",
    ],
)
def test_eps_round_trip(string, ecl, cellsize, tmp_path, eps_to_png, zbarimg):
    """EPS output rasterised with Ghostscript decodes back to the original string."""
    eps = tmp_path / "qrcode-test.eps"
    png = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, ecl).save_eps(str(eps), cellsize=cellsize)
    eps_to_png(eps, png)
    assert zbarimg(png) == string


@pytest.mark.parametrize("inverse", [True, False])
@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize(
    "string",
    [
        "banana",
        "http://www.hudora.de/track/00340059980000001319/",
        "B-4-1-20170805-6",
        "00231872347699829949",
    ],
)
def test_dxf_round_trip(string, ecl, inverse, tmp_path, dxf_to_svg, svg_to_png, zbarimg):
    """DXF output rendered to SVG via ezdxf, rasterised, decodes back to the original string."""
    cellsize = 5
    dxf = tmp_path / "qrcode-test.dxf"
    svg = tmp_path / "qrcode-test.svg"
    png = tmp_path / "qrcode-test.png"
    dxf.write_text(
        QRCodeEncoder(string, ecl).get_dxf(cellsize=cellsize, inverse=inverse),
        encoding="ascii",
    )
    if inverse:
        dxf_to_svg(dxf, svg, inverse=True)
    else:
        # inverse=False emits no geometry for the light quiet-zone cells, so
        # the SVG bounding box hugs the dark modules; pad a 4-module margin
        # back in for the decoder.
        dxf_to_svg(dxf, svg, inverse=False, margin_mm=4 * cellsize)
    svg_to_png(svg, png)
    assert zbarimg(png) == string


@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize(
    "text",
    [
        "hi",
        "A" * 78,
        # https://github.com/mmulqueen/pyStrich/issues/8
        "B-4-1-20170805-6",
        "00231872347699829949",
    ],
)
def test_total_codewords_equals_max_codewords(text, ecl):
    """After encoding, len(codewords) must equal MAX_CODEWORDS[version]."""
    enc = TextEncoder()
    enc.encode(QRCodeData(text, auto_encoding=True), ecl=ecl)
    assert len(enc.codewords) == isodata.MAX_CODEWORDS[enc.version]


_BLOCK_CHARS = set("█▀▄ ")


def test_get_terminal_art_uses_only_block_chars_and_newlines():
    text = QRCodeEncoder("hi").get_terminal_art(ansi_bg=False)
    assert set(text) <= _BLOCK_CHARS | {"\n"}


def test_get_terminal_art_collapses_two_rows_per_line():
    enc = QRCodeEncoder("hi")
    matrix_height = enc.init_renderer().height
    plain = enc.get_terminal_art(ansi_bg=False).rstrip("\n").splitlines()
    assert len(plain) == -(-matrix_height // 2)


def test_get_terminal_art_ansi_wraps_each_line():
    text = QRCodeEncoder("hi").get_terminal_art()
    for line in text.rstrip("\n").splitlines():
        assert line.startswith("\033[107;30m")
        assert line.endswith("\033[0m")


def test_get_terminal_art_ansi_off_has_no_escape_codes():
    text = QRCodeEncoder("hi").get_terminal_art(ansi_bg=False)
    assert "\033" not in text


@pytest.mark.parametrize(
    "text, expected_encoding",
    [
        pytest.param("hello", "ascii", id="ascii"),
        pytest.param("café", "iso-8859-1", id="latin1"),
        pytest.param("½", "iso-8859-1", id="latin1-edge"),
        pytest.param("中文", "utf-8", id="utf8-cjk"),
        pytest.param("☕", "utf-8", id="utf8-symbol"),
        pytest.param("", "ascii", id="empty"),
    ],
)
def test_qrcodedata_auto_encoding_picks_narrowest(text, expected_encoding):
    assert QRCodeData(text, auto_encoding=True).encoding == expected_encoding


def test_qrcodedata_explicit_ascii_rejects_non_ascii():
    with pytest.raises(PyStrichInvalidInput, match="ASCII"):
        QRCodeData("café", encoding="ascii")


def test_qrcodedata_explicit_latin1_rejects_codepoint_above_ff():
    with pytest.raises(PyStrichInvalidInput, match="ISO-8859-1"):
        QRCodeData("☕", encoding="iso-8859-1")


def test_qrcodedata_requires_encoding_or_auto():
    with pytest.raises(PyStrichInvalidOption, match="auto_encoding"):
        QRCodeData("hello")


def test_qrcodedata_rejects_unknown_encoding():
    with pytest.raises(PyStrichInvalidOption, match="unknown"):
        QRCodeData("hello", encoding="latin1")  # type: ignore[arg-type]


def test_qrcode_encoder_accepts_qrcodedata_directly():
    """Passing QRCodeData lets the caller pin the encoding."""
    # Force ascii — would raise on non-ASCII input.
    enc = TextEncoder()
    enc.encode(QRCodeData("hello", encoding="ascii"), ecl="M")
    # No ECI header for ASCII: first nibble is 0100 (byte mode), not 0111 (ECI).
    assert enc.codewords[0] >> 4 == 0b0100


def test_qrcode_encoder_wraps_plain_str_with_auto_encoding():
    """``QRCodeEncoder(str)`` wraps the input as ``QRCodeData(..., auto_encoding=True)``."""
    assert (
        QRCodeEncoder("café").matrix == QRCodeEncoder(QRCodeData("café", auto_encoding=True)).matrix
    )


# Direct tests on the mask-penalty helpers so the conformance fixes
# (N3 4-module light buffer, N4 full module count denominator) cannot
# silently regress.
@pytest.mark.parametrize(
    "lines, expected",
    [
        pytest.param([b""], 0, id="empty"),
        pytest.param([b"\x00\x00\x00\x00"], 0, id="run-of-4-no-penalty"),
        pytest.param([b"\x00\x00\x00\x00\x00"], 3, id="run-of-5-scores-3"),
        pytest.param([b"\x01\x01\x01\x01\x01\x01"], 4, id="run-of-6-scores-4"),
        pytest.param([b"\x01" * 7], 5, id="run-of-7-scores-5"),
        pytest.param([b"\x00\x00\x00\x00\x00", b"\x01" * 6], 7, id="two-runs-sum"),
    ],
)
def test_mask_penalty_n1(lines, expected):
    assert _mask_penalty_n1(lines) == expected


@pytest.mark.parametrize(
    "rows, expected",
    [
        pytest.param([b"\x00\x00", b"\x00\x00"], 3, id="2x2-all-same-scores-3"),
        pytest.param([b"\x00\x01", b"\x01\x00"], 0, id="checker-scores-0"),
        # 3x3 same: four overlapping 2x2 blocks * 3 = 12.
        pytest.param([b"\x01\x01\x01"] * 3, 12, id="3x3-all-same-scores-12"),
    ],
)
def test_mask_penalty_n2(rows, expected):
    assert _mask_penalty_n2(rows) == expected


@pytest.mark.parametrize(
    "lines, expected",
    [
        # A bare 7-module finder with no light flank scores 0: the
        # 4-module light buffer is required for the 40-point hit.
        pytest.param([b"\x01\x00\x01\x01\x01\x00\x01"], 0, id="finder-no-flanks"),
        pytest.param(
            [b"\x00\x00\x00\x00\x01\x00\x01\x01\x01\x00\x01"], 40, id="finder-light-before"
        ),
        pytest.param(
            [b"\x01\x00\x01\x01\x01\x00\x01\x00\x00\x00\x00"], 40, id="finder-light-after"
        ),
        # Flanks on both sides counts twice (one each pattern).
        pytest.param(
            [b"\x00\x00\x00\x00\x01\x00\x01\x01\x01\x00\x01\x00\x00\x00\x00"],
            80,
            id="finder-both-flanks",
        ),
    ],
)
def test_mask_penalty_n3(lines, expected):
    assert _mask_penalty_n3(lines) == expected


@pytest.mark.parametrize(
    "rows, total_modules, expected",
    [
        # Exactly 50% dark: deviation 0, penalty 0.
        pytest.param([b"\x01\x00" * 50, b"\x01\x00" * 50], 200, 0, id="balanced-50pct"),
        # 80% dark of 400 modules: dev 30%, ⌊30/5⌋ * 10 = 60.
        pytest.param([b"\x01" * 80 + b"\x00" * 20] * 4, 400, 60, id="80pct-dark-scores-60"),
        # 40% dark of 400 modules: dev 10%, ⌊10/5⌋ * 10 = 20.
        pytest.param([b"\x01" * 40 + b"\x00" * 60] * 4, 400, 20, id="40pct-dark-scores-20"),
        # Within 45-55% band: no penalty.
        pytest.param([b"\x01" * 47 + b"\x00" * 53] * 4, 400, 0, id="47pct-in-band"),
    ],
)
def test_mask_penalty_n4(rows, total_modules, expected):
    assert _mask_penalty_n4(rows, total_modules) == expected
