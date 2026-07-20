"""Unit test for QR Code barcode encoder"""

from datetime import timedelta
from string import ascii_lowercase

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption
from pystrich.qrcode import QRCodeData, QRCodeEncoder, QRErrorCorrectionLevel, isodata
from pystrich.qrcode.isodata import (
    _LINE_SEP,
    _mask_penalty_n1,
    _mask_penalty_n2,
    _mask_penalty_n3,
    _mask_penalty_n4,
)
from pystrich.qrcode.modes import ALPHA, BYTE, CHAR_COUNT_BITS, NUM, bracket_for_version
from pystrich.qrcode.textencoder import STR2ECL, TextEncoder


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
        # Trailing "31337" splits out as a Numeric segment; the lowercase
        # prefix stays in Byte mode.
        (
            "wer das liest ist 31337",
            [
                65,
                39,
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
                1,
                1,
                83,
                148,
                160,
                236,
                17,
                236,
                17,
                21,
                102,
                207,
                186,
                118,
                226,
                164,
                253,
                246,
                152,
                135,
                15,
                61,
                99,
                154,
                30,
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
        # Exercises the Numeric encoding path.
        "0123456789" * 5,
        # Exercises the Alphanumeric encoding path.
        "HTTPS://EXAMPLE.COM/PRODUCT/12345",
        # Latin-1 (auto-selected ECI 3 header).
        "café",
        "naïve",
        "Zürich",
        "½ + ½ = 1",
        # Mixed segmentation under Latin-1 ECI: ALPHA prefix, BYTE for 'Ü',
        # ALPHA tail. Exercises mode switching around a non-ASCII byte.
        "PROD-12345-ZÜRICH 67890",
        # UTF-8 (auto-selected ECI 26 header).
        "中文",
        "☕",
        "Hello 🎉",
    ],
)
@pytest.mark.png
def test_scanner_round_trip(string, ecl, tmp_path, decode_barcode):
    """A real scanner decodes this library's output back to the original string."""
    img = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, ecl).save(str(img), 3)
    assert decode_barcode(img) == string


# The payloads above top out around version 6; sweep a payload sized for
# every version so each frame, alignment grid and block structure is
# decode-verified by an independent implementation. Asserting the reported
# error correction level also proves the format information: zxing must
# read it to unmask the data.
@pytest.mark.png
def test_scanner_round_trip_every_version(tmp_path, decode_barcode):
    img = tmp_path / "qrcode-test.png"
    ecls: tuple[QRErrorCorrectionLevel, ...] = ("L", "M", "Q", "H")
    for version in range(1, 41):
        ecl = ecls[version % 4]
        if version == 1:
            payload = "hi"
        else:
            # One byte more than the previous version holds, so byte mode
            # lands exactly on the target version.
            capacity = isodata.MAX_DATA_BITS[version - 2 + 40 * STR2ECL[ecl]]
            payload = (ascii_lowercase * 200)[: capacity // 8]
        encoder = QRCodeEncoder(payload, ecl)
        assert (len(encoder.matrix) - 17) // 4 == version
        encoder.save(str(img), 3)
        result = decode_barcode(img, full=True)
        assert str(result.text) == payload
        assert result.ec_level == ecl


@pytest.mark.parametrize("ecl", ["L", "M", "Q", "H"])
@pytest.mark.parametrize(
    "string",
    [
        "中文",
        "Hello 中文",
        "日本語テスト",
        # Mixed segmentation: NUM+KANJI and ALPHA+KANJI under shift_jis.
        "0123456789中文",
        "HELLO中文",
    ],
)
@pytest.mark.png
def test_shift_jis_kanji_round_trip(string, ecl, tmp_path, decode_barcode):
    """Shift_JIS payloads use Kanji mode where it pays and decode back cleanly."""
    img = tmp_path / "qrcode-test.png"
    QRCodeEncoder(QRCodeData(string, encoding="shift_jis"), ecl).save(str(img), 3)
    assert decode_barcode(img) == string


@st.composite
def _qr_payload(draw):
    parts = draw(
        st.lists(
            st.one_of(
                st.text(alphabet="0123456789", min_size=1, max_size=8),
                st.text(alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZ", min_size=1, max_size=8),
                st.text(alphabet=" $%*+-./:", min_size=1, max_size=4),
                st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=8),
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


@given(text=_qr_payload(), ecl=st.sampled_from([None, "L", "M", "Q", "H"]))
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
def test_property_roundtrip(text, ecl, tmp_path, decode_barcode):
    """Class-banded payloads roundtrip through encode + render + decode."""
    img = tmp_path / "qrcode-property.png"
    QRCodeEncoder(text, ecl).save(str(img), 3)
    assert decode_barcode(img) == text


def _max_chars(mode, version, capacity):
    """Most characters of one mode that fit ``capacity`` bits as a single segment."""
    usable = capacity - 4 - CHAR_COUNT_BITS[mode][bracket_for_version(version)]
    if mode == NUM:
        groups, rem = divmod(usable, 10)
        return 3 * groups + (2 if rem >= 7 else 1 if rem >= 4 else 0)
    if mode == ALPHA:
        groups, rem = divmod(usable, 11)
        return 2 * groups + (1 if rem >= 6 else 0)
    return usable // 8


_QR_FILLERS = {NUM: "0", ALPHA: "A", BYTE: "a"}

# Spans the one-to-multi-block transitions; larger versions are covered
# deterministically by test_scanner_round_trip_every_version.
_SWEEP_VERSIONS = tuple(range(1, 11))


@st.composite
def _qr_boundary_payload(draw, versions=_SWEEP_VERSIONS):
    """Single-mode filler sized to land the bit stream within two characters
    of a version's data capacity, sweeping the terminator, pad-byte and
    version-selection edges that uniformly random payloads rarely reach.

    Returns ``(text, ecl, version, fits)``; ``fits`` is whether the payload
    still fits the drawn version.
    """
    ecl = draw(st.sampled_from("LMQH"))
    version = draw(st.sampled_from(versions))
    capacity = isodata.MAX_DATA_BITS[version - 1 + 40 * STR2ECL[ecl]]
    mode = draw(st.sampled_from((NUM, ALPHA, BYTE)))
    n0 = _max_chars(mode, version, capacity)
    n = n0 + draw(st.integers(-2, 2))
    return _QR_FILLERS[mode] * max(1, n), ecl, version, n <= n0


@given(payload=_qr_boundary_payload())
@settings(
    max_examples=300,
    deadline=timedelta(seconds=2),
    print_blob=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.png
def test_property_roundtrip_capacity_boundaries(payload, tmp_path, decode_barcode):
    """Boundary-biased payloads roundtrip across versions 1-10 at every ECL."""
    text, ecl, _, _ = payload
    img = tmp_path / "qrcode-boundary.png"
    QRCodeEncoder(text, ecl).save(str(img), 3)
    assert decode_barcode(img) == text


@given(payload=_qr_boundary_payload(versions=(40,)))
@settings(
    max_examples=20,
    deadline=timedelta(seconds=5),
    print_blob=True,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
@pytest.mark.png
def test_property_roundtrip_top_edge(payload, tmp_path, decode_barcode):
    """At version 40 a draw past capacity must overflow cleanly instead."""
    text, ecl, _, fits = payload
    img = tmp_path / "qrcode-top-edge.png"
    try:
        QRCodeEncoder(text, ecl).save(str(img), 3)
    except PyStrichInvalidInput:
        assert not fits
        return
    assert decode_barcode(img) == text


@given(payload=_qr_boundary_payload())
@settings(max_examples=300, deadline=timedelta(seconds=2), print_blob=True)
def test_boundary_payloads_select_their_target_version(payload):
    """Guards the strategy's bit arithmetic: if the encoder's cost model
    drifts, the sweeps would otherwise silently stop reaching the edges."""
    text, ecl, version, fits = payload
    enc = TextEncoder()
    enc.encode(QRCodeData(text, auto_encoding=True), ecl)
    if fits:
        assert enc.version == version
    else:
        assert enc.version > version


@given(text=_qr_payload(), ecl=st.sampled_from(["L", "M", "Q", "H"]))
@settings(max_examples=100, deadline=timedelta(seconds=2), print_blob=True)
def test_chosen_mask_minimises_penalty(text, ecl):
    """The emitted symbol scores no worse than its seven re-maskings, and
    its data modules carry the mask the selection picked."""
    enc = TextEncoder()
    matrix = enc.encode(QRCodeData(text, auto_encoding=True), ecl)
    content = enc.minfo.create_matrix(enc.version, enc.codewords)
    chosen = enc.minfo.calc_mask_number(content)
    size = len(matrix)

    scores = []
    for mask in range(8):
        rows = [bytes((content[c][r] >> mask) & 1 for c in range(size)) for r in range(size)]
        cols = [bytes(row[c] for row in rows) for c in range(size)]
        lines_blob = _LINE_SEP.join(rows + cols)
        scores.append(
            _mask_penalty_n1(lines_blob)
            + _mask_penalty_n2(rows)
            + _mask_penalty_n3(lines_blob)
            + _mask_penalty_n4(rows, size * size)
        )
    assert scores[chosen] == min(scores)

    _, occupied = isodata._build_frame(enc.version)
    for row in range(size):
        for col in range(size):
            if not occupied[row][col]:
                assert matrix[row][col] == (content[col][row] >> chosen) & 1


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
def test_svg_round_trip(string, ecl, cellsize, tmp_path, svg_to_png, decode_barcode):
    """SVG output rasterised with librsvg decodes back to the original string."""
    svg = tmp_path / "qrcode-test.svg"
    png = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, ecl).save_svg(str(svg), cellsize=cellsize)
    svg_to_png(svg, png)
    assert decode_barcode(png) == string


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
def test_eps_round_trip(string, ecl, cellsize, tmp_path, eps_to_png, decode_barcode):
    """EPS output rasterised with Ghostscript decodes back to the original string."""
    eps = tmp_path / "qrcode-test.eps"
    png = tmp_path / "qrcode-test.png"
    QRCodeEncoder(string, ecl).save_eps(str(eps), cellsize=cellsize)
    eps_to_png(eps, png)
    assert decode_barcode(png) == string


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
def test_dxf_round_trip(string, ecl, inverse, tmp_path, dxf_to_svg, svg_to_png, decode_barcode):
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
    assert decode_barcode(png) == string


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


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        pytest.param(
            {"ssid": "MyNet", "password": "MyPassword"},
            "WIFI:T:WPA;S:MyNet;P:MyPassword;;",
            id="wpa",
        ),
        pytest.param(
            {"ssid": "MyNet"},
            "WIFI:S:MyNet;;",
            id="open-omits-type-and-password",
        ),
        pytest.param(
            {"ssid": "MyNet", "password": "pw", "hidden": True},
            "WIFI:T:WPA;S:MyNet;H:true;P:pw;;",
            id="hidden-comes-before-password",
        ),
        pytest.param(
            {"ssid": "Bar; Grill", "password": "p%ss:wo;rd"},
            "WIFI:T:WPA;S:Bar%3B%20Grill;P:p%25ss%3Awo%3Brd;;",
            id="percent-encodes-reserved-octets",
        ),
        pytest.param(
            {"ssid": "MyNet", "password": "MyPassword", "transition_disable": 1},
            "WIFI:T:WPA;R:1;S:MyNet;P:MyPassword;;",
            id="transition-disable-rendered-hex",
        ),
        pytest.param(
            {"ssid": "MyNet", "password": "pw", "password_identifier": "id;1"},
            "WIFI:T:WPA;S:MyNet;I:id%3B1;P:pw;;",
            id="password-identifier-before-password",
        ),
        # Example 3 from the WPA3 Specification v3.5, verbatim.
        pytest.param(
            {
                "ssid": "MyNet",
                "password": "a2bc-de3f-ghi4",
                "transition_disable": 3,
                "public_key": "MDkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDIgADURzxmttZoIRIPWGoQMV00XHWCAQIhXruVWOz0NjlkIA=",
            },
            "WIFI:T:WPA;R:3;S:MyNet;P:a2bc-de3f-ghi4;"
            "K:MDkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDIgADURzxmttZoIRIPWGoQMV00XHWCAQIhXruVWOz0NjlkIA=;;",
            id="sae-pk-public-key-verbatim",
        ),
    ],
)
def test_wifi_network_uri_structure(kwargs, expected):
    data = QRCodeData.wifi_network(**kwargs)
    assert data.segments == (expected,)
    assert data.encoding == "ascii"


# Direct tests on the mask-penalty helpers so the conformance fixes
# (N3 4-module light buffer, N4 full module count denominator) cannot
# silently regress.
@pytest.mark.parametrize(
    "lines_blob, expected",
    [
        pytest.param(b"", 0, id="empty"),
        pytest.param(b"\x00\x00\x00\x00", 0, id="run-of-4-no-penalty"),
        pytest.param(b"\x00\x00\x00\x00\x00", 3, id="run-of-5-scores-3"),
        pytest.param(b"\x01\x01\x01\x01\x01\x01", 4, id="run-of-6-scores-4"),
        pytest.param(b"\x01" * 7, 5, id="run-of-7-scores-5"),
        pytest.param(_LINE_SEP.join([b"\x00" * 5, b"\x01" * 6]), 7, id="two-runs-sum"),
        pytest.param(_LINE_SEP.join([b"\x00" * 3, b"\x00" * 3]), 0, id="separator-breaks-runs"),
        pytest.param(
            _LINE_SEP.join([b"\x01" * 3, b"\x01" * 3]), 0, id="separator-breaks-dark-runs"
        ),
    ],
)
def test_mask_penalty_n1(lines_blob, expected):
    assert _mask_penalty_n1(lines_blob) == expected


@pytest.mark.parametrize(
    "rows, expected",
    [
        pytest.param([b"\x00\x00", b"\x00\x00"], 3, id="2x2-all-same-scores-3"),
        pytest.param([b"\x00\x01", b"\x01\x00"], 0, id="checker-scores-0"),
        # A same-colour left-edge column pair is not a block on its own.
        pytest.param([b"\x00\x01", b"\x00\x00"], 0, id="left-edge-column-not-a-block"),
        # 3x3 same: four overlapping 2x2 blocks * 3 = 12.
        pytest.param([b"\x01\x01\x01"] * 3, 12, id="3x3-all-same-scores-12"),
    ],
)
def test_mask_penalty_n2(rows, expected):
    assert _mask_penalty_n2(rows) == expected


@pytest.mark.parametrize(
    "lines_blob, expected",
    [
        # A bare 7-module finder with no light flank scores 0: the
        # 4-module light buffer is required for the 40-point hit.
        pytest.param(b"\x01\x00\x01\x01\x01\x00\x01", 0, id="finder-no-flanks"),
        pytest.param(b"\x00\x00\x00\x00\x01\x00\x01\x01\x01\x00\x01", 40, id="finder-light-before"),
        pytest.param(b"\x01\x00\x01\x01\x01\x00\x01\x00\x00\x00\x00", 40, id="finder-light-after"),
        # Flanks on both sides counts twice (one each pattern).
        pytest.param(
            b"\x00\x00\x00\x00\x01\x00\x01\x01\x01\x00\x01\x00\x00\x00\x00",
            80,
            id="finder-both-flanks",
        ),
        # A light flank on the far side of a line boundary does not count.
        pytest.param(
            _LINE_SEP.join([b"\x00" * 4, b"\x01\x00\x01\x01\x01\x00\x01"]),
            0,
            id="flank-split-across-lines",
        ),
    ],
)
def test_mask_penalty_n3(lines_blob, expected):
    assert _mask_penalty_n3(lines_blob) == expected


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


@pytest.mark.png
def test_qrcode_smudge_tolerance(tmp_path, decode_barcode):
    """The smudged QR Code rendered for ``docs/printing.rst`` still decodes."""
    from pystrich._simulate_damage import qrcode_smudge_demo

    text = "https://github.com/mmulqueen/pyStrich"
    path = tmp_path / "qrcode-damaged.png"
    qrcode_smudge_demo(text).save(path)
    assert decode_barcode(path) == text


def test_rs_block_order_consistency():
    """The expanded error-correction block structure adds up for every
    version and error correction level."""
    for ecl in range(4):
        for version in range(1, 41):
            minfo = isodata.MatrixInfo(version, ecl)
            index = version - 1 + 40 * ecl
            assert len(minfo.rs_block_order) == isodata.RS_BLOCK_COUNT[index]
            assert sum(minfo.rs_block_order) == isodata.MAX_CODEWORDS[version]
            data_codewords = [block - minfo.rs_ecc_codewords for block in minfo.rs_block_order]
            assert all(length > 0 for length in data_codewords)
            assert sum(data_codewords) * 8 == isodata.MAX_DATA_BITS[index]


def test_version_info_bits():
    assert isodata._version_info_bits(7) == 0x07C94
    assert isodata._version_info_bits(8) == 0x085BC


def test_placement_covers_every_data_module_once():
    """Every version's coordinate arrays address ``byte_num`` distinct
    modules, none of them function-pattern or reserved ones."""
    for version in range(1, 41):
        minfo = isodata.MatrixInfo(version, 0)
        coords = set(zip(minfo.matrix_d[0], minfo.matrix_d[1], strict=True))
        assert len(coords) == minfo.byte_num
        _, occupied = isodata._build_frame(version)
        assert not any(occupied[row][col] for col, row in coords)


def test_version_information_blocks():
    """Version 7+ frames carry two mirrored version-information blocks
    whose value BCH-checks and encodes the version number."""
    for version in range(7, 41):
        frame, _ = isodata._build_frame(version)
        size = 17 + 4 * version
        top_right = [frame[i // 3][size - 11 + i % 3] for i in range(18)]
        bottom_left = [frame[size - 11 + i % 3][i // 3] for i in range(18)]
        assert bottom_left == top_right
        value = sum(bit << i for i, bit in enumerate(top_right))
        assert value >> 12 == version
        remainder = value
        for bit in range(17, 11, -1):
            if remainder & (1 << bit):
                remainder ^= 0b1111100100101 << (bit - 12)
        assert remainder == 0


# Transcribed by hand so it cannot inherit a bug from the drawing code.
_FINDER = (
    "1111111",
    "1000001",
    "1011101",
    "1011101",
    "1011101",
    "1000001",
    "1111111",
)


def test_finder_patterns_match_transcribed_tile():
    frame, _ = isodata._build_frame(2)
    size = 25
    for row0, col0 in ((0, 0), (0, size - 7), (size - 7, 0)):
        for r in range(7):
            for c in range(7):
                assert frame[row0 + r][col0 + c] == int(_FINDER[r][c])
    # Light separators along each finder's inner edges.
    assert all(frame[7][c] == 0 for c in range(8))
    assert all(frame[r][7] == 0 for r in range(8))
    assert all(frame[7][c] == 0 for c in range(size - 8, size))
    assert all(frame[r][size - 8] == 0 for r in range(8))
    assert all(frame[size - 8][c] == 0 for c in range(8))
    assert all(frame[r][7] == 0 for r in range(size - 8, size))


# Transcribed by hand from the eight mask-pattern definitions. Each
# pattern repeats within six rows except the fourth, which needs twelve.
_MASK_TILES = (
    ("101010", "010101", "101010", "010101", "101010", "010101"),
    ("111111", "000000", "111111", "000000", "111111", "000000"),
    ("100100", "100100", "100100", "100100", "100100", "100100"),
    ("100100", "001001", "010010", "100100", "001001", "010010"),
    (
        "111000",
        "111000",
        "000111",
        "000111",
        "111000",
        "111000",
        "000111",
        "000111",
        "111000",
        "111000",
        "000111",
        "000111",
    ),
    ("111111", "100000", "100100", "101010", "100100", "100000"),
    ("111111", "111000", "110110", "101010", "101101", "100011"),
    ("101010", "000111", "100011", "010101", "111000", "011100"),
)


def test_mask_patterns_match_transcribed_tiles():
    for mask, tile in enumerate(_MASK_TILES):
        for row in range(12):
            for col in range(6):
                bit = (isodata._MASK_BYTES[row][col] >> mask) & 1
                assert bit == int(tile[row % len(tile)][col]), (mask, row, col)


def test_emitted_format_information_is_valid():
    """Both format-information copies match, BCH-check, and name the
    error correction level and mask actually used."""
    for ecl in ("L", "M", "Q", "H"):
        enc = TextEncoder()
        matrix = enc.encode(QRCodeData("HuDoRa", auto_encoding=True), ecl)
        size = len(matrix)
        cols = [0, 1, 2, 3, 4, 5, 7, 8, 8, 8, 8, 8, 8, 8, 8]
        rows = [8, 8, 8, 8, 8, 8, 8, 8, 7, 5, 4, 3, 2, 1, 0]
        first = [matrix[r][c] for r, c in zip(rows, cols, strict=True)]
        second = [matrix[size - 1 - i][8] for i in range(7)] + [
            matrix[8][size - 8 + i] for i in range(8)
        ]
        assert second == first
        value = sum(bit << (14 - i) for i, bit in enumerate(first))
        unmasked = value ^ 0b101010000010010
        remainder = unmasked
        for bit in range(14, 9, -1):
            if remainder & (1 << bit):
                remainder ^= 0b10100110111 << (bit - 10)
        assert remainder == 0
        content = enc.minfo.create_matrix(enc.version, enc.codewords)
        chosen = enc.minfo.calc_mask_number(content)
        assert unmasked >> 10 == (STR2ECL[ecl] << 3) | chosen


# The golden grids pin the exact module pattern — including frame bits and
# mask choice — that decode round-trips would forgive drifting.
def test_module_grid_golden_version_1():
    matrix = QRCodeEncoder("HuDoRa", ecl="M").matrix
    assert ["".join(str(module) for module in row) for row in matrix] == [
        "111111101101001111111",
        "100000101011001000001",
        "101110101110001011101",
        "101110100100101011101",
        "101110101010101011101",
        "100000100111101000001",
        "111111101010101111111",
        "000000000111100000000",
        "100111111110110010111",
        "000011010000101011110",
        "010101101110011010111",
        "011010000111000000100",
        "110111100000001001110",
        "000000001101100001111",
        "111111101110111110100",
        "100000101001110111100",
        "101110101011101101011",
        "101110101001100000000",
        "101110100100001010011",
        "100000100110011011111",
        "111111101011000111100",
    ]


def test_module_grid_golden_version_11():
    """A version 11 symbol additionally exercises version-information
    placement (versions 7 and up)."""
    data = QRCodeData.wifi_network(
        ssid="MyNet",
        password="a2bc-de3f-ghi4",
        transition_disable=3,
        public_key="MDkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDIgADURzxmttZoIRIPWGoQMV00XHWCAQIhXruVWOz0NjlkIA=",
    )
    matrix = QRCodeEncoder(data, ecl="H").matrix
    assert ["".join(str(module) for module in row) for row in matrix] == [
        "1111111011001011010001101010001010000010111111010001101111111",
        "1000001011101100011101001000101100011111000100111101101000001",
        "1011101001001010110001001101010001000110100001111011101011101",
        "1011101011100110100001111001101110001010110010001110101011101",
        "1011101011111111111000000101111110001101110110000011001011101",
        "1000001011011010101010101011100011001011001100111110001000001",
        "1111111010101010101010101010101010101010101010101010101111111",
        "0000000000010000111011000111100011110010110101110101000000000",
        "0001001000100001100111011100111110001011101111111100000111011",
        "0011010110011011010010111011101101100011110001100011001101011",
        "0011101101000111110011110100001001010010111111011101011010010",
        "0001010101111010100100110010110001001111101110001010111110100",
        "1101011100110101110011111011000100111011001111111110111100000",
        "1111100101101001101011001001101101011001001101100101011000000",
        "0011101101001100101011111100011111011001010101111001100101101",
        "0111010111111000001000011111110000001111110101110011101111100",
        "0111111110101000011011001110000000110100001110011010111000101",
        "1000100011101000110001001111001101001101011010110110110110010",
        "1101011111110011101011110001101110001110100100110110100101101",
        "1111000011111011010110110110000010011100111101111100000101100",
        "1111001111001000101101101011111011101010011111100101101100011",
        "0010000011111100101010100100000000101010111001000101110000011",
        "1001101111001111110101010111111010100010110001000101011101010",
        "0000110111101001011100110011100101011101011011000110110011010",
        "0110111100101100101010000110000110101001111001110111111010010",
        "0100000000010101111100110010001101111000110101010011100100111",
        "1011011101010111010010110011111110111110001111010011111001111",
        "1010010101110010001110001100100111010001100000011011001011100",
        "1011111111000110101011010000111110111001111001000101111111001",
        "0111100011000000000010100011100010101010010011010000100010001",
        "0001101011111010010000101100101010010001101111000010101011101",
        "0110100010011101010000101010100011011000100001101110100010100",
        "0001111111000000010110100101111110001100001111111111111110100",
        "1001100101100001111111001000100000011000111000100111000101011",
        "0010011000011000100100100000011001011010101110000001001011001",
        "0101000111011000001111101011001111100100000110010101100110010",
        "1010101011110010111000011000001000110110111100100110000011101",
        "0111110110101011111000010110101111001100100010000001000001011",
        "0101011110001001001001000101011010010010110111001110010100111",
        "0110100111101011111101111111011100001011010111011011111010100",
        "0101011101011101100101011111011101101111101001010110110100011",
        "1111110111011101010010101011100101101001111111010101001110101",
        "0000011010111000101001000110011010011101001111111100010110011",
        "1111000110110011101111101110010101100100011101100111010010000",
        "0010101001001110010001111010110111111010101110111000010000100",
        "0101000101001010010000101010001100101000000001000011011100000",
        "0111011010000101100100000111011111010111111100000100010010100",
        "1000100001010010001111010101011111010011111011110010011000110",
        "1100011101100101100000011010010000100011101111101110010100111",
        "1011100100100100011110010101101100110100110101000111100011010",
        "0011111110011100011011111101101101011100111101111011101100101",
        "1110100101100111101100110110101111001010101000011110110010100",
        "1111001111110100100110100011111110010010100000001010111110010",
        "0000000011010010011001110101100010001100011010110100100011100",
        "1111111000111000010100110111101010010100001110110000101011111",
        "1000001000001101101100000100100010001100100001111010100011000",
        "1011101001101111000111101010111111011110101001110101111110100",
        "1011101011110111000111111010110111011100001001100011111111010",
        "1011101001100001000111101101101011000111111110111101111111001",
        "1000001001011101010111110101011110101011110111011001001011101",
        "1111111001101100101110111100110101111101111011100110101010001",
    ]
