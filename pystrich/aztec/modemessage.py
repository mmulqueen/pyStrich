"""Aztec Mode Message construction.

The Mode Message encircles the finder pattern and tells a reader the symbol
size (number of data layers) and the message length (number of data
codewords). Both quantities are packed minus one, split into 4-bit nibbles,
and extended with Reed-Solomon checkwords over GF(16).
"""

from __future__ import annotations

from pystrich.aztec.symbol import COMPACT_LAYERS, FULL_LAYERS, SymbolKind
from pystrich.exceptions import PyStrichInvalidOption
from pystrich.reedsolomon import GF16_0x13, reed_solomon_encode

# kind -> (size_bits, length_bits, num_data_nibbles, num_ec_nibbles, max_data_codewords)
_KIND_PARAMS: dict[SymbolKind, tuple[int, int, int, int, int]] = {
    "compact": (2, 6, 2, 5, 64),
    "full": (5, 11, 4, 6, 2048),
}


def build_mode_message(kind: SymbolKind, *, layers: int, data_codewords: int) -> list[int]:
    """Return the mode message as a list of MSB-first bits.

    :param kind: ``"compact"`` (28-bit ring, 2+5 nibbles) or ``"full"``
        (40-bit ring, 4+6 nibbles).
    :param layers: Number of data layers (1..4 compact, 1..32 full).
    :param data_codewords: Number of data codewords the symbol carries.
    :returns: 28 bits (compact) or 40 bits (full), MSB-first.
    """
    if kind not in _KIND_PARAMS:
        raise PyStrichInvalidOption(f"unknown Aztec kind {kind!r}; expected 'compact' or 'full'")
    _, length_bits, num_data, num_ec, max_codewords = _KIND_PARAMS[kind]

    valid_layers = COMPACT_LAYERS if kind == "compact" else FULL_LAYERS
    if layers not in valid_layers:
        raise PyStrichInvalidOption(
            f"invalid layers={layers!r} for {kind} symbol; expected {list(valid_layers)!r}"
        )
    if not 1 <= data_codewords <= max_codewords:
        raise PyStrichInvalidOption(
            f"invalid data_codewords={data_codewords!r} for {kind} symbol; "
            f"expected 1..{max_codewords}"
        )

    packed = ((layers - 1) << length_bits) | (data_codewords - 1)
    nibbles = [(packed >> (4 * (num_data - 1 - i))) & 0xF for i in range(num_data)]
    ec = reed_solomon_encode(nibbles, GF16_0x13, num_ec, first_root=1)

    return [(nibble >> shift) & 1 for nibble in nibbles + ec for shift in (3, 2, 1, 0)]
