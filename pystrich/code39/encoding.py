"""Encoding data tables for code39 barcode encoder

Source: MIL-STD-1189B, via: http://quicksearch.dla.mil/qsDocDetails.aspx?ident_number=36123"""

# Code39 encoding is deliberately represented in strings instead of bytestrings for ease of
# iteration.

# MIL-STD-1189B, page 21, Table VI
ascii_to_code39 = {
    b"\x00": "%U",  # NUL
    b"\x01": "$A",  # SOH
    b"\x02": "$B",  # STX
    b"\x03": "$C",  # ETX
    b"\x04": "$D",  # EOT
    b"\x05": "$E",  # ENQ
    b"\x06": "$F",  # ACK
    b"\x07": "$G",  # BEL
    b"\x08": "$H",  # BS
    b"\x09": "$I",  # HT
    b"\x0a": "$J",  # LF
    b"\x0b": "$K",  # VT
    b"\x0c": "$L",  # FF
    b"\x0d": "$M",  # CR
    b"\x0e": "$N",  # SO
    b"\x0f": "$O",  # SI
    b"\x10": "$P",  # DLE
    b"\x11": "$Q",  # DC1
    b"\x12": "$R",  # DC2
    b"\x13": "$S",  # DC3
    b"\x14": "$T",  # DC4
    b"\x15": "$U",  # NAK
    b"\x16": "$V",  # SYN
    b"\x17": "$W",  # ETB
    b"\x18": "$X",  # CAN
    b"\x19": "$Y",  # EM
    b"\x1a": "$Z",  # SUB
    b"\x1b": "%A",  # ESC
    b"\x1c": "%B",  # FS
    b"\x1d": "%C",  # GS
    b"\x1e": "%D",  # RS
    b"\x1f": "%E",  # US
    b" ": " ",  # Space
    b"!": "/A",
    b'"': "/B",
    b"#": "/C",
    b"$": "/D",
    b"%": "/E",
    b"&": "/F",
    b"'": "/G",
    b"(": "/H",
    b")": "/I",
    b"*": "/J",
    b"+": "/K",
    b",": "/L",
    b"-": "-",
    b".": ".",
    b"/": "/O",
    b"0": "0",
    b"1": "1",
    b"2": "2",
    b"3": "3",
    b"4": "4",
    b"5": "5",
    b"6": "6",
    b"7": "7",
    b"8": "8",
    b"9": "9",
    b":": "/Z",
    b";": "%F",
    b"<": "%G",
    b"=": "%H",
    b">": "%I",
    b"?": "%J",
    b"@": "%V",
    b"A": "A",
    b"B": "B",
    b"C": "C",
    b"D": "D",
    b"E": "E",
    b"F": "F",
    b"G": "G",
    b"H": "H",
    b"I": "I",
    b"J": "J",
    b"K": "K",
    b"L": "L",
    b"M": "M",
    b"N": "N",
    b"O": "O",
    b"P": "P",
    b"Q": "Q",
    b"R": "R",
    b"S": "S",
    b"T": "T",
    b"U": "U",
    b"V": "V",
    b"W": "W",
    b"X": "X",
    b"Y": "Y",
    b"Z": "Z",
    b"[": "%K",
    b"\\": "%L",
    b"]": "%M",
    b"^": "%N",
    b"_": "%O",
    b"`": "%W",
    b"a": "+A",
    b"b": "+B",
    b"c": "+C",
    b"d": "+D",
    b"e": "+E",
    b"f": "+F",
    b"g": "+G",
    b"h": "+H",
    b"i": "+I",
    b"j": "+J",
    b"k": "+K",
    b"l": "+L",
    b"m": "+M",
    b"n": "+N",
    b"o": "+O",
    b"p": "+P",
    b"q": "+Q",
    b"r": "+R",
    b"s": "+S",
    b"t": "+T",
    b"u": "+U",
    b"v": "+V",
    b"w": "+W",
    b"x": "+X",
    b"y": "+Y",
    b"z": "+Z",
    b"{": "%P",
    b"|": "%Q",
    b"}": "%R",
    b"~": "%S",
    b"\x7f": "%T",  # DEL
}

ascii_ord_to_code39 = {ord(k): v for k, v in ascii_to_code39.items()}

# MIL-STD-1189B, page 8
# 1 represents a wide bar/gap, 0 represents a narrow bar/gap
code39_bars_and_gaps = {
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


def build_code39_encodings():
    """Change representations so that 1 represents a narrow bar and 0 represents a narrow gap.
    # (11 = wide bar, 00 = wide gap)"""
    encodings = {}
    for symbol, bars_and_gaps in code39_bars_and_gaps.items():
        bars, gaps = bars_and_gaps
        new_seq = []
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


code39_encodings = build_code39_encodings()
