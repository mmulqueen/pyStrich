"""Aztec text encoder — high-level DP + bit-stuff + RS + placement.

Pipeline:
  1. Encode the payload to a bit stream via the DP encoder (with an ECI
     prologue if the charset requires one).
  2. Pick the smallest symbol whose data capacity holds the bit-stuffed
     codewords plus the chosen error-correction percentage. Compact symbols
     are preferred over full-range when both fit at the same module count.
  3. Bit-stuff the bit stream into codewords of the chosen width.
  4. Reed-Solomon encode to produce the EC codewords.
  5. Build the mode message and call ``placement.build_matrix``.
"""

from __future__ import annotations

import math
from typing import Literal

from pystrich.aztec.bitstuff import to_codewords
from pystrich.aztec.data import AztecData
from pystrich.aztec.dpencoder import encode_high_level
from pystrich.aztec.modemessage import build_mode_message
from pystrich.aztec.placement import build_matrix
from pystrich.aztec.symbol import (
    COMPACT_LAYERS,
    FULL_LAYERS,
    SymbolKind,
    codeword_bits,
    module_count,
    total_codewords,
)
from pystrich.charset import Charset
from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption
from pystrich.reedsolomon import (
    BinaryExtensionGaloisField,
    GF64_0x43,
    GF256_0x12D,
    GF1024_0x409,
    GF4096_0x1069,
    reed_solomon_encode,
)

SymbolKindSpec = Literal["auto", "compact", "full"]

_RS_FIELD_BY_WIDTH: dict[int, BinaryExtensionGaloisField] = {
    6: GF64_0x43,
    8: GF256_0x12D,
    10: GF1024_0x409,
    12: GF4096_0x1069,
}

# Map the AztecData charset to the ECI number to prepend, or None for ASCII.
_ECI_BY_CHARSET: dict[Charset, int | None] = {
    "ascii": None,
    "iso-8859-1": 3,
    "utf-8": 26,
}


def _candidate_sizes(
    kind_pref: SymbolKindSpec, layers_override: int | None
) -> list[tuple[SymbolKind, int]]:
    """Symbol candidates in preferred size order.

    If a manual ``(kind, layers)`` was specified, only that one is returned.
    Otherwise candidates are sorted by ascending module count with compact
    preferred over full at the same module count.
    """
    if layers_override is not None:
        if kind_pref == "auto":
            raise PyStrichInvalidOption(
                "specify symbol_kind='compact' or 'full' when overriding layers="
            )
        return [(kind_pref, layers_override)]

    candidates: list[tuple[SymbolKind, int]] = []
    if kind_pref in ("auto", "compact"):
        candidates += [("compact", layer) for layer in COMPACT_LAYERS]
    if kind_pref in ("auto", "full"):
        candidates += [("full", layer) for layer in FULL_LAYERS]

    def sort_key(kl: tuple[SymbolKind, int]) -> tuple[int, int]:
        return (module_count(kl[0], kl[1]), 0 if kl[0] == "compact" else 1)

    candidates.sort(key=sort_key)
    return candidates


def _min_ec_needed(total_cw: int, ecc_pct: int) -> int:
    """Minimum EC codeword count for the requested ECC percentage."""
    return math.ceil(total_cw * ecc_pct / 100) + 3


class TextEncoder:
    """Builds an Aztec matrix from an :class:`AztecData` payload."""

    def encode(
        self,
        data: AztecData,
        *,
        ecc_pct: int,
        symbol_kind: SymbolKindSpec = "auto",
        layers: int | None = None,
    ) -> list[list[int]]:
        """Encode the payload to a 2D module matrix."""
        if not 5 <= ecc_pct <= 95:
            raise PyStrichInvalidOption(f"ecc must be between 5 and 95 (got {ecc_pct})")

        payload_bytes = "".join(data.segments).encode(data.encoding)
        eci = _ECI_BY_CHARSET[data.encoding]
        bits = encode_high_level(payload_bytes, eci=eci)

        kind, n_layers, codewords, num_ec = self._choose_size(bits, ecc_pct, symbol_kind, layers)

        width = codeword_bits(kind, n_layers)
        field = _RS_FIELD_BY_WIDTH[width]
        ec_codewords = reed_solomon_encode(codewords, field, num_ec, first_root=1)
        all_codewords = list(codewords) + list(ec_codewords)

        mode_word = build_mode_message(kind, layers=n_layers, data_codewords=len(codewords))

        return build_matrix(
            kind,
            layers=n_layers,
            codewords=all_codewords,
            mode_word=mode_word,
        )

    def _choose_size(
        self,
        bits: list[int],
        ecc_pct: int,
        kind_pref: SymbolKindSpec,
        layers_override: int | None,
    ) -> tuple[SymbolKind, int, list[int], int]:
        """Pick the smallest symbol that holds the bit-stuffed payload plus EC."""
        candidates = _candidate_sizes(kind_pref, layers_override)
        last_err: PyStrichInvalidInput | None = None
        for kind, n_layers in candidates:
            width = codeword_bits(kind, n_layers)
            total = total_codewords(kind, n_layers)
            codewords = to_codewords(bits, width)
            min_ec = _min_ec_needed(total, ecc_pct)
            if len(codewords) + min_ec <= total:
                # Fill all spare capacity with extra EC codewords.
                num_ec = total - len(codewords)
                return kind, n_layers, codewords, num_ec
            last_err = PyStrichInvalidInput(
                f"payload exceeds capacity of {kind} L{n_layers} "
                f"(needs {len(codewords)} data + {min_ec} EC codewords, "
                f"have {total})"
            )
        if last_err is not None and layers_override is not None:
            raise last_err
        raise PyStrichInvalidInput(f"payload too large for any Aztec symbol at ecc={ecc_pct}%")
