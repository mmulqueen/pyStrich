"""Text encoder for code128 barcode encoder"""

from __future__ import annotations

from typing import Literal

from . import encoding
from .data import _FNC4, Code128Data, Code128Marker

Charset = Literal["A", "B", "C"]

START_A, START_B, START_C = 103, 104, 105
TO_C, TO_B, TO_A = 99, 100, 101

_DIGIT_0, _DIGIT_9 = 0x30, 0x39

start_codes: dict[Charset, int] = {"A": START_A, "B": START_B, "C": START_C}
switch_codes: dict[Charset, int] = {"A": TO_A, "B": TO_B, "C": TO_C}
to_values: dict[int, int] = {TO_A: START_A, TO_B: START_B, TO_C: START_C}


def _is_digit(cp: int) -> bool:
    return _DIGIT_0 <= cp <= _DIGIT_9


class TextEncoder:
    """Class which encodes a raw text string into a list of
    character codes.
    Adds in character set switch codes, and compresses pairs of
    digits under character set C"""

    current_charset: Charset
    digits: list[int]

    def __init__(self) -> None:
        self.current_charset = "B"
        self.digits = []

    def switch_charset(self, new_charset: Charset) -> list[int]:
        """Switch to ``new_charset`` and return the emitted codewords.

        Leaving charset C with a half-formed digit pair flushes the
        leftover digit in the new charset after the switch code — the
        half-pair would otherwise be stranded.
        """
        pending_digit: int | None = None
        if self.current_charset == "C" and new_charset != "C" and self.digits:
            pending_digit = self.digits[0]
            self.digits = []
        self.current_charset = new_charset
        codes = [switch_codes[new_charset]]
        if pending_digit is not None:
            codes.extend(self.convert_char(pending_digit))
        return codes

    def switch_charset_if_necessary(self, cp: int, lookahead: list[int]) -> list[int]:
        """Decide whether we want to switch charsets for the
        next character"""

        def upcoming_digits() -> bool:
            """Return true if there are more than three consecutive digits
            coming up"""
            num_digits = 0
            for c in lookahead:
                if _is_digit(c):
                    num_digits += 1
                else:
                    break
            return num_digits > 3

        # Latin-1 supplement chars (cp >= 0x80) emit FNC4 + the ASCII
        # counterpart in convert_char; route the switch by where that
        # counterpart lives. The C1 controls 0x80-0x9F land in 0x00-0x1F,
        # which is charset A only.
        lookup_cp = cp - 0x80 if cp >= 0x80 else cp
        codes: list[int] = []
        if self.current_charset == "C" and not _is_digit(cp):
            target: Charset = "B" if lookup_cp in encoding.charset_b else "A"
            codes = self.switch_charset(target)

        elif self.current_charset == "B":
            if upcoming_digits():
                codes = self.switch_charset("C")
            elif lookup_cp not in encoding.charset_b:
                codes = self.switch_charset("A")

        elif self.current_charset == "A":
            if upcoming_digits():
                codes = self.switch_charset("C")
            elif lookup_cp not in encoding.charset_a:
                codes = self.switch_charset("B")

        return codes

    def convert_char(self, cp: int) -> list[int]:
        """Convert the given codepoint into codewords in the current charset.

        For A and B this is a simple table lookup. Latin-1 supplement
        codepoints emit an FNC4 single-shift followed by their ASCII
        counterpart (Code128Data rejects non-ASCII chars in ASCII mode
        at construction, so they're only seen with iso-8859-1). In C the
        caller has switched out for any non-digit, so the codepoint is an
        ASCII digit and consecutive digits are packed in pairs.
        """

        if cp >= 0x80:
            assert self.current_charset != "C"
            table = encoding.charset_a if self.current_charset == "A" else encoding.charset_b
            return [_FNC4.codeword_for_charset(self.current_charset), table[cp - 0x80]]

        if self.current_charset == "A":
            return [encoding.charset_a[cp]]

        if self.current_charset == "B":
            return [encoding.charset_b[cp]]

        # charset C — caller guarantees an ASCII digit
        self.digits.append(cp)
        if len(self.digits) == 2:
            ret = (self.digits[0] - _DIGIT_0) * 10 + (self.digits[1] - _DIGIT_0)
            self.digits = []
            return [ret]
        return []

    @staticmethod
    def optimize_encoding(enc: list[int]) -> None:
        """Perform various optimizations on the encoded string"""

        # [START_X, TO_Y]  => [START_Y,]
        # (This is only relevant at the start)
        # Saves one character
        if enc[1] in to_values:
            enc[0:2] = [to_values[enc[1]]]
        # [START_X, FNC1, TO_Y]  => [START_Y, FNC1, ]
        elif enc[1] == 102 and enc[2] in to_values:
            enc[0:3] = [to_values[enc[2]], 102]

    def encode(self, text: Code128Data) -> list[int]:
        """Encode the given data, optimize it and return a list of
        character codes.

        :param text: A :class:`Code128Data` whose segments interleave
            ``str`` chunks with :class:`Code128Marker` tokens. When the
            data's encoding is ``"iso-8859-1"`` each char in the Latin-1
            supplement range expands inline to an FNC4 single-shift
            followed by its ASCII counterpart.
        """

        encoded_text: list[int] = [start_codes[self.current_charset]]

        cp_stream = _flatten_segments(text)

        for i, item in enumerate(cp_stream):
            if isinstance(item, Code128Marker):
                encoded_text.extend(self._encode_marker(item))
                continue
            # Lookahead drives digit-run detection; markers don't
            # participate in digit packing so they're filtered out.
            lookahead = [cp for cp in cp_stream[i : i + 10] if isinstance(cp, int)]
            encoded_text.extend(self.switch_charset_if_necessary(item, lookahead))
            encoded_text.extend(self.convert_char(item))

        # End-of-stream: spill any leftover single digit from charset C
        # (switch_charset flushes it as part of the C→B transition).
        if self.digits:
            encoded_text.extend(self.switch_charset("B"))

        self.optimize_encoding(encoded_text)
        return encoded_text

    def _encode_marker(self, marker: Code128Marker) -> list[int]:
        """Emit a marker codeword, leaving charset C first if there's a
        pending leftover digit or the marker isn't representable in C.
        switch_charset() handles the leftover flush.
        """
        codes: list[int] = []
        if self.current_charset == "C" and (self.digits or not marker.representable_in("C")):
            codes.extend(self.switch_charset(marker.representable_charsets()[0]))
        codes.append(marker.codeword_for_charset(self.current_charset))
        return codes

    @staticmethod
    def get_bars(encoded_text: list[int], checksum: int) -> str:
        """Return the bar encoding (a string of ones and zeroes)
        representing the given encoded text and checksum digit.
        Stop code and termination bars are added onto the end"""

        full_code = [*encoded_text, checksum]
        bars = "".join(encoding.encodings[char] for char in full_code)

        bars += encoding.STOP
        bars += "11"

        return bars


def _flatten_segments(data: Code128Data) -> list[int | Code128Marker]:
    """Flatten Code128Data segments into a stream of codepoints. Marker
    tokens pass through unchanged.
    """
    out: list[int | Code128Marker] = []
    for seg in data.segments:
        if isinstance(seg, Code128Marker):
            out.append(seg)
        else:
            out.extend(map(ord, seg))
    return out
