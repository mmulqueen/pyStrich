"""ISO/IEC 18004:2006 tables and functions implementation"""

import functools
import re
from collections.abc import Iterable, Sequence
from pathlib import Path

from pystrich.exceptions import PyStrichError

_DATA_DIR = Path(__file__).parent / "qrcode_data"

# fmt: off
MAX_DATA_BITS = [
    128, 224, 352, 512, 688, 864, 992, 1232, 1456, 1728,
    2032, 2320, 2672, 2920, 3320, 3624, 4056, 4504, 5016, 5352,
    5712, 6256, 6880, 7312, 8000, 8496, 9024, 9544, 10136, 10984,
    11640, 12328, 13048, 13800, 14496, 15312, 15936, 16816, 17728, 18672,

    152, 272, 440, 640, 864, 1088, 1248, 1552, 1856, 2192,
    2592, 2960, 3424, 3688, 4184, 4712, 5176, 5768, 6360, 6888,
    7456, 8048, 8752, 9392, 10208, 10960, 11744, 12248, 13048, 13880,
    14744, 15640, 16568, 17528, 18448, 19472, 20528, 21616, 22496, 23648,

    72, 128, 208, 288, 368, 480, 528, 688, 800, 976,
    1120, 1264, 1440, 1576, 1784, 2024, 2264, 2504, 2728, 3080,
    3248, 3536, 3712, 4112, 4304, 4768, 5024, 5288, 5608, 5960,
    6344, 6760, 7208, 7688, 7888, 8432, 8768, 9136, 9776, 10208,

    104, 176, 272, 384, 496, 608, 704, 880, 1056, 1232,
    1440, 1648, 1952, 2088, 2360, 2600, 2936, 3176, 3560, 3880,
    4096, 4544, 4912, 5312, 5744, 6032, 6464, 6968, 7288, 7880,
    8264, 8920, 9368, 9848, 10288, 10832, 11408, 12016, 12656, 13328]


MAX_CODEWORDS = [
    0, 26, 44, 70, 100, 134, 172, 196, 242,
    292, 346, 404, 466, 532, 581, 655, 733, 815, 901, 991, 1085, 1156,
    1258, 1364, 1474, 1588, 1706, 1828, 1921, 2051, 2185, 2323, 2465,
    2611, 2761, 2876, 3034, 3196, 3362, 3532, 3706]


MATRIX_REMAIN_BIT = [0, 0, 7, 7, 7, 7, 7, 0,
                     0, 0, 0, 0, 0, 0, 3, 3,
                     3, 3, 3, 3, 3, 4, 4, 4,
                     4, 4, 4, 4, 3, 3, 3, 3,
                     3, 3, 3, 0, 0, 0, 0, 0, 0]
# fmt: on


class MatrixInfo:
    """Provides QR Code version and Error Correction Level
    dependent information necessary for creating matrix"""

    def __init__(self, version, ecl):
        self.byte_num = MATRIX_REMAIN_BIT[version] + (MAX_CODEWORDS[version] << 3)

        with (_DATA_DIR / f"qrv{version}_{ecl}.dat").open("rb") as f:
            self.matrix_d = [
                list(f.read(self.byte_num)),
                list(f.read(self.byte_num)),
                list(f.read(self.byte_num)),
            ]
            self.format_info = [list(f.read(15)), list(f.read(15))]
            self.rs_ecc_codewords = ord(f.read(1))
            self.rs_block_order = list(f.read(128))

        with (_DATA_DIR / f"qrvfr{version}.dat").open(encoding="ascii") as f:
            self.frame_data = []
            for line in f.read().splitlines():
                frame_line = []
                for char in line:
                    if char == "1":
                        frame_line.append(1)
                    elif char == "0":
                        frame_line.append(0)
                    else:
                        raise PyStrichError(f"Corrupted frame data file, found char: {char}")
                self.frame_data.append(frame_line)

    def create_matrix(self, version, codewords):
        """Create matrix based on version and fills it w/ codewords"""

        mtx_size = 17 + (version << 2)
        matrix = [[0 for i in range(mtx_size)] for j in range(mtx_size)]

        max_codewords = MAX_CODEWORDS[version]
        i = 0
        while i < max_codewords:
            codeword_i = codewords[i]
            j = 7
            while j >= 0:
                codeword_bits_number = (i << 3) + j
                pos_x = self.matrix_d[0][codeword_bits_number]
                pos_y = self.matrix_d[1][codeword_bits_number]
                mask = self.matrix_d[2][codeword_bits_number]
                matrix[pos_x][pos_y] = (255 * (codeword_i & 1)) ^ mask
                codeword_i >>= 1
                j -= 1
            i += 1

        for matrix_remain in range(MATRIX_REMAIN_BIT[version], 0, -1):
            remain_bit_temp = matrix_remain + (max_codewords << 3) - 1
            pos_x = self.matrix_d[0][remain_bit_temp]
            pos_y = self.matrix_d[1][remain_bit_temp]
            mask = self.matrix_d[2][remain_bit_temp]
            matrix[pos_x][pos_y] = 255 ^ mask
        return matrix

    def put_format_info(self, matrix, format_info_value):
        """Put format information into the matrix"""

        # fmt: off
        format_info = ["101010000010010", "101000100100101",
                       "101111001111100", "101101101001011",
                       "100010111111001", "100000011001110",
                       "100111110010111", "100101010100000",
                       "111011111000100", "111001011110011",
                       "111110110101010", "111100010011101",
                       "110011000101111", "110001100011000",
                       "110110001000001", "110100101110110",
                       "001011010001001", "001001110111110",
                       "001110011100111", "001100111010000",
                       "000011101100010", "000001001010101",
                       "000110100001100", "000100000111011",
                       "011010101011111", "011000001101000",
                       "011111100110001", "011101000000110",
                       "010010010110100", "010000110000011",
                       "010111011011010", "010101111101101"]
        # fmt: on

        format_info_x1 = [0, 1, 2, 3, 4, 5, 7, 8, 8, 8, 8, 8, 8, 8, 8]
        format_info_y1 = [8, 8, 8, 8, 8, 8, 8, 8, 7, 5, 4, 3, 2, 1, 0]
        for i in range(15):
            content = int(format_info[format_info_value][i]) * 255
            matrix[format_info_x1[i]][format_info_y1[i]] = content
            matrix[self.format_info[0][i]][self.format_info[1][i]] = content

    def finalize(self, matrix_content, mask_content):
        """Create final matrix and put frame data into it"""

        mtx_size = len(matrix_content)
        matrix = [[0 for i in range(mtx_size)] for j in range(mtx_size)]

        for i in range(mtx_size):
            for j in range(mtx_size):
                if (int(matrix_content[j][i]) & mask_content) != 0:
                    matrix[i][j] = 1
                else:
                    matrix[i][j] = self.frame_data[i][j]
        return matrix

    def calc_mask_number(self, matrix_content):
        """Pick the data mask that minimises the ISO 18004 penalty score.

        ``matrix_content`` is the per-mask packed matrix from
        :meth:`create_matrix`: bit ``i`` of cell ``[x][y]`` is 1 when the
        module is dark under mask ``i``.
        """
        mtx_size = len(matrix_content)
        best_mask = 0
        best_score = 0
        for mask_index in range(8):
            mask_bit = 1 << mask_index
            rows = [
                bytes((matrix_content[x][y] & mask_bit) != 0 for x in range(mtx_size))
                for y in range(mtx_size)
            ]
            cols = [bytes(row[x] for row in rows) for x in range(mtx_size)]
            lines = rows + cols
            score = (
                _mask_penalty_n1(lines)
                + _mask_penalty_n2(rows)
                + _mask_penalty_n3(lines)
                + _mask_penalty_n4(rows, mtx_size * mtx_size)
            )
            if mask_index == 0 or score <= best_score:
                best_mask = mask_index
                best_score = score
        return best_mask


# The 1:1:3:1:1 dark/light finder pattern only scores N3 when it has a
# 4-module light run on at least one side. Both flanks count separately,
# so a finder flanked on both sides contributes twice. Lookahead so
# overlapping occurrences are still counted.
_FINDER_BEFORE = re.compile(b"(?=\x00\x00\x00\x00\x01\x00\x01\x01\x01\x00\x01)")
_FINDER_AFTER = re.compile(b"(?=\x01\x00\x01\x01\x01\x00\x01\x00\x00\x00\x00)")
_N1_RUN_RE = re.compile(rb"\x00{5,}|\x01{5,}")


def _mask_penalty_n1(lines: Iterable[bytes]) -> int:
    """N1: runs of 5+ same-colour modules in a row or column.

    Each run of length ``L >= 5`` contributes ``L - 2`` (i.e. 3 + (L - 5)).
    """
    score = 0
    for line in lines:
        for m in _N1_RUN_RE.finditer(line):
            score += m.end() - m.start() - 2
    return score


def _mask_penalty_n2(rows: Sequence[bytes]) -> int:
    """N2: 2x2 blocks of same-colour modules. 3 per block; overlaps count."""
    score = 0
    n = len(rows)
    for y in range(n - 1):
        top = rows[y]
        bot = rows[y + 1]
        for x in range(n - 1):
            if top[x] == top[x + 1] == bot[x] == bot[x + 1]:
                score += 3
    return score


def _mask_penalty_n3(lines: Iterable[bytes]) -> int:
    """N3: 1:1:3:1:1 dark/light pattern flanked by ≥4 light modules in a row or column.

    40 per occurrence; a finder pattern with light runs on both sides counts twice.
    """
    score = 0
    for line in lines:
        score += len(_FINDER_BEFORE.findall(line)) + len(_FINDER_AFTER.findall(line))
    return score * 40


def _mask_penalty_n4(rows: Iterable[bytes], total_modules: int) -> int:
    """N4: 10 penalty per 5% deviation of dark-module proportion from 50%."""
    dark_count = sum(row.count(1) for row in rows)
    deviation = (dark_count * 100 / total_modules) - 50
    return abs(int(deviation / 5)) * 10


@functools.cache
def get_matrix_info(version: int, ecl: int) -> MatrixInfo:
    """Cached :class:`MatrixInfo` constructor.

    The instance is read-only after construction, so a single shared copy per
    (version, ECL) is safe and avoids re-reading the binary data files.
    """
    return MatrixInfo(version, ecl)
