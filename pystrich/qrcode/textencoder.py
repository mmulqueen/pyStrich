"""Text encoder for QR Code encoder"""

from __future__ import annotations

import logging

from pystrich.bitstream import BitStream
from pystrich.exceptions import PyStrichInvalidInput
from pystrich.reedsolomon import GF256_0x11D, reed_solomon_encode

from . import isodata
from .data import QRCodeData, QRCodeEncoding

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
        """Encode the given QRCodeData into bitstream"""

        encoded = "".join(data.segments).encode(data.encoding)
        eci = _ECI_DESIGNATOR[data.encoding]
        eci_overhead = 0 if eci is None else 12  # 4-bit ECI mode + 8-bit designator

        char_count_num = 8
        num_bytes = len(encoded)
        result_len = eci_overhead + 4 + char_count_num + 8 * num_bytes
        terminator_len = 4
        # Calculate smallest symbol version
        for self.version in range(1, 42):
            if self.version == 10:
                char_count_num = 16
                result_len += 8
            elif self.version == 41:
                raise PyStrichInvalidInput(f"QRCode cannot store {result_len} bits")

            max_bits = isodata.MAX_DATA_BITS[self.version - 1 + 40 * self.ecl]
            if max_bits >= result_len:
                if max_bits - result_len < 4:
                    terminator_len = max_bits - result_len
                self.max_data_codewords = max_bits >> 3
                break

        bitstream = BitStream()
        for byte in encoded:
            bitstream.append(byte, 8)

        bitstream.prepend(num_bytes, char_count_num)
        # write 'byte' mode
        bitstream.prepend(4, 4)
        if eci is not None:
            # ECI mode indicator 0111 followed by the 8-bit designator
            # (valid for ECI numbers up to 127).
            bitstream.prepend(eci, 8)
            bitstream.prepend(7, 4)
        # Terminator is 0-4 zero bits; omit when the data fills the symbol.
        if terminator_len > 0:
            bitstream.append(0, terminator_len)
        # convert bitstream into codewords
        byte = 0
        bit_num = 7
        for bit in bitstream.data:
            byte |= bit << bit_num
            bit_num -= 1
            if bit_num == -1:
                self.codewords.append(byte)
                bit_num = 7
                byte = 0
        # Pad the final partial byte to a codeword boundary. Only reachable
        # when an ECI prefix has shifted the bit stream off byte alignment.
        if bit_num != 7:
            self.codewords.append(byte)

    def pad(self) -> None:
        """Pad out the encoded text to the correct word length"""

        pads = [236, 17]
        pad_idx = 0
        for _ in range(len(self.codewords), self.max_data_codewords):
            self.codewords.append(pads[pad_idx])
            pad_idx = 1 - pad_idx

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
