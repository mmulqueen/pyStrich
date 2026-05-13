"""Lookup tables for PDF417.

Reed-Solomon generator coefficients are computed on demand by
:func:`pystrich.reedsolomon.GF929.generator_coefficients` rather than
embedded here. Only the data that has no algorithmic source -- the
Text Compaction sub-mode character maps and the function-codeword
constants -- lives in this module.
"""

from __future__ import annotations

from typing import Final

# Function codewords for mode switching.
LATCH_TEXT: Final = 900
LATCH_BYTE: Final = 901
LATCH_NUMERIC: Final = 902
SHIFT_BYTE: Final = 913
LATCH_BYTE_MULT6: Final = 924
ECI_SMALL: Final = 927
"""ECI prefix for values 0-899; one codeword carrying the value follows.

PDF417 also defines codewords 926 and 925 for larger ECI values, but
UTF-8 (ECI 26) fits in the 927 range.
"""

# Text Compaction has four sub-modes. Each maps a base-30 value (0..29)
# to a character or a transition marker; slots 25 and 27-29 hold latches
# and shifts, the rest hold data characters. Pairs of base-30 values
# combine as ``h * 30 + l`` to produce one codeword.

LL: Final = "ll"  # latch to lower
LU: Final = "al"  # latch to alpha (upper)
LM: Final = "ml"  # latch to mixed
LP: Final = "pl"  # latch to punctuation
SU: Final = "as"  # shift to alpha (upper); reverts after one base-30 value
SP: Final = "ps"  # shift to punctuation; reverts after one base-30 value

# Position i in each tuple is the base-30 value that selects that
# character or transition. Latches and shifts go in the slots the spec
# pins them to; everything else is a single literal character.
# fmt: off
ALPHA: Final[tuple[str, ...]] = (
    "A", "B", "C", "D", "E", "F", "G", "H", "I", "J",
    "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T",
    "U", "V", "W", "X", "Y", "Z", " ", LL,  LM,  SP,
)

LOWER: Final[tuple[str, ...]] = (
    "a", "b", "c", "d", "e", "f", "g", "h", "i", "j",
    "k", "l", "m", "n", "o", "p", "q", "r", "s", "t",
    "u", "v", "w", "x", "y", "z", " ", SU,  LM,  SP,
)

MIXED: Final[tuple[str, ...]] = (
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "&", "\r", "\t", ",", ":", "#", "-", ".", "$", "/",
    "+", "%", "*", "=", "^", LP, " ", LL, LU, SP,
)

PUNCT: Final[tuple[str, ...]] = (
    ";", "<", ">", "@", "[", "\\", "]", "_", "`", "~",
    "!", "\r", "\t", ",", ":", "\n", "-", ".", "$", "/",
    '"', "|", "*", "(", ")", "?", "{", "}", "'", LU,
)
# fmt: on

# Sub-mode identifiers used as dictionary keys in the encoder.
SUB_ALPHA: Final = "alpha"
SUB_LOWER: Final = "lower"
SUB_MIXED: Final = "mixed"
SUB_PUNCT: Final = "punct"

TEXT_SUBMODES: Final[dict[str, tuple[str, ...]]] = {
    SUB_ALPHA: ALPHA,
    SUB_LOWER: LOWER,
    SUB_MIXED: MIXED,
    SUB_PUNCT: PUNCT,
}


# Reverse map: a character may live in several sub-modes (space is in
# Alpha, Lower and Mixed), so each entry is a list of placements.


def _build_char_table() -> dict[str, tuple[tuple[str, int], ...]]:
    table: dict[str, list[tuple[str, int]]] = {}
    for sub, row in TEXT_SUBMODES.items():
        for value, ch in enumerate(row):
            if len(ch) != 1:
                continue
            table.setdefault(ch, []).append((sub, value))
    return {ch: tuple(positions) for ch, positions in table.items()}


CHAR_TO_SUBMODE_VALUE: Final[dict[str, tuple[tuple[str, int], ...]]] = _build_char_table()
"""Map each text-encodable character to ``((sub-mode, base-30 value), ...)``.

Sub-modes are listed in the order they appear in :data:`TEXT_SUBMODES`; the
encoder iterates this tuple looking for the cheapest entry given its current
sub-mode.
"""


def ec_codeword_count(ecl: int) -> int:
    """Number of error correction codewords for level ``ecl`` (0..8).

    PDF417 uses ``2 ** (ecl + 1)`` EC codewords: 2, 4, 8, 16, 32, 64, 128, 256, 512.
    """
    if not 0 <= ecl <= 8:
        raise ValueError(f"PDF417 error correction level must be 0..8, got {ecl}")
    return 1 << (ecl + 1)
