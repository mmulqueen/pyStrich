"""Text encoder for 2D datamatrix barcode encoder"""

from __future__ import annotations

from collections.abc import Iterable

from pystrich.exceptions import PyStrichInvalidInput
from pystrich.reedsolomon import GF256_0x12D, reed_solomon_encode

from .data import DataMatrixCodeword, DataMatrixData, fnc1_workaround_compat

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
    mtx_size: int
    regions: int

    def __init__(self) -> None:
        self.codewords = []
        self.size_index = 0
        self.mtx_size = 0
        self.regions = 0

    def encode(self, text: DataMatrixData | str) -> list[int]:
        """Encode the given text and add padding and error codes
        also set up the correct matrix size for the resulting codewords"""

        self.codewords = []

        self.encode_text(text)

        self.pad()

        self.append_error_codes()

        self.mtx_size = data_region_size[self.size_index]
        self.regions = hv_regions[self.size_index]

        return self.codewords

    def encode_text(self, text: DataMatrixData | str) -> None:
        """Encode the given text into codewords"""

        data = text if isinstance(text, DataMatrixData) else fnc1_workaround_compat(text)

        if data.encoding == "utf-8":
            # Codeword 241 (ECI) + 27 (ECI value 26 + 1) declares UTF-8 for the
            # remainder of the symbol. Emitted once, before any data.
            self.append_codeword(241)
            self.append_codeword(27)

        numbuf = ""

        def flush_numbuf() -> None:
            nonlocal numbuf
            if len(numbuf) == 2:
                self.append_digits(numbuf)
            elif numbuf:
                self.append_byte(ord(numbuf))
            numbuf = ""

        for segment in data.segments:
            if isinstance(segment, DataMatrixCodeword):
                flush_numbuf()
                self.append_codeword(segment.value)
                continue

            # Compat mode tolerates codepoints outside its nominal ASCII charset,
            # so .encode() would raise; everything else maps cleanly to bytes.
            byte_iter: Iterable[int] = (
                map(ord, segment) if data.encoding == "compat" else segment.encode(data.encoding)
            )

            for byte in byte_iter:
                if 0x30 <= byte <= 0x39:  # ASCII '0'-'9'
                    numbuf += chr(byte)
                    if len(numbuf) == 2:
                        flush_numbuf()
                    continue
                flush_numbuf()
                if data.encoding == "compat":
                    # Legacy +1 offset preserved for backwards compat: emits
                    # codewords > 255 for non-ASCII input (broken on purpose).
                    self.append_codeword(byte + 1)
                else:
                    self.append_byte(byte)

        flush_numbuf()

    def pad(self) -> None:
        """Pad out the encoded text to the correct word length"""

        unpadded_len = len(self.codewords)

        if unpadded_len > data_word_length[-1]:
            raise DataTooLongForImplementation(
                f"input requires {unpadded_len} data codewords; "
                f"largest supported ECC200 square symbol holds {data_word_length[-1]}"
            )

        # Work out how big the matrix needs to be
        for self.size_index, length in enumerate(data_word_length):
            if length >= unpadded_len:
                break

        # Number of characters with which the data will be padded
        padsize = length - unpadded_len

        # First pad character is 129
        if padsize:
            self.append_codeword(129)

        # Remaining pad characters generated by 253-state algorithm
        for i in range(1, padsize):
            self.append_codeword(_randomise_pad(unpadded_len + i + 1))

    def append_error_codes(self) -> None:
        """Compute Reed-Solomon error correction codewords and append to the buffer.

        Larger symbols split the data into multiple interleaved blocks, each with
        its own RS codeword group; the EC bytes are then re-interleaved on the wire.
        """

        error_length = error_word_length[self.size_index]
        n_blocks = rs_blocks[self.size_index]
        ec_per_block = error_length // n_blocks
        blocks_data = [self.codewords[i::n_blocks] for i in range(n_blocks)]
        blocks_ec = [
            reed_solomon_encode(b, GF256_0x12D, ec_per_block, first_root=1) for b in blocks_data
        ]
        self.codewords.extend(blocks_ec[i][j] for j in range(ec_per_block) for i in range(n_blocks))

    def append_codeword(self, value: int) -> None:
        """Append a single codeword to the buffer."""

        self.codewords.append(value)

    def append_digits(self, digits: str) -> None:
        """Append a pair of digits as a single codeword (130 + integer value)."""

        self.append_codeword(130 + int(digits))

    def append_byte(self, byte: int) -> None:
        """Append a data byte: ASCII (0-127) as codeword byte+1; high byte
        (128-255) as Upper Shift (235) + (byte-127)."""

        if byte > 127:
            self.append_codeword(235)
            self.append_codeword(byte - 127)
        else:
            self.append_codeword(byte + 1)
