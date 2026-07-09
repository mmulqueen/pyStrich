"""ISO/IEC 18004:2006 tables and functions implementation"""

from __future__ import annotations

import functools
from collections.abc import Iterable, Sequence

# fmt: off
MAX_DATA_BITS: list[int] = [
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


MAX_CODEWORDS: list[int] = [
    0, 26, 44, 70, 100, 134, 172, 196, 242,
    292, 346, 404, 466, 532, 581, 655, 733, 815, 901, 991, 1085, 1156,
    1258, 1364, 1474, 1588, 1706, 1828, 1921, 2051, 2185, 2323, 2465,
    2611, 2761, 2876, 3034, 3196, 3362, 3532, 3706]


MATRIX_REMAIN_BIT: list[int] = [0, 0, 7, 7, 7, 7, 7, 0,
                     0, 0, 0, 0, 0, 0, 3, 3,
                     3, 3, 3, 3, 3, 4, 4, 4,
                     4, 4, 4, 4, 3, 3, 3, 3,
                     3, 3, 3, 0, 0, 0, 0, 0, 0]


# Error correction codewords per Reed-Solomon block and block count,
# indexed version - 1 + 40 * ecl like MAX_DATA_BITS (ECL rows: M, L, H, Q).
RS_ECC_CODEWORDS: tuple[int, ...] = (
    10, 16, 26, 18, 24, 16, 18, 22, 22, 26,
    30, 22, 22, 24, 24, 28, 28, 26, 26, 26,
    26, 28, 28, 28, 28, 28, 28, 28, 28, 28,
    28, 28, 28, 28, 28, 28, 28, 28, 28, 28,

    7, 10, 15, 20, 26, 18, 20, 24, 30, 18,
    20, 24, 26, 30, 22, 24, 28, 30, 28, 28,
    28, 28, 30, 30, 26, 28, 30, 30, 30, 30,
    30, 30, 30, 30, 30, 30, 30, 30, 30, 30,

    17, 28, 22, 16, 22, 28, 26, 26, 24, 28,
    24, 28, 22, 24, 24, 30, 28, 28, 26, 28,
    30, 24, 30, 30, 30, 30, 30, 30, 30, 30,
    30, 30, 30, 30, 30, 30, 30, 30, 30, 30,

    13, 22, 18, 26, 18, 24, 18, 22, 20, 24,
    28, 26, 24, 20, 30, 24, 28, 28, 26, 30,
    28, 30, 30, 30, 30, 28, 30, 30, 30, 30,
    30, 30, 30, 30, 30, 30, 30, 30, 30, 30)


RS_BLOCK_COUNT: tuple[int, ...] = (
    1, 1, 1, 2, 2, 4, 4, 4, 5, 5,
    5, 8, 9, 9, 10, 10, 11, 13, 14, 16,
    17, 17, 18, 20, 21, 23, 25, 26, 28, 29,
    31, 33, 35, 37, 38, 40, 43, 45, 47, 49,

    1, 1, 1, 1, 1, 2, 2, 2, 2, 4,
    4, 4, 4, 4, 6, 6, 6, 6, 7, 8,
    8, 9, 9, 10, 12, 12, 12, 13, 14, 15,
    16, 17, 18, 19, 19, 20, 21, 22, 24, 25,

    1, 1, 2, 4, 4, 4, 5, 6, 8, 8,
    11, 11, 16, 16, 18, 16, 19, 21, 25, 25,
    25, 34, 30, 32, 35, 37, 40, 42, 45, 48,
    51, 54, 57, 60, 63, 66, 70, 74, 77, 81,

    1, 1, 2, 2, 4, 4, 6, 6, 8, 8,
    8, 10, 12, 16, 12, 17, 16, 18, 21, 20,
    23, 23, 25, 27, 29, 34, 34, 35, 38, 40,
    43, 45, 48, 51, 53, 56, 59, 62, 65, 68)


# Alignment-pattern centre coordinates, indexed version - 1. The spacing
# is irregular (version 32 breaks every closed-form rule), so the whole
# table is kept literal.
ALIGNMENT_CENTRES: tuple[tuple[int, ...], ...] = (
    (), (6, 18), (6, 22), (6, 26), (6, 30), (6, 34),
    (6, 22, 38), (6, 24, 42), (6, 26, 46), (6, 28, 50), (6, 30, 54),
    (6, 32, 58), (6, 34, 62), (6, 26, 46, 66), (6, 26, 48, 70),
    (6, 26, 50, 74), (6, 30, 54, 78), (6, 30, 56, 82), (6, 30, 58, 86),
    (6, 34, 62, 90), (6, 28, 50, 72, 94), (6, 26, 50, 74, 98),
    (6, 30, 54, 78, 102), (6, 28, 54, 80, 106), (6, 32, 58, 84, 110),
    (6, 30, 58, 86, 114), (6, 34, 62, 90, 118), (6, 26, 50, 74, 98, 122),
    (6, 30, 54, 78, 102, 126), (6, 26, 52, 78, 104, 130),
    (6, 30, 56, 82, 108, 134), (6, 34, 60, 86, 112, 138),
    (6, 30, 58, 86, 114, 142), (6, 34, 62, 90, 118, 146),
    (6, 30, 54, 78, 102, 126, 150), (6, 24, 50, 76, 102, 128, 154),
    (6, 28, 54, 80, 106, 132, 158), (6, 32, 58, 84, 110, 136, 162),
    (6, 26, 54, 82, 110, 138, 166), (6, 30, 58, 86, 114, 142, 170))
# fmt: on


def _version_info_bits(version: int) -> int:
    """Return the 18-bit version information: 6 version bits followed by
    a 12-bit BCH error-correction remainder."""

    remainder = version << 12
    for bit in range(17, 11, -1):
        if remainder & (1 << bit):
            remainder ^= 0x1F25 << (bit - 12)
    return (version << 12) | remainder


def _build_frame(version: int) -> tuple[list[list[int]], list[list[bool]]]:
    """Build the function-pattern frame for a version.

    Returns ``(frame, occupied)``, both indexed ``[row][col]``: ``frame``
    holds the dark function modules that overlay the data matrix, while
    ``occupied`` additionally marks light function modules and the
    reserved format/version information areas so codeword placement
    skips them.
    """

    size = 17 + (version << 2)
    frame = [[0] * size for _ in range(size)]
    occupied = [[False] * size for _ in range(size)]

    def set_module(row: int, col: int, dark: bool) -> None:
        frame[row][col] = int(dark)
        occupied[row][col] = True

    # Finder patterns with their light separators at three corners.
    for row0, col0 in ((0, 0), (0, size - 7), (size - 7, 0)):
        for r in range(-1, 8):
            for c in range(-1, 8):
                row, col = row0 + r, col0 + c
                if 0 <= row < size and 0 <= col < size:
                    ring = r in (0, 6) or c in (0, 6)
                    core = 2 <= r <= 4 and 2 <= c <= 4
                    set_module(row, col, 0 <= r <= 6 and 0 <= c <= 6 and (ring or core))

    # Timing patterns: row and column 6, dark at even coordinates.
    for i in range(8, size - 8):
        set_module(6, i, i % 2 == 0)
        set_module(i, 6, i % 2 == 0)

    # Alignment patterns: 5x5 ring plus centre dot at each centre pair,
    # except the three that would sit on finder corners. Overlaps with
    # the timing patterns agree, so drawing over them is harmless.
    centres = ALIGNMENT_CENTRES[version - 1]
    for cr in centres:
        for cc in centres:
            if (cr < 9 and cc < 9) or (cr < 9 and cc > size - 10) or (cr > size - 10 and cc < 9):
                continue
            for r in range(-2, 3):
                for c in range(-2, 3):
                    set_module(cr + r, cc + c, max(abs(r), abs(c)) != 1)

    # Reserve the format information areas (light, filled in later) and
    # place the always-dark module above the bottom-left finder.
    for i in range(9):
        occupied[8][i] = True
        occupied[i][8] = True
    for i in range(8):
        occupied[8][size - 1 - i] = True
        occupied[size - 1 - i][8] = True
    set_module(size - 8, 8, True)

    # Version information for versions 7 and up: 18 bits in a 6x3 block
    # beside the top-right finder and its transpose above the bottom-left.
    if version >= 7:
        bits = _version_info_bits(version)
        for i in range(18):
            dark = bool((bits >> i) & 1)
            row, col = i // 3, size - 11 + i % 3
            set_module(row, col, dark)
            set_module(col, row, dark)

    return frame, occupied


def _placement_sequence(size: int, occupied: list[list[bool]]) -> list[tuple[int, int]]:
    """Return the data-module placement order as ``(col, row)`` pairs.

    Walks two-module column pairs right to left, alternating upward and
    downward, skipping the vertical timing column and occupied modules.
    """

    sequence: list[tuple[int, int]] = []
    col = size - 1
    upward = True
    while col > 0:
        if col == 6:
            col -= 1
        rows = range(size - 1, -1, -1) if upward else range(size)
        for row in rows:
            for c in (col, col - 1):
                if not occupied[row][c]:
                    sequence.append((c, row))
        upward = not upward
        col -= 2
    return sequence


def _mask_byte(row: int, col: int) -> int:
    """Pack the eight data-mask patterns for a module: bit ``i`` is set
    when mask pattern ``i`` darkens the module at ``(row, col)``."""

    product = row * col
    conditions = (
        (row + col) % 2 == 0,
        row % 2 == 0,
        col % 3 == 0,
        (row + col) % 3 == 0,
        (row // 2 + col // 3) % 2 == 0,
        product % 2 + product % 3 == 0,
        (product % 2 + product % 3) % 2 == 0,
        ((row + col) % 2 + product % 3) % 2 == 0,
    )
    return sum(1 << i for i, dark in enumerate(conditions) if dark)


# Every mask predicate is periodic: 12 rows (row parity, mod 3 and
# ``row // 2`` parity) by 6 columns (column parity, mod 3 and
# ``col // 3`` parity), so mask bytes come from this table as
# ``_MASK_BYTES[row % 12][col % 6]``.
_MASK_BYTES = tuple(tuple(_mask_byte(row, col) for col in range(6)) for row in range(12))


class MatrixInfo:
    """Provides QR Code version and Error Correction Level
    dependent information necessary for creating matrix"""

    byte_num: int
    matrix_d: list[list[int]]
    format_info: list[list[int]]
    rs_ecc_codewords: int
    rs_block_order: list[int]
    frame_data: list[list[int]]

    def __init__(self, version: int, ecl: int) -> None:
        total_codewords = MAX_CODEWORDS[version]
        self.byte_num = MATRIX_REMAIN_BIT[version] + (total_codewords << 3)

        table_index = version - 1 + 40 * ecl
        self.rs_ecc_codewords = RS_ECC_CODEWORDS[table_index]
        block_count = RS_BLOCK_COUNT[table_index]
        short_block, long_blocks = divmod(total_codewords, block_count)
        self.rs_block_order = [short_block] * (block_count - long_blocks) + [
            short_block + 1
        ] * long_blocks

        size = 17 + (version << 2)
        self.frame_data, occupied = _build_frame(version)
        walk = _placement_sequence(size, occupied)

        # The codeword buffer holds the data blocks back to back followed
        # by the error-correction blocks, but the symbol carries the
        # codewords interleaved round-robin across blocks. Map each stream
        # position back to its buffer codeword so the coordinate arrays
        # can stay indexed by buffer position.
        data_lengths = [block - self.rs_ecc_codewords for block in self.rs_block_order]
        data_starts = [sum(data_lengths[:b]) for b in range(block_count)]
        data_total = sum(data_lengths)
        buffer_order: list[int] = []
        for i in range(max(data_lengths)):
            buffer_order.extend(
                data_starts[b] + i for b in range(block_count) if i < data_lengths[b]
            )
        for i in range(self.rs_ecc_codewords):
            buffer_order.extend(
                data_total + b * self.rs_ecc_codewords + i for b in range(block_count)
            )

        xs = [0] * self.byte_num
        ys = [0] * self.byte_num
        for stream_pos, buffer_pos in enumerate(buffer_order):
            for bit in range(8):
                col, row = walk[(stream_pos << 3) + bit]
                xs[(buffer_pos << 3) + bit] = col
                ys[(buffer_pos << 3) + bit] = row
        for idx in range(total_codewords << 3, self.byte_num):  # remainder bits
            xs[idx], ys[idx] = walk[idx]
        self.matrix_d = [
            xs,
            ys,
            [_MASK_BYTES[ys[i] % 12][xs[i] % 6] for i in range(self.byte_num)],
        ]

        # Second format-information copy: below the top-right finder and
        # beside the bottom-left one.
        self.format_info = [
            [8] * 7 + list(range(size - 8, size)),
            [size - 1 - i for i in range(7)] + [8] * 8,
        ]

    def create_matrix(self, version: int, codewords: Sequence[int]) -> list[list[int]]:
        """Create matrix based on version and fills it w/ codewords"""

        mtx_size = 17 + (version << 2)
        matrix: list[list[int]] = [[0 for _ in range(mtx_size)] for _ in range(mtx_size)]

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

    def put_format_info(self, matrix: list[list[int]], format_info_value: int) -> None:
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

    def finalize(self, matrix_content: list[list[int]], mask_content: int) -> list[list[int]]:
        """Create final matrix and put frame data into it"""

        mtx_size = len(matrix_content)
        matrix: list[list[int]] = [[0 for _ in range(mtx_size)] for _ in range(mtx_size)]

        for i in range(mtx_size):
            for j in range(mtx_size):
                if (int(matrix_content[j][i]) & mask_content) != 0:
                    matrix[i][j] = 1
                else:
                    matrix[i][j] = self.frame_data[i][j]
        return matrix

    def calc_mask_number(self, matrix_content: list[list[int]]) -> int:
        """Pick the data mask that minimises the ISO 18004 penalty score.

        ``matrix_content`` is the per-mask packed matrix from
        :meth:`create_matrix`: bit ``i`` of cell ``[x][y]`` is 1 when the
        module is dark under mask ``i``.
        """
        mtx_size = len(matrix_content)
        packed_cols = [bytes(col) for col in matrix_content]
        packed_rows = [bytes(t) for t in zip(*packed_cols, strict=True)]
        best_mask = 0
        best_score = 0
        for mask_index in range(8):
            table = _MASK_EXTRACT[mask_index]
            rows = [line.translate(table) for line in packed_rows]
            cols = [line.translate(table) for line in packed_cols]
            lines_blob = _LINE_SEP.join(rows + cols)
            score = (
                _mask_penalty_n1(lines_blob)
                + _mask_penalty_n2(rows)
                + _mask_penalty_n3(lines_blob)
                + _mask_penalty_n4(rows, mtx_size * mtx_size)
            )
            if mask_index == 0 or score <= best_score:
                best_mask = mask_index
                best_score = score
        return best_mask


# The 1:1:3:1:1 finder pattern with its 4-module light flank before or
# after. Neither can overlap a copy of itself (the flank can't fall
# inside the dark-heavy core), so non-overlapping ``bytes.count`` is exact.
_FINDER_BEFORE = b"\x00\x00\x00\x00\x01\x00\x01\x01\x01\x00\x01"
_FINDER_AFTER = b"\x01\x00\x01\x01\x01\x00\x01\x00\x00\x00\x00"

# Module byte -> 1 where light; the line separator maps to 0, breaking runs.
_LIGHT_INDICATOR = bytes(1 if value == 0 else 0 for value in range(256))

# Lines are joined with a byte that is neither module colour, so one regex
# pass covers the whole symbol without a run or finder pattern matching
# across a line boundary.
_LINE_SEP = b"\x02"

# One translate table per mask pattern: packed cell byte -> the 0/1 module
# colour under that mask.
_MASK_EXTRACT = tuple(
    bytes(1 if value & (1 << mask) else 0 for value in range(256)) for mask in range(8)
)


def _mask_penalty_n1(lines_blob: bytes) -> int:
    """N1: runs of 5+ same-colour modules in a row or column.

    A run of length ``L >= 5`` scores ``L - 2``. With one byte lane per
    module, ANDing a colour's 0/1 indicator against itself shifted by
    1..k-1 lanes leaves a set bit where each k-module window of that
    colour starts, so ``bit_count`` gives ``W_k = sum(L - k + 1)``. Per
    run ``L - 2 == 3(L - 4) - 2(L - 5)``, so the score is ``3*W_5 - 2*W_6``.
    """
    score = 0
    # The raw blob serves as the dark indicator: the separator's bit 1
    # dies in the ANDs, as no other byte within five lanes ever sets it.
    for indicator in (lines_blob.translate(_LIGHT_INDICATOR), lines_blob):
        lanes = int.from_bytes(indicator, "big")
        w4 = lanes & (lanes >> 8) & (lanes >> 16) & (lanes >> 24)
        w5 = w4 & (lanes >> 32)
        w6 = w5 & (lanes >> 40)
        score += 3 * w5.bit_count() - 2 * w6.bit_count()
    return score


def _mask_penalty_n2(rows: Sequence[bytes]) -> int:
    """N2: 2x2 blocks of same-colour modules. 3 per block; overlaps count.

    Each row is loaded into a big int -- one byte lane per module -- and
    ``row + (row >> 8)`` puts the sum of each horizontally adjacent module
    pair in its right-hand module's lane, with no carries since lane values
    stay at most 4. Adding two adjacent rows' pair sums makes a lane 0 or 4
    exactly at the 2x2 same-colour blocks. Lane 0 holds only the left-edge
    column sum, not a pair, so it is masked off and dropped before counting.
    """
    width = len(rows[0])
    edge_mask = (1 << (8 * (width - 1))) - 1
    score = 0
    prev = int.from_bytes(rows[0], "big")
    prev += prev >> 8
    for y in range(1, len(rows)):
        cur = int.from_bytes(rows[y], "big")
        cur += cur >> 8
        lanes = ((prev + cur) & edge_mask).to_bytes(width - 1, "big")
        score += 3 * (lanes.count(0) + lanes.count(4))
        prev = cur
    return score


def _mask_penalty_n3(lines_blob: bytes) -> int:
    """N3: 1:1:3:1:1 dark/light pattern flanked by ≥4 light modules in a row or column.

    40 per occurrence; a finder pattern with light runs on both sides counts twice.
    """
    return 40 * (lines_blob.count(_FINDER_BEFORE) + lines_blob.count(_FINDER_AFTER))


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
