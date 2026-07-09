"""Text encoder for QR Code encoder"""

from __future__ import annotations

import itertools
import logging

from pystrich.exceptions import PyStrichInvalidInput
from pystrich.reedsolomon import GF256_0x11D, reed_solomon_encode

from . import isodata
from .data import QRCodeData, QRCodeEncoding
from .dpencoder import encode_high_level
from .modes import bracket_for_version

LOG = logging.getLogger("qrcode")

STR2ECL: dict[str, int] = {"L": 1, "l": 1, "M": 0, "m": 0, "Q": 3, "q": 3, "H": 2, "h": 2}

# The spec defaults byte mode to ISO-8859-1 with no ECI, but real
# decoders disagree (some apply Shift-JIS heuristics on high bytes).
# Emit ECI 3 explicitly for Latin-1 to remove the ambiguity. Pure ASCII
# is safe everywhere with no ECI; UTF-8 needs ECI 26.
_ECI_DESIGNATOR: dict[QRCodeEncoding, int | None] = {
    "ascii": None,
    "iso-8859-1": 3,
    "utf-8": 26,
    "shift_jis": 20,
}


class TextEncoder:
    """Text encoder class for QR Code"""

    version: int
    ecl: int
    codewords: list[int]
    matrix: list[list[int]]
    mtx_size: int
    minfo: isodata.MatrixInfo
    max_data_codewords: int

    def __init__(self) -> None:
        self.version = 0
        self.ecl = 0
        self.codewords = []
        self.matrix = []
        self.mtx_size = 0
        self.max_data_codewords = 0

    def encode(self, data: QRCodeData, ecl: str | None = None) -> list[list[int]]:
        """Encode the given data and add padding and error codes
        also set up the correct matrix size for the resulting codewords"""

        self.codewords = []
        if ecl is None:
            ecl = "M"
        self.ecl = STR2ECL[ecl]

        self.encode_text(data)

        self.pad()

        self.minfo = isodata.get_matrix_info(self.version, self.ecl)

        self.append_error_codes()

        LOG.debug("Codewords: " + " ".join([str(codeword) for codeword in self.codewords]))

        self.create_matrix()

        return self.matrix

    def encode_text(self, data: QRCodeData) -> None:
        """Encode the given QRCodeData into the codeword buffer."""

        text, charset = data.as_plain_text()
        encoded = text.encode(charset)
        eci = _ECI_DESIGNATOR[charset]

        # Bit cost never decreases from one bracket to the next (only the
        # segment headers widen), so a computed bracket's bit count is a
        # lower bound for higher brackets and rules versions out without
        # re-running the encoder.
        bits_by_bracket: dict[int, list[int]] = {}
        bound = 0
        for self.version in range(1, 41):
            max_bits = isodata.MAX_DATA_BITS[self.version - 1 + 40 * self.ecl]
            if max_bits < bound:
                continue
            bracket = bracket_for_version(self.version)
            if bracket not in bits_by_bracket:
                bits_by_bracket[bracket] = encode_high_level(
                    encoded, version_bracket=bracket, eci=eci
                )
                bound = len(bits_by_bracket[bracket])
            bits = bits_by_bracket[bracket]
            if max_bits >= len(bits):
                terminator_len = min(4, max_bits - len(bits))
                self.max_data_codewords = max_bits // 8
                break
        else:
            if (bits_at_40 := bits_by_bracket.get(2)) is None:
                bits_at_40 = encode_high_level(encoded, version_bracket=2, eci=eci)
            raise PyStrichInvalidInput(
                f"payload needs {len(bits_at_40)} bits at version 40; "
                f"no QR symbol at ECL {self.ecl} holds this"
            )

        self._pack_bits(bits, terminator_len)

    def _pack_bits(self, bits: list[int], terminator_len: int) -> None:
        """Append terminator zeros then pack the bit stream into codewords."""

        bits = bits + [0] * terminator_len
        bits += [0] * (-len(bits) % 8)  # pad final byte to a codeword boundary
        for i in range(0, len(bits), 8):
            byte = 0
            for bit in bits[i : i + 8]:
                byte = (byte << 1) | bit
            self.codewords.append(byte)

    def pad(self) -> None:
        """Pad out the encoded text to the correct word length"""

        pad_cycle = itertools.cycle((236, 17))
        for _ in range(len(self.codewords), self.max_data_codewords):
            self.codewords.append(next(pad_cycle))

    def append_error_codes(self) -> None:
        """Calculate the necessary number of error codes for the encoded
        text and padding codewords, and append to the codeword buffer"""

        i = 0
        j = 0
        rs_block_number = 0
        rs_temp: list[list[int]] = [[]]
        while i < self.max_data_codewords:
            rs_temp[rs_block_number].append(self.codewords[i])

            j += 1
            if j >= self.minfo.rs_block_order[rs_block_number] - self.minfo.rs_ecc_codewords:
                j = 0
                rs_block_number += 1
                rs_temp.append([])
            i += 1

        for block_number in range(len(self.minfo.rs_block_order)):
            ec = reed_solomon_encode(
                rs_temp[block_number], GF256_0x11D, self.minfo.rs_ecc_codewords
            )
            self.codewords += ec

    def create_matrix(self) -> None:
        """Create QR Code matrix"""

        matrix_content = self.minfo.create_matrix(self.version, self.codewords)
        self.mtx_size = len(matrix_content)

        LOG.debug("Matrix size is %d", self.mtx_size)

        mask_number = self.minfo.calc_mask_number(matrix_content)
        mask_content = 1 << mask_number

        format_info_value = (self.ecl << 3) | mask_number
        self.minfo.put_format_info(matrix_content, format_info_value)
        self.matrix = self.minfo.finalize(matrix_content, mask_content)
