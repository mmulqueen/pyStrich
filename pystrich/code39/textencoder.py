"""Text encoder for code39 barcode encoder"""

from __future__ import annotations

from pystrich.exceptions import PyStrichInvalidInput

from . import encoding


class CharacterNotAllowedInCode39(PyStrichInvalidInput):
    pass


class TextEncoder:
    """Class which encodes a raw text string into a list of
    character codes."""

    def encode(self, text: str, full_ascii: bool) -> list[str]:
        """Encode the given text and return a
        list of character codes"""

        encoded_text: list[str] = []

        # First symbol is always the start code
        encoded_text.append("*")

        # MIL-STD-1189 defines a full ASCII encoding, but permits its use only in closed-loop
        # applications (i.e. where the whole system is controlled by one authority). Otherwise
        # we are limited to a smaller subset.
        if full_ascii:
            try:
                ascii_bytes = text.encode("ascii")
            except UnicodeEncodeError as exc:
                raise PyStrichInvalidInput(
                    f"Code 39 full-ASCII mode requires ASCII input; got non-ASCII "
                    f"character {exc.object[exc.start]!r} at index {exc.start}"
                ) from exc
            for byte in ascii_bytes:
                encoded_text.extend(encoding.ascii_to_code39[byte])
        else:
            allowed_chars = encoding.code39_encodings.keys()
            for char in text:
                if char not in allowed_chars:
                    raise CharacterNotAllowedInCode39(
                        f"{char} is not allowed in code 39 unless you've enabled full ASCII "
                        f"mode (not suitable for all software/hardware). You may use "
                        f"{''.join(allowed_chars)}"
                    )
                encoded_text.append(char)

        # Last symbol is always the stop code
        encoded_text.append("*")

        return encoded_text

    @staticmethod
    def get_bars(encoded_text: list[str]) -> str:
        """Return the bar encoding (a string of ones and zeroes)
        representing the given encoded text."""

        bars = [encoding.code39_encodings[char] for char in encoded_text]

        # Join the characters, leaving a wide gap between
        return "0".join(bars)
