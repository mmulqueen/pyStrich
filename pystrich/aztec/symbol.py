"""Aztec Code symbol geometry tables.

Maps ``(kind, layers)`` to the symbol's overall module dimension, total
codeword count, and codeword bit-width. Codeword width grows with layer
count: 6 bits for the smallest symbols, 12 bits for the largest.
"""

from __future__ import annotations

from typing import Literal

from pystrich.exceptions import PyStrichInvalidOption

SymbolKind = Literal["compact", "full"]

COMPACT_LAYERS = range(1, 5)
FULL_LAYERS = range(1, 33)

# (kind, layers) -> (module_count, total_codewords, codeword_bits)
# fmt: off
_SYMBOL_ATTRIBUTES: dict[tuple[SymbolKind, int], tuple[int, int, int]] = {
    ("compact",  1): (15,   17,  6),
    ("compact",  2): (19,   40,  6),
    ("compact",  3): (23,   51,  8),
    ("compact",  4): (27,   76,  8),
    ("full",     1): (19,   21,  6),
    ("full",     2): (23,   48,  6),
    ("full",     3): (27,   60,  8),
    ("full",     4): (31,   88,  8),
    ("full",     5): (37,  120,  8),
    ("full",     6): (41,  156,  8),
    ("full",     7): (45,  196,  8),
    ("full",     8): (49,  240,  8),
    ("full",     9): (53,  230, 10),
    ("full",    10): (57,  272, 10),
    ("full",    11): (61,  316, 10),
    ("full",    12): (67,  364, 10),
    ("full",    13): (71,  416, 10),
    ("full",    14): (75,  470, 10),
    ("full",    15): (79,  528, 10),
    ("full",    16): (83,  588, 10),
    ("full",    17): (87,  652, 10),
    ("full",    18): (91,  720, 10),
    ("full",    19): (95,  790, 10),
    ("full",    20): (101, 864, 10),
    ("full",    21): (105, 940, 10),
    ("full",    22): (109,1020, 10),
    ("full",    23): (113, 920, 12),
    ("full",    24): (117, 992, 12),
    ("full",    25): (121,1066, 12),
    ("full",    26): (125,1144, 12),
    ("full",    27): (131,1224, 12),
    ("full",    28): (135,1306, 12),
    ("full",    29): (139,1392, 12),
    ("full",    30): (143,1480, 12),
    ("full",    31): (147,1570, 12),
    ("full",    32): (151,1664, 12),
}
# fmt: on


def _lookup(kind: str, layers: int) -> tuple[int, int, int]:
    try:
        return _SYMBOL_ATTRIBUTES[(kind, layers)]  # type: ignore[index]
    except KeyError:
        raise PyStrichInvalidOption(
            f"no Aztec symbol with kind={kind!r}, layers={layers!r}; "
            f"expected kind='compact' with layers in {list(COMPACT_LAYERS)} "
            f"or kind='full' with layers in {list(FULL_LAYERS)}"
        ) from None


def module_count(kind: SymbolKind, layers: int) -> int:
    """Side length of the symbol in modules."""
    return _lookup(kind, layers)[0]


def total_codewords(kind: SymbolKind, layers: int) -> int:
    """Total codeword count in the data area (data + error correction)."""
    return _lookup(kind, layers)[1]


def codeword_bits(kind: SymbolKind, layers: int) -> int:
    """Bit-width of a single data codeword (6, 8, 10 or 12)."""
    return _lookup(kind, layers)[2]


def total_bits(kind: SymbolKind, layers: int) -> int:
    """Total bit capacity of the data area."""
    _, cw, bits = _lookup(kind, layers)
    return cw * bits
