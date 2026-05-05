"""Text encoder for code39 barcode encoder"""

import logging
import string
log = logging.getLogger("code39")

from . import encoding
from pystrich.exceptions import PyStrichInvalidInput

class CharacterNotAllowedInCode39(PyStrichInvalidInput):
    pass

class TextEncoder:
    """Class which encodes a raw text string into a list of
    character codes.
    Adds in character set switch codes, and compresses pairs of
    digits under character set C"""

    def __init__(self):
        self.digits = ""

    def encode(self, text, full_ascii):
        """Encode the given text and return a
        list of character codes"""

        encoded_text = list()

        # First symbol is always the start code
        encoded_text.append("*")

        # MIL-STD-1189 defines a full ASCII encoding, but permits its use only in closed loop applications (i.e.
        # where the whole system is controlled by one authority). Otherwise we are limited to a smaller subset.
        if full_ascii:
            # Ensure the text can be encoded into ASCII first
            ascii_text = text.encode("ascii")
            # Convert to Code 39 encodings. This is only for use in closed-loop applications
            for char in ascii_text:
                encoded_text.extend(encoding.ascii_ord_to_code39[char])
        else:
            allowed_chars = encoding.code39_encodings.keys()
            for char in text:
                if char not in allowed_chars:
                    raise CharacterNotAllowedInCode39("{} is not allowed in code 39 unless you've enabled full "
                                                      "ASCII mode (not suitable for all software/hardware). You may "
                                                      "use {}".format(char, "".join(allowed_chars)))
                encoded_text.append(char)


        # Last symbol is always the stop code
        encoded_text.append("*")

        return encoded_text

    @staticmethod
    def get_bars(encoded_text):
        """Return the bar encoding (a string of ones and zeroes)
        representing the given encoded text."""

        bars = []
        for char in encoded_text:
            bars.append(encoding.code39_encodings[char])

        # Join the characters, leaving a wide gap between
        return "0".join(bars)
