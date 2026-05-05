"""Text encoder for QR Code encoder"""

import logging

from . import isodata
from pystrich.exceptions import PyStrichError, PyStrichInvalidInput

LOG = logging.getLogger("qrcode")

STR2ECL = {"L": 1, "l": 1, "M": 0, "m": 0, "Q": 3, "q": 3, "H": 2, "h": 2}


class BitStream:
    """Simple Bit stream implementation"""

    def __init__(self):

        self.data = []

    def append(self, value, bitsnum):
        """Append 'bitsnum' bits to the end of bit stream"""

        if bitsnum < 1:
            raise PyStrichError("Wrong value for number of bits (%d)" % bitsnum)
        for i in range(bitsnum - 1, -1, -1):
            self.data.append((value >> i) & 0x01)

    def prepend(self, value, bitsnum):
        """Prepend 'bitsnum' bits to the begining of bit stream"""

        if bitsnum < 1:
            raise PyStrichError("Wrong value for number of bits (%d)" % bitsnum)
        for i in range(0, bitsnum, 1):
            self.data.insert(0, (value >> i) & 0x01)


class TextEncoder:
    """Text encoder class for QR Code"""

    def __init__(self):

        self.version = None
        self.ecl = None
        self.codewords = []
        self.matrix = None
        self.mtx_size = 0
        self.minfo = None
        self.max_data_codewords = None

    def encode(self, text, ecl=None):
        """Encode the given text and add padding and error codes
        also set up the correct matrix size for the resulting codewords"""

        self.__init__()
        if ecl is None:
            ecl = 'M'
        self.ecl = STR2ECL[ecl]

        self.encode_text(text)

        self.pad()

        self.minfo = isodata.MatrixInfo(self.version, self.ecl)

        self.append_error_codes()

        LOG.debug(
            "Codewords: " + ' '.join([str(codeword) for codeword in self.codewords]))

        self.create_matrix()

        return self.matrix

    def encode_text(self, text):
        """Encode the given text into bitstream"""

        char_count_num = 8
        result_len = 4 + char_count_num + 8 * len(text)
        terminator_len = 4
        # Calculate smallest symbol version
        for self.version in range(1, 42):
            if self.version == 10:
                char_count_num = 16
                result_len += 8
            elif self.version == 41:
                raise PyStrichInvalidInput("QRCode cannot store %d bits" % result_len)

            max_bits = isodata.MAX_DATA_BITS[self.version - 1 + 40 * self.ecl]
            if max_bits >= result_len:
                if max_bits - result_len < 4:
                    terminator_len = max_bits - result_len
                self.max_data_codewords = max_bits >> 3
                break

        bitstream = BitStream()
        for char in text:
            bitstream.append(ord(char), 8)

        bitstream.prepend(len(text), char_count_num)
        # write 'byte' mode
        bitstream.prepend(4, 4)
        # add terminator
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

    def pad(self):
        """Pad out the encoded text to the correct word length"""

        pads = [236, 17]
        pad_idx = 0
        for _ in range(len(self.codewords), self.max_data_codewords):
            self.codewords.append(pads[pad_idx])
            pad_idx = 1 - pad_idx

    def append_error_codes(self):
        """Calculate the necessary number of error codes for the encoded
        text and padding codewords, and append to the codeword buffer"""

        i = 0
        j = 0
        rs_block_number = 0
        rs_temp = [[]]
        while i < self.max_data_codewords:

            rs_temp[rs_block_number].append(self.codewords[i])

            j += 1
            if j >= self.minfo.rs_block_order[rs_block_number] - self.minfo.rs_ecc_codewords:
                j = 0
                rs_block_number += 1
                rs_temp.append([])
            i += 1

        rs_block_number = 0
        rs_block_order_num = len(self.minfo.rs_block_order)

        while rs_block_number < rs_block_order_num:
            rs_codewords = self.minfo.rs_block_order[rs_block_number]
            rs_data_codewords = rs_codewords - self.minfo.rs_ecc_codewords

            rstemp = rs_temp[rs_block_number] + [0] * self.minfo.rs_ecc_codewords
            j = rs_data_codewords
            while j > 0:
                first = rstemp[0]
                if first != 0:
                    rstemp = rstemp[1:]
                    cal = list(self.minfo.rs_cal_table[first])

                    if len(rstemp) < len(cal):
                        rstemp, cal = cal, rstemp
                    cal += [0] * (len(rstemp) - len(cal))
                    rstemp = [x1 ^ x2 for x1, x2 in zip(rstemp, cal)]
                else:
                    rstemp = rstemp[1:]
                j -= 1
            self.codewords += rstemp
            rs_block_number += 1

    def create_matrix(self):
        """Create QR Code matrix"""

        matrix_content = self.minfo.create_matrix(self.version, self.codewords)
        self.mtx_size = len(matrix_content)

        LOG.debug("Matrix size is %d", self.mtx_size)

        mask_number = self.minfo.calc_mask_number(matrix_content)
        mask_content = 1 << mask_number

        format_info_value = ((self.ecl << 3) | mask_number)
        self.minfo.put_format_info(matrix_content, format_info_value)
        self.matrix = self.minfo.finalize(matrix_content, mask_content)
