"""Aztec encodation mode tables.

Six modes: Upper (U), Lower (L), Mixed (M), Punctuation (P), Digit (D) and
Byte (B). Encoding starts in Upper. U/L/M/P use 5-bit codewords; D uses
4-bit. Byte emits raw 8-bit values bracketed by a length prefix and
auto-returns to its caller.

The high-level encoder consults these tables and the latch/shift transition
costs to find the shortest bit sequence for an input byte string.
"""

from __future__ import annotations

# Mode labels — short single-character codes used as DP state keys.
U = "U"
L = "L"
M = "M"
P = "P"
D = "D"
B = "B"

ALL_MODES = (U, L, M, P, D)


# Per-mode char(byte value) -> codeword. Bit-width is 5 for U/L/M/P, 4 for D.
# Bytes not listed can only be encoded in Byte mode.
# fmt: off
CHAR_TABLE_UPPER: dict[int, int] = {
    32: 1,                          # SP
    **{65 + i: 2 + i for i in range(26)},  # A..Z -> 2..27
}

CHAR_TABLE_LOWER: dict[int, int] = {
    32: 1,                          # SP
    **{97 + i: 2 + i for i in range(26)},  # a..z -> 2..27
}

CHAR_TABLE_MIXED: dict[int, int] = {
    32: 1,                          # SP
    1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 7, 7: 8,        # SOH..BEL
    8: 9, 9: 10, 10: 11, 11: 12, 12: 13, 13: 14,     # BS, HT, LF, VT, FF, CR
    27: 15, 28: 16, 29: 17, 30: 18, 31: 19,          # ESC, FS, GS, RS, US
    64: 20, 92: 21, 94: 22, 95: 23, 96: 24,          # @ \ ^ _ `
    124: 25, 126: 26, 127: 27,                       # | ~ DEL
}

CHAR_TABLE_PUNCT: dict[int, int] = {
    13: 1,                                              # CR (alone)
    33: 6, 34: 7, 35: 8, 36: 9, 37: 10, 38: 11,         # ! " # $ % &
    39: 12, 40: 13, 41: 14, 42: 15, 43: 16, 44: 17,     # ' ( ) * + ,
    45: 18, 46: 19, 47: 20, 58: 21, 59: 22, 60: 23,     # - . / : ; <
    61: 24, 62: 25, 63: 26, 91: 27, 93: 28,             # = > ? [ ]
    123: 29, 125: 30,                                   # { }
}

# Two-byte sequences encoded as a single Punct codeword.
PUNCT_DIGRAPHS: dict[tuple[int, int], int] = {
    (13, 10): 2,                    # CR LF
    (46, 32): 3,                    # ". "
    (44, 32): 4,                    # ", "
    (58, 32): 5,                    # ": "
}

CHAR_TABLE_DIGIT: dict[int, int] = {
    32: 1,                          # SP
    **{48 + i: 2 + i for i in range(10)},  # 0..9 -> 2..11
    44: 12,                         # ,
    46: 13,                         # .
}
# fmt: on


CHAR_TABLES: dict[str, dict[int, int]] = {
    U: CHAR_TABLE_UPPER,
    L: CHAR_TABLE_LOWER,
    M: CHAR_TABLE_MIXED,
    P: CHAR_TABLE_PUNCT,
    D: CHAR_TABLE_DIGIT,
}

CHAR_BITS: dict[str, int] = {U: 5, L: 5, M: 5, P: 5, D: 4}


# Direct (one-hop) latch codewords: (from, to) -> (codeword_value, bit_width).
# Multi-hop paths fall out of the DP's relaxation.
# fmt: off
LATCH_CODEWORDS: dict[tuple[str, str], tuple[int, int]] = {
    (U, L): (28, 5),  (U, M): (29, 5),  (U, D): (30, 5),
    (L, M): (29, 5),  (L, D): (30, 5),
    (M, L): (28, 5),  (M, U): (29, 5),  (M, P): (30, 5),
    (P, U): (31, 5),
    (D, U): (14, 4),
}
# fmt: on


# Single-character shifts: (from, to) -> (codeword_value, bit_width).
# The encoder emits the shift, then the char in the target mode, then
# implicitly returns to the source mode.
# fmt: off
SHIFT_CODEWORDS: dict[tuple[str, str], tuple[int, int]] = {
    (U, P): (0, 5),
    (L, U): (28, 5),
    (L, P): (0, 5),
    (M, P): (0, 5),
    (D, U): (15, 4),
    (D, P): (0, 4),
}
# fmt: on


# Byte-shift codewords by source mode (B/S is always value 31, 5 bits, but
# only available from U/L/M; from P/D the encoder must latch first).
BYTE_SHIFT_CODEWORDS: dict[str, tuple[int, int]] = {
    U: (31, 5),
    L: (31, 5),
    M: (31, 5),
}

BYTE_SHIFT_FROM: frozenset[str] = frozenset(BYTE_SHIFT_CODEWORDS)
