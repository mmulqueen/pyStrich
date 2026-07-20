"""Text encoder for 2D datamatrix barcode encoder"""

from __future__ import annotations

from typing import Literal, NamedTuple

from pystrich.charset import Charset, _HasMarkers
from pystrich.exceptions import PyStrichInvalidInput
from pystrich.reedsolomon import GF256_0x12D, reed_solomon_encode

from .data import (
    DataMatrixCodeword,
    DataMatrixData,
    fnc1_workaround_compat,
)
from .dpencoder import _pack_byte_by_byte, encode_high_level
from .modes import UNLATCH

# fmt: off
data_word_length: tuple[int, ...] = (3, 5, 8, 12, 18, 22, 30, 36, 44,
                                     62, 86, 114, 144, 174, 204,
                                     280, 368, 456, 576, 696, 816,
                                     1050, 1304, 1558)

error_word_length: tuple[int, ...] = (5, 7, 10, 12, 14, 18, 20, 24, 28,
                                      36, 42, 48, 56, 68, 84,
                                      112, 144, 192, 224, 272, 336,
                                      408, 496, 620)

data_region_size: tuple[int, ...] = (8, 10, 12, 14, 16, 18, 20, 22, 24,
                                     14, 16, 18, 20, 22, 24,
                                     14, 16, 18, 20, 22, 24,
                                     18, 20, 22)

hv_regions: tuple[int, ...] = (1, 1, 1, 1, 1, 1, 1, 1, 1,
                               2, 2, 2, 2, 2, 2,
                               4, 4, 4, 4, 4, 4,
                               6, 6, 6)

rs_blocks: tuple[int, ...] = (1, 1, 1, 1, 1, 1, 1, 1, 1,
                              1, 1, 1, 1, 1,
                              2, 2, 4, 4, 4, 4,
                              6, 6, 8, 10)
# fmt: on

SymbolShape = Literal["square", "rectangular", "auto"]


class _SymbolSpec(NamedTuple):
    """One ECC-200 symbol size: its data capacity and grid geometry.

    ``region_rows``/``region_cols`` size a single data region (finder pattern
    excluded); ``h_regions``/``v_regions`` are how many regions tile the symbol
    horizontally and vertically. The full mapping matrix the placer fills is
    ``region_rows * v_regions`` by ``region_cols * h_regions``.
    """

    data_words: int
    error_words: int
    rs_blocks: int
    region_rows: int
    region_cols: int
    h_regions: int
    v_regions: int
    shape: Literal["square", "rectangular"]


_SQUARE_SPECS: tuple[_SymbolSpec, ...] = tuple(
    _SymbolSpec(dw, ew, rb, region, region, hv, hv, "square")
    for dw, ew, region, hv, rb in zip(
        data_word_length, error_word_length, data_region_size, hv_regions, rs_blocks, strict=True
    )
)

# fmt: off
_RECT_SPECS: tuple[_SymbolSpec, ...] = (
    _SymbolSpec(5,  7,  1, 6,  16, 1, 1, "rectangular"),  # 8x18
    _SymbolSpec(10, 11, 1, 6,  14, 2, 1, "rectangular"),  # 8x32
    _SymbolSpec(16, 14, 1, 10, 24, 1, 1, "rectangular"),  # 12x26
    _SymbolSpec(22, 18, 1, 10, 16, 2, 1, "rectangular"),  # 12x36
    _SymbolSpec(32, 24, 1, 14, 16, 2, 1, "rectangular"),  # 16x36
    _SymbolSpec(49, 28, 1, 14, 22, 2, 1, "rectangular"),  # 16x48
)
# fmt: on

_ALL_SPECS: tuple[_SymbolSpec, ...] = _SQUARE_SPECS + _RECT_SPECS


def _total_area(spec: _SymbolSpec) -> int:
    """Total module count of the rendered symbol (each region adds a 2-module finder)."""
    return (spec.region_rows + 2) * spec.v_regions * ((spec.region_cols + 2) * spec.h_regions)


# Map the DataMatrix charset to the ECI number to prepend, or None for no ECI.
# iso-8859-1 emits the redundant ECI 3 designator so heuristic decoders
# (zxing-cpp) don't misinterpret short Upper-Shift sequences as another charset.
_ECI_BY_CHARSET: dict[Charset, int | None] = {
    "ascii": None,
    "iso-8859-1": 3,
    "utf-8": 26,
}

# Codeword that introduces an ECI designator (designator = ECI value + 1).
_ECI_INDICATOR = 241


class DataTooLongForImplementation(PyStrichInvalidInput):
    pass


def _randomise_pad(position: int) -> int:
    """253-state pad codeword randomisation."""
    pseudo_random = ((149 * position) % 253) + 1
    temp = 129 + pseudo_random
    return temp if temp <= 254 else temp - 254


class TextEncoder:
    """Text encoder class for 2D datamatrix"""

    codewords: list[int]
    size_index: int
    spec: _SymbolSpec
    mapping_rows: int
    mapping_cols: int

    def __init__(self) -> None:
        self.codewords = []
        self.size_index = 0

    def encode(
        self,
        text: DataMatrixData | str,
        *,
        force_byte_mode: bool = False,
        symbol_shape: SymbolShape = "square",
    ) -> list[int]:
        """Encode the given text and add padding and error codes
        also set up the correct matrix size for the resulting codewords"""

        self.codewords = []

        self.encode_text(text, force_byte_mode=force_byte_mode)

        self.pad(symbol_shape)

        self.append_error_codes()

        self.mapping_rows = self.spec.region_rows * self.spec.v_regions
        self.mapping_cols = self.spec.region_cols * self.spec.h_regions

        return self.codewords

    def encode_text(
        self,
        text: DataMatrixData | str,
        *,
        force_byte_mode: bool = False,
    ) -> None:
        """Encode the given text into codewords.

        With ``force_byte_mode=False`` (the default), marker-free input goes
        through the DP optimiser; payloads containing :class:`DataMatrixCodeword`
        markers (FNC1, compat high bytes) fall back to the single-mode
        byte-by-byte path because the DP can't represent the markers. Pass
        ``force_byte_mode=True`` to take the byte-by-byte path for any
        payload.
        """

        data = text if isinstance(text, DataMatrixData) else fnc1_workaround_compat(text)
        if force_byte_mode:
            self._encode_text_byte_by_byte(data)
            return
        try:
            plain_text, charset = data.as_plain_text()
        except _HasMarkers:
            self._encode_text_byte_by_byte(data)
        else:
            self._encode_text_dp(plain_text, charset)

    def _encode_text_dp(self, text: str, charset: Charset) -> None:
        """Multi-mode optimiser: pick the cheapest of ASCII/C40/Text/X12 per byte."""

        eci = _ECI_BY_CHARSET[charset]
        self.codewords.extend(encode_high_level(text.encode(charset), eci=eci))

    def _encode_text_byte_by_byte(self, data: DataMatrixData) -> None:
        """Single-mode byte-by-byte encoding via the ASCII mode: emits the ECI
        prologue for non-ASCII charsets, then digit-pair packs plain bytes and
        escapes high bytes with Upper Shift."""

        # DataMatrixData has already normalised compat by replacing high
        # codepoints with raw-codeword markers, so every str segment here is
        # encodable in its declared charset (treating compat as ASCII).
        charset = data.encoding
        eci = _ECI_BY_CHARSET[charset]
        if eci is not None:
            self.append_codeword(_ECI_INDICATOR)
            self.append_codeword(eci + 1)

        for segment in data.segments:
            if isinstance(segment, DataMatrixCodeword):
                self.append_codeword(segment.value)
            else:
                self.codewords.extend(_pack_byte_by_byte(segment.encode(charset)))

    def pad(self, symbol_shape: SymbolShape = "square") -> None:
        """Pad out the encoded text to the correct word length"""

        # If the trailing Unlatch would push us into the next symbol size,
        # drop it: an Unlatch is only required before pad bytes, so an
        # exact-fit symbol can omit it. The symbol actually selected must be
        # the exact fit -- "auto" picks by rendered area, so a capacity match
        # somewhere in the tables is not enough.
        if self.codewords and self.codewords[-1] == UNLATCH:
            try:
                exact_fit = (
                    self._select_spec(len(self.codewords) - 1, symbol_shape).data_words
                    == len(self.codewords) - 1
                )
            except DataTooLongForImplementation:
                # Too long for any symbol, so no exact fit; the selection
                # below reports the true stream length.
                exact_fit = False
            if exact_fit:
                self.codewords.pop()

        unpadded_len = len(self.codewords)

        self.spec = self._select_spec(unpadded_len, symbol_shape)

        # Number of characters with which the data will be padded
        padsize = self.spec.data_words - unpadded_len

        # First pad character is 129
        if padsize:
            self.append_codeword(129)

        # Remaining pad characters generated by 253-state algorithm
        for i in range(1, padsize):
            self.append_codeword(_randomise_pad(unpadded_len + i + 1))

    def _select_spec(self, unpadded_len: int, symbol_shape: SymbolShape) -> _SymbolSpec:
        """Pick the symbol that holds ``unpadded_len`` data codewords for the shape."""

        if symbol_shape == "rectangular":
            for spec in _RECT_SPECS:
                if spec.data_words >= unpadded_len:
                    return spec
            raise DataTooLongForImplementation(
                f"input requires {unpadded_len} data codewords; "
                f"largest ECC200 rectangular symbol holds {_RECT_SPECS[-1].data_words}"
            )

        if symbol_shape == "auto":
            fitting = [s for s in _ALL_SPECS if s.data_words >= unpadded_len]
            if not fitting:
                raise DataTooLongForImplementation(
                    f"input requires {unpadded_len} data codewords; "
                    f"largest supported ECC200 symbol holds {_SQUARE_SPECS[-1].data_words}"
                )
            # Smallest rendered symbol; on an area tie prefer the square, which
            # is more widely supported by scanners.
            return min(fitting, key=lambda s: (_total_area(s), s.shape != "square"))

        # square (default): keep size_index in step with the legacy tables.
        for self.size_index, spec in enumerate(_SQUARE_SPECS):
            if spec.data_words >= unpadded_len:
                return spec
        raise DataTooLongForImplementation(
            f"input requires {unpadded_len} data codewords; "
            f"largest supported ECC200 square symbol holds {_SQUARE_SPECS[-1].data_words}"
        )

    def append_error_codes(self) -> None:
        """Compute Reed-Solomon error correction codewords and append to the buffer.

        Larger symbols split the data into multiple interleaved blocks, each with
        its own RS codeword group; the EC bytes are then re-interleaved on the wire.
        """

        error_length = self.spec.error_words
        n_blocks = self.spec.rs_blocks
        ec_per_block = error_length // n_blocks
        blocks_data = [self.codewords[i::n_blocks] for i in range(n_blocks)]
        blocks_ec = [
            reed_solomon_encode(b, GF256_0x12D, ec_per_block, first_root=1) for b in blocks_data
        ]
        self.codewords.extend(blocks_ec[i][j] for j in range(ec_per_block) for i in range(n_blocks))

    def append_codeword(self, value: int) -> None:
        """Append a single codeword to the buffer."""

        self.codewords.append(value)
