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
