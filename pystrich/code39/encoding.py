"""Encoding data tables for code39 barcode encoder

Source: MIL-STD-1189B, via: http://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=36123"""

from __future__ import annotations

# MIL-STD-1189B, page 21, Table VI -- maps each ASCII byte (0-127) to its
# Code 39 representation (one or two symbols from the restricted set).
ascii_to_code39: dict[int, str] = {
    0x00: "%U",  # NUL
    0x01: "$A",  # SOH
    0x02: "$B",  # STX
    0x03: "$C",  # ETX
    0x04: "$D",  # EOT
    0x05: "$E",  # ENQ
    0x06: "$F",  # ACK
    0x07: "$G",  # BEL
    0x08: "$H",  # BS
    0x09: "$I",  # HT
    0x0A: "$J",  # LF
    0x0B: "$K",  # VT
    0x0C: "$L",  # FF
    0x0D: "$M",  # CR
    0x0E: "$N",  # SO
    0x0F: "$O",  # SI
    0x10: "$P",  # DLE
    0x11: "$Q",  # DC1
    0x12: "$R",  # DC2
    0x13: "$S",  # DC3
    0x14: "$T",  # DC4
    0x15: "$U",  # NAK
    0x16: "$V",  # SYN
    0x17: "$W",  # ETB
    0x18: "$X",  # CAN
    0x19: "$Y",  # EM
    0x1A: "$Z",  # SUB
    0x1B: "%A",  # ESC
    0x1C: "%B",  # FS
    0x1D: "%C",  # GS
    0x1E: "%D",  # RS
    0x1F: "%E",  # US
    0x20: " ",  # Space
    0x21: "/A",  # !
    0x22: "/B",  # "
    0x23: "/C",  # #
    0x24: "/D",  # $
    0x25: "/E",  # %
    0x26: "/F",  # &
    0x27: "/G",  # '
    0x28: "/H",  # (
    0x29: "/I",  # )
    0x2A: "/J",  # *
    0x2B: "/K",  # +
    0x2C: "/L",  # ,
    0x2D: "-",  # -
    0x2E: ".",  # .
    0x2F: "/O",  # /
    0x30: "0",
    0x31: "1",
    0x32: "2",
    0x33: "3",
    0x34: "4",
    0x35: "5",
    0x36: "6",
    0x37: "7",
    0x38: "8",
    0x39: "9",
    0x3A: "/Z",  # :
    0x3B: "%F",  # ;
    0x3C: "%G",  # <
    0x3D: "%H",  # =
    0x3E: "%I",  # >
    0x3F: "%J",  # ?
    0x40: "%V",  # @
    0x41: "A",
    0x42: "B",
    0x43: "C",
    0x44: "D",
    0x45: "E",
    0x46: "F",
    0x47: "G",
    0x48: "H",
    0x49: "I",
    0x4A: "J",
    0x4B: "K",
    0x4C: "L",
    0x4D: "M",
    0x4E: "N",
    0x4F: "O",
    0x50: "P",
    0x51: "Q",
    0x52: "R",
    0x53: "S",
    0x54: "T",
    0x55: "U",
    0x56: "V",
    0x57: "W",
    0x58: "X",
    0x59: "Y",
    0x5A: "Z",
    0x5B: "%K",  # [
    0x5C: "%L",  # \
    0x5D: "%M",  # ]
    0x5E: "%N",  # ^
    0x5F: "%O",  # _
    0x60: "%W",  # `
    0x61: "+A",  # a
    0x62: "+B",
    0x63: "+C",
    0x64: "+D",
    0x65: "+E",
    0x66: "+F",
    0x67: "+G",
    0x68: "+H",
    0x69: "+I",
    0x6A: "+J",
    0x6B: "+K",
    0x6C: "+L",
    0x6D: "+M",
    0x6E: "+N",
    0x6F: "+O",
    0x70: "+P",
    0x71: "+Q",
    0x72: "+R",
    0x73: "+S",
    0x74: "+T",
    0x75: "+U",
    0x76: "+V",
    0x77: "+W",
    0x78: "+X",
    0x79: "+Y",
    0x7A: "+Z",  # z
    0x7B: "%P",  # {
    0x7C: "%Q",  # |
    0x7D: "%R",  # }
    0x7E: "%S",  # ~
    0x7F: "%T",  # DEL
}

# MIL-STD-1189B, page 8
# 1 represents a wide bar/gap, 0 represents a narrow bar/gap
code39_bars_and_gaps: dict[str, tuple[str, str]] = {
    # symbol: (bars, gaps)
    # Numbers
    "1": ("10001", "0100"),
    "2": ("01001", "0100"),
    "3": ("11000", "0100"),
    "4": ("00101", "0100"),
    "5": ("10100", "0100"),
    "6": ("01100", "0100"),
    "7": ("00011", "0100"),
    "8": ("10010", "0100"),
    "9": ("01010", "0100"),
    "0": ("00110", "0100"),
    # Letters
    "A": ("10001", "0010"),
    "B": ("01001", "0010"),
    "C": ("11000", "0010"),
    "D": ("00101", "0010"),
    "E": ("10100", "0010"),
    "F": ("01100", "0010"),
    "G": ("00011", "0010"),
    "H": ("10010", "0010"),
    "I": ("01010", "0010"),
    "J": ("00110", "0010"),
    "K": ("10001", "0001"),
    "L": ("01001", "0001"),
    "M": ("11000", "0001"),
    "N": ("00101", "0001"),
    "O": ("10100", "0001"),
    "P": ("01100", "0001"),
    "Q": ("00011", "0001"),
    "R": ("10010", "0001"),
    "S": ("01010", "0001"),
    "T": ("00110", "0001"),
    "U": ("10001", "1000"),
    "V": ("01001", "1000"),
    "W": ("11000", "1000"),
    "X": ("00101", "1000"),
    "Y": ("10100", "1000"),
    "Z": ("01100", "1000"),
    "-": ("00011", "1000"),
    ".": ("10010", "1000"),
    " ": ("01010", "1000"),
    "*": ("00110", "1000"),
    "$": ("00000", "1110"),
    "/": ("00000", "1101"),
    "+": ("00000", "1011"),
    "%": ("00000", "0111"),
}


def build_code39_encodings() -> dict[str, str]:
    """Change representations so that 1 represents a narrow bar and 0 represents a narrow gap.
    # (11 = wide bar, 00 = wide gap)"""
    encodings: dict[str, str] = {}
    for symbol, bars_and_gaps in code39_bars_and_gaps.items():
        bars, gaps = bars_and_gaps
        new_seq: list[str] = []
        for i in range(5):
            if bars[i] == "0":
                new_seq.extend("1")
            else:
                new_seq.extend("11")
            if i == 4:
                break  # No 5th gap
            if gaps[i] == "0":
                new_seq.extend("0")
            else:
                new_seq.extend("00")
        encodings[symbol] = "".join(new_seq)
        assert len(encodings[symbol]) == 12  # 3 doubles and 6 singles = 12 total
    return encodings


code39_encodings: dict[str, str] = build_code39_encodings()
