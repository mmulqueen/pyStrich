"""DP high-level encoder tests for QR Code."""

from __future__ import annotations

import pytest

from pystrich.qrcode.dpencoder import encode_high_level


def _bits(*emissions: tuple[int, int]) -> list[int]:
    """Expand (value, width) tuples to an MSB-first bit list."""
    out: list[int] = []
    for value, width in emissions:
        for i in range(width - 1, -1, -1):
            out.append((value >> i) & 1)
    return out


# Mode-indicator nibbles.
_NUM = 0b0001
_ALPHA = 0b0010
_BYTE = 0b0100
_KANJI = 0b1000

# Shift_JIS ECI designator (enables Kanji mode in the DP).
_SJIS = 20


@pytest.mark.parametrize(
    "payload, bracket, expected",
    [
        pytest.param(b"A", 0, _bits((_ALPHA, 4), (1, 9), (10, 6)), id="single-A-picks-alpha"),
        pytest.param(b"5", 0, _bits((_NUM, 4), (1, 10), (5, 4)), id="single-digit-picks-numeric"),
        pytest.param(b"123", 0, _bits((_NUM, 4), (3, 10), (123, 10)), id="three-digits-numeric"),
        pytest.param(
            b"HELLO",
            0,
            _bits(
                (_ALPHA, 4),
                (5, 9),
                (17 * 45 + 14, 11),
                (21 * 45 + 21, 11),
                (24, 6),
            ),
            id="all-caps-picks-alpha",
        ),
        pytest.param(
            b"hello",
            0,
            _bits(
                (_BYTE, 4),
                (5, 8),
                (ord("h"), 8),
                (ord("e"), 8),
                (ord("l"), 8),
                (ord("l"), 8),
                (ord("o"), 8),
            ),
            id="all-lowercase-falls-back-to-byte",
        ),
        pytest.param(
            b"ABC123",
            0,
            _bits(
                (_ALPHA, 4),
                (6, 9),
                (10 * 45 + 11, 11),
                (12 * 45 + 1, 11),
                (2 * 45 + 3, 11),
            ),
            id="short-mix-stays-single-alpha-segment",
        ),
        pytest.param(
            b"AB12345678",
            0,
            _bits(
                (_ALPHA, 4),
                (2, 9),
                (10 * 45 + 11, 11),
                (_NUM, 4),
                (8, 10),
                (123, 10),
                (456, 10),
                (78, 7),
            ),
            id="long-digit-run-splits-into-alpha-plus-numeric",
        ),
        pytest.param(
            b"1",
            0,
            _bits((_NUM, 4), (1, 10), (1, 4)),
            id="numeric-trailing-one-digit",
        ),
        pytest.param(
            b"12",
            0,
            _bits((_NUM, 4), (2, 10), (12, 7)),
            id="numeric-trailing-two-digits",
        ),
        pytest.param(
            b"\xe9",
            0,
            _bits((_BYTE, 4), (1, 8), (0xE9, 8)),
            id="high-byte-forces-byte-mode",
        ),
        pytest.param(b"", 0, _bits((_BYTE, 4), (0, 8)), id="empty-payload-emits-byte-header-only"),
        pytest.param(
            b"HELLO",
            2,
            _bits(
                (_ALPHA, 4),
                (5, 13),
                (17 * 45 + 14, 11),
                (21 * 45 + 21, 11),
                (24, 6),
            ),
            id="bracket-27-40-uses-wider-char-count",
        ),
    ],
)
def test_optimal_encoding(payload: bytes, bracket: int, expected: list[int]) -> None:
    assert encode_high_level(payload, version_bracket=bracket) == expected


def test_eci_prologue_precedes_first_segment() -> None:
    expected = _bits(
        (0b0111, 4),
        (26, 8),
        (_NUM, 4),
        (3, 10),
        (123, 10),
    )
    assert encode_high_level(b"123", version_bracket=0, eci=26) == expected


def test_no_eci_emits_no_prologue() -> None:
    assert encode_high_level(b"A", version_bracket=0) == _bits((_ALPHA, 4), (1, 9), (10, 6))


# Kanji mode tests. The encoder turns Kanji on only when eci is the Shift_JIS
# designator (20); under any other ECI, kanji-lead-shaped bytes go through
# byte mode unchanged. The Shift_JIS encodings:
#   '中' = 0x9286  → kanji codeword 0xD06
#   '文' = 0x95B6  → kanji codeword 0xF76
#   '　' = 0x8140  → kanji codeword 0x000  (low boundary)
# The ECI prologue is (0b0111, 4) + (20, 8) = 12 bits, included in each
# expected emission.
_ECI20 = ((0b0111, 4), (20, 8))


@pytest.mark.parametrize(
    "payload, expected",
    [
        pytest.param(
            b"\x92\x86",
            _bits(*_ECI20, (_KANJI, 4), (1, 8), (0xD06, 13)),
            id="single-kanji-pair-picks-kanji-mode",
        ),
        pytest.param(
            b"\x81\x40",
            _bits(*_ECI20, (_KANJI, 4), (1, 8), (0, 13)),
            id="kanji-range-low-boundary",
        ),
        pytest.param(
            b"\xe0\x40",
            _bits(*_ECI20, (_KANJI, 4), (1, 8), (0x1740, 13)),
            id="upper-range-low-boundary",
        ),
        pytest.param(
            b"\xeb\xbf",
            _bits(*_ECI20, (_KANJI, 4), (1, 8), (0x1FFF, 13)),
            id="upper-range-high-boundary",
        ),
        pytest.param(
            # 0xA0 sits in the Shift_JIS half-width katakana band, outside
            # both kanji-lead ranges, so the pair falls through to BYTE.
            b"\xa0\x40",
            _bits(*_ECI20, (_BYTE, 4), (2, 8), (0xA0, 8), (0x40, 8)),
            id="half-width-katakana-not-treated-as-kanji-lead",
        ),
        pytest.param(
            # ASCII bytes have no kanji classification, so they go through
            # the usual alpha/num/byte selection.
            b"ABC",
            _bits(*_ECI20, (_ALPHA, 4), (3, 9), (10 * 45 + 11, 11), (12, 6)),
            id="ascii-under-sjis-eci-stays-alpha",
        ),
        pytest.param(
            # NUM run followed by Kanji pairs: NUM(10) wins over ALPHA over byte;
            # KANJI segment captures the two pairs.
            b"0123456789\x92\x86\x95\xb6",
            _bits(
                *_ECI20,
                (_NUM, 4),
                (10, 10),
                (12, 10),
                (345, 10),
                (678, 10),
                (9, 4),
                (_KANJI, 4),
                (2, 8),
                (0xD06, 13),
                (0xF76, 13),
            ),
            id="numeric-run-then-kanji-segments",
        ),
        pytest.param(
            # ALPHA run followed by Kanji pairs.
            b"HELLO\x92\x86\x95\xb6",
            _bits(
                *_ECI20,
                (_ALPHA, 4),
                (5, 9),
                (17 * 45 + 14, 11),
                (21 * 45 + 21, 11),
                (24, 6),
                (_KANJI, 4),
                (2, 8),
                (0xD06, 13),
                (0xF76, 13),
            ),
            id="alpha-run-then-kanji-segments",
        ),
    ],
)
def test_kanji_mode_under_sjis(payload: bytes, expected: list[int]) -> None:
    assert encode_high_level(payload, version_bracket=0, eci=_SJIS) == expected


def test_kanji_disabled_outside_sjis_eci() -> None:
    """Same bytes under ECI 26 (UTF-8) go through byte mode, not kanji."""
    payload = b"\x92\x86"
    expected = _bits((0b0111, 4), (26, 8), (_BYTE, 4), (2, 8), (0x92, 8), (0x86, 8))
    assert encode_high_level(payload, version_bracket=0, eci=26) == expected


@pytest.mark.parametrize(
    "bracket, count_width",
    [(0, 8), (1, 10), (2, 12)],
    ids=["bracket-1-9", "bracket-10-26", "bracket-27-40"],
)
def test_kanji_char_count_width_per_bracket(bracket: int, count_width: int) -> None:
    assert encode_high_level(b"\x92\x86", version_bracket=bracket, eci=_SJIS) == _bits(
        *_ECI20, (_KANJI, 4), (1, count_width), (0xD06, 13)
    )
