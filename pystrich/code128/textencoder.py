"""Text encoder for code128 barcode encoder"""

from __future__ import annotations

from typing import Literal

from pystrich.exceptions import PyStrichInvalidInput

from . import encoding

Charset = Literal["A", "B", "C"]

START_A, START_B, START_C = 103, 104, 105
TO_C, TO_B, TO_A = 99, 100, 101

start_codes: dict[Charset, int] = {"A": START_A, "B": START_B, "C": START_C}

to_values: dict[int, int] = {TO_A: START_A, TO_B: START_B, TO_C: START_C}

_TO_CODES: dict[Charset, str] = {"A": "TO_A", "B": "TO_B", "C": "TO_C"}


class TextEncoder:
    """Class which encodes a raw text string into a list of
    character codes.
    Adds in character set switch codes, and compresses pairs of
    digits under character set C"""

    current_charset: Charset
    digits: str

    def __init__(self) -> None:
        self.current_charset = "B"
        self.digits = ""

    def switch_charset(self, new_charset: Charset) -> list[int]:
        """Switch to a new character set
        Return a single item list containing the switch code"""

        switch_code = self.convert_char(_TO_CODES[new_charset])
        # TO_A/TO_B/TO_C are always direct table lookups, never the digit buffer.
        assert switch_code is not None
        self.current_charset = new_charset
        return [switch_code]

    def switch_charset_if_necessary(self, char: str, lookahead: str) -> list[int]:
        """Decide whether we want to switch charsets for the
        next character"""

        def upcoming_digits() -> bool:
            """Return true if there are more than three consecutive digits
            coming up"""
            num_digits = 0
            for c in lookahead:
                if c.isdigit():
                    num_digits += 1
                else:
                    break
            return num_digits > 3

        codes: list[int] = []
        if self.current_charset == "C" and not char.isdigit():
            # Switch from C - the next char is not a digit

            # by default, switch to B
            if char in encoding.charset_b:
                codes = self.switch_charset("B")
            # but if the character's not in B, switch to A
            elif char in encoding.charset_a:
                codes = self.switch_charset("A")
            else:
                raise PyStrichInvalidInput(
                    f"Character {char!r} (U+{ord(char):04X}) cannot be encoded in Code 128"
                )

            # Take care of the odd leftover digit if there is one
            if len(self.digits) == 1:
                leftover = self.convert_char(self.digits[0])
                assert leftover is not None
                codes.append(leftover)
                self.digits = ""

        elif self.current_charset == "B":
            # Do we want to switch from B?

            # Lookahead - are there lots of digits coming up?
            # If so, switch to C
            if upcoming_digits():
                codes = self.switch_charset("C")
            # If B can't handle the next char, switch to A
            elif char not in encoding.charset_b:
                if char in encoding.charset_a:
                    codes = self.switch_charset("A")
                else:
                    raise PyStrichInvalidInput(
                        f"Character {char!r} (U+{ord(char):04X}) cannot be encoded in Code 128"
                    )

        elif self.current_charset == "A":
            # Do we want to switch from A?

            # Lookahead - are there lots of digits coming up?
            # If so, switch to C
            if upcoming_digits():
                codes = self.switch_charset("C")
            # If A can't handle the next char, switch to B
            elif char not in encoding.charset_a:
                if char in encoding.charset_b:
                    codes = self.switch_charset("B")
                else:
                    raise PyStrichInvalidInput(
                        f"Character {char!r} (U+{ord(char):04X}) cannot be encoded in Code 128"
                    )

        return codes

    def convert_char(self, char: str) -> int | None:
        """Convert the given character into the current charset
        For A and B and a few cases in C, this is a simple lookup in
        the charset table.
        For most cases in C, this involves grouping consecutive digits
        into pairs and adding in each pair as a single character"""

        if self.current_charset == "A":
            return encoding.charset_a[char]

        if self.current_charset == "B":
            return encoding.charset_b[char]

        # charset C
        if char in encoding.charset_c:
            return encoding.charset_c[char]
        if char.isdigit():
            self.digits += char
            if len(self.digits) == 2:
                ret = int(self.digits)
                self.digits = ""
                return ret
            return None
        raise PyStrichInvalidInput(f"Character {char!r} cannot be encoded in Code 128 charset C")

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

    def encode(self, text: str) -> list[int]:
        """Encode the given text, optimize it and return a
        list of character codes"""

        encoded_text: list[int] = []

        # First symbol is always the start code for the initial charset
        encoded_text.append(start_codes[self.current_charset])

        # Start with charset B
        for i, char in enumerate(text):
            encoded_text.extend(self.switch_charset_if_necessary(char, text[i : i + 10]))
            converted = self.convert_char(char)
            if converted is not None:
                encoded_text.append(converted)

        # Finale Take care of the odd leftover digit if there is
        # one from encoding Charset C
        if len(self.digits) == 1:
            # We now force Charset B
            encoded_text.extend(self.switch_charset("B"))
            leftover = self.convert_char(self.digits[0])
            assert leftover is not None
            encoded_text.append(leftover)

        self.optimize_encoding(encoded_text)
        return encoded_text

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
