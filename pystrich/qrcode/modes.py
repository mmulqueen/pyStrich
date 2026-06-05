"""QR Code encoding-mode tables for the high-level DP encoder.

Four of QR's data modes are modelled: Numeric (3 digits → 10 bits),
Alphanumeric (2 chars from a 45-symbol set → 11 bits), Byte (1 byte →
8 bits) and Kanji (1 JIS X 0208 character → 13 bits). Each mode carries
a 4-bit indicator; the character-count indicator width depends on the
symbol's version bracket.
"""

from __future__ import annotations

# Mode indices into the DP's dp / prev tables.
NUM = 0
ALPHA = 1
BYTE = 2
KANJI = 3
ALL_MODES: tuple[int, ...] = (NUM, ALPHA, BYTE, KANJI)

# 4-bit mode indicators emitted at the start of each segment.
MODE_INDICATOR: tuple[int, ...] = (
    0b0001,  # NUM
    0b0010,  # ALPHA
    0b0100,  # BYTE
    0b1000,  # KANJI
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
    ( 8, 10, 12),  # KANJI
)

# Bits emitted to flush a buffered phase when closing a segment.
# NUM phase=1: trailing single digit packs to 4 bits.
# NUM phase=2: trailing two digits pack to 7 bits.
# ALPHA phase=1: trailing single char packs to 6 bits.
# Phases that never occur (ALPHA=2, BYTE>0, KANJI>0) are left at 0.
CLOSE_COST: tuple[tuple[int, ...], ...] = (
    (0, 4, 7),  # NUM
    (0, 6, 0),  # ALPHA
    (0, 0, 0),  # BYTE
    (0, 0, 0),  # KANJI
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


def kanji_value(lead: int, trail: int) -> int | None:
    """Return the 13-bit Kanji-mode codeword for a Shift_JIS byte pair.

    ``None`` if ``lead`` isn't a kanji-mode lead byte (0x81-0x9F or
    0xE0-0xEB). Assumes the caller passes bytes from a valid Shift_JIS
    stream; under that precondition every kanji-range lead byte is
    followed by a valid trail byte. The arithmetic collapses both range
    families to a 13-bit value: subtract the range base, treat the
    result as a base-0xC0 pair.
    """
    if 0x81 <= lead <= 0x9F:
        shifted = ((lead << 8) | trail) - 0x8140
    elif 0xE0 <= lead <= 0xEB:
        shifted = ((lead << 8) | trail) - 0xC140
    else:
        return None
    return (shifted >> 8) * 0xC0 + (shifted & 0xFF)
