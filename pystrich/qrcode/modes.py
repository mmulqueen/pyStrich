"""QR Code encoding-mode tables for the high-level DP encoder.

Three of QR's four data modes are modelled here: Numeric (3 digits → 10
bits), Alphanumeric (2 chars from a 45-symbol set → 11 bits) and Byte (1
byte → 8 bits). Kanji is deferred. Each mode carries a 4-bit indicator;
the character-count indicator width depends on the symbol's version
bracket.
"""

from __future__ import annotations

# Mode indices into the DP's dp / prev tables.
NUM = 0
ALPHA = 1
BYTE = 2
ALL_MODES: tuple[int, ...] = (NUM, ALPHA, BYTE)

# 4-bit mode indicators emitted at the start of each segment.
MODE_INDICATOR: tuple[int, ...] = (
    0b0001,  # NUM
    0b0010,  # ALPHA
    0b0100,  # BYTE
)

# Version brackets: 1-9, 10-26, 27-40 (zero-indexed below).
BRACKET_1_9 = 0
BRACKET_10_26 = 1
BRACKET_27_40 = 2
ALL_BRACKETS: tuple[int, ...] = (BRACKET_1_9, BRACKET_10_26, BRACKET_27_40)

# Character-count indicator widths, indexed [mode][bracket].
# fmt: off
CHAR_COUNT_BITS: tuple[tuple[int, ...], ...] = (
    (10, 12, 14),  # NUM
    ( 9, 11, 13),  # ALPHA
    ( 8, 16, 16),  # BYTE
)

# Bits emitted to flush a buffered phase when closing a segment.
# NUM phase=1: trailing single digit packs to 4 bits.
# NUM phase=2: trailing two digits pack to 7 bits.
# ALPHA phase=1: trailing single char packs to 6 bits.
# Phases that never occur (ALPHA=2, BYTE>0) are left at 0.
CLOSE_COST: tuple[tuple[int, ...], ...] = (
    (0, 4, 7),  # NUM
    (0, 6, 0),  # ALPHA
    (0, 0, 0),  # BYTE
)
# fmt: on


def bracket_for_version(version: int) -> int:
    """Return the version-bracket index for ``version`` (1..40)."""
    if version <= 9:
        return BRACKET_1_9
    if version <= 26:
        return BRACKET_10_26
    return BRACKET_27_40


def _build_alpha_value() -> tuple[int, ...]:
    """For each byte 0..255, its Alphanumeric value, or -1 if not in the set."""
    out: list[int] = [-1] * 256
    for d in range(10):
        out[0x30 + d] = d  # '0'..'9'
    for i in range(26):
        out[0x41 + i] = 10 + i  # 'A'..'Z'
    out[0x20] = 36  # space
    out[0x24] = 37  # $
    out[0x25] = 38  # %
    out[0x2A] = 39  # *
    out[0x2B] = 40  # +
    out[0x2D] = 41  # -
    out[0x2E] = 42  # .
    out[0x2F] = 43  # /
    out[0x3A] = 44  # :
    return tuple(out)


ALPHA_VALUE: tuple[int, ...] = _build_alpha_value()
