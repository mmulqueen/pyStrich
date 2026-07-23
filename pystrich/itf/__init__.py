"""Interleaved 2 of 5 and ITF-14 barcode encoders.

Interleaved 2 of 5 (ITF) encodes an even number of digits compactly. ITF-14
is the GS1 application of it: a fixed 14-digit GTIN-14 (13 data digits plus a
mod-10 check digit) printed inside a bearer bar.

>>> encoder = ITF14Encoder("1540141453698")
>>> encoder.save("itf14.png")
"""

from __future__ import annotations

from pystrich.bar_encoder import Bar1DEncoder
from pystrich.exceptions import (
    PyStrichInvalidCheckDigit,
    PyStrichInvalidInput,
    PyStrichInvalidPayloadLength,
)
from pystrich.limits import check_input_length

from . import encoding
from .renderer import ITFRenderer, ITFRenderOptions

# ITF-14 is conventionally framed by a bearer bar; the encoder applies this
# default unless the caller overrides ``bearer_width``.
DEFAULT_ITF14_BEARER_MODULES = 4


class ITFEncoder(Bar1DEncoder):
    """Encode an even-length string of digits as an Interleaved 2 of 5 barcode.

    Typical use::

        encoder = ITFEncoder("1234567890")
        encoder.save("itf.png")

    :ivar digits: The digits being encoded.
    :ivar bars: The bar/space pattern as a string of ``"1"`` and ``"0"``.
    :ivar options: Render-time options dict (empty if none were supplied).
    :ivar width: Pixel width of the most recently rendered image.
    :ivar height: Pixel height of the most recently rendered image.
    """

    options: ITFRenderOptions
    digits: str
    bars: str

    def __init__(
        self,
        digits: str,
        options: ITFRenderOptions | None = None,
    ) -> None:
        """Validate ``digits`` and build the bar pattern.

        :param digits: An even-length string of digits.
        :param options: Optional dict tweaking the rendered output. See
            :class:`pystrich.itf.ITFRenderOptions` for accepted keys.
        :raises pystrich.exceptions.PyStrichInvalidInput: if ``digits`` is not
            an even-length run of digits.
        """
        check_input_length(len(digits), self._MAX_PAYLOAD_LENGTH)
        super().__init__(options)
        if not digits.isdigit() or len(digits) % 2 != 0 or len(digits) == 0:
            raise PyStrichInvalidInput("digits must be a non-empty even-length run of digits")
        self.digits = digits
        self.bars = encoding.encode_digits(digits)

    def init_renderer(self) -> ITFRenderer:
        """Construct an :class:`ITFRenderer` for the encoded bars."""
        return ITFRenderer(self.digits, self.bars, self.options)


class ITF14Encoder(ITFEncoder):
    """Encode a 13- or 14-digit code as an ITF-14 (GTIN-14) barcode.

    The check digit is computed for you. If a 14-digit code is supplied, its
    final digit is discarded and recomputed. The symbol is framed by a bearer
    bar unless ``bearer_width`` is overridden in ``options``.

    Typical use::

        encoder = ITF14Encoder("1540141453698")
        encoder.save("itf14.png")

    :ivar check_digit: The computed mod-10 check digit.
    :ivar full_code: The 14-digit code including check digit (== ``digits``).
    """

    # A 13-digit GTIN-14 body plus its optional check digit.
    _MAX_PAYLOAD_LENGTH = 14

    check_digit: int
    full_code: str

    def __init__(
        self,
        code: str,
        options: ITFRenderOptions | None = None,
        *,
        require_valid_check_digit: bool = False,
    ) -> None:
        """Validate ``code`` and compute its check digit.

        :param code: A string of 13 digits (the GTIN-14 without its check
            digit). A 14-digit code is also accepted; its final digit is
            treated as a check digit and recomputed.
        :param options: Optional dict tweaking the rendered output. See
            :class:`pystrich.itf.ITFRenderOptions` for accepted keys.
        :param require_valid_check_digit: If ``True``, a check digit must be
            supplied (a 14-digit ``code``) and must match the computed one.
        :raises pystrich.exceptions.PyStrichInvalidPayloadLength: if ``code`` is
            not exactly 13 (or 14) digits.
        :raises pystrich.exceptions.PyStrichInvalidCheckDigit: if
            ``require_valid_check_digit`` is set and the supplied check digit is
            missing or wrong.
        """
        # ITF-14 hands ``full_code`` to super(), so guard the raw input here.
        check_input_length(len(code), self._MAX_PAYLOAD_LENGTH)
        # Normalise to 13 data digits: a 14-digit input has its trailing check
        # digit dropped (we recompute it below).
        supplied_check_digit = code[-1] if len(code) == 14 else None
        if len(code) == 14:
            code = code[:-1]
        if not (code.isdigit() and len(code) == 13):
            raise PyStrichInvalidPayloadLength("code must be 13 or 14 digits long")
        self.check_digit = self.calculate_check_digit(code)
        if require_valid_check_digit:
            if supplied_check_digit is None:
                raise PyStrichInvalidCheckDigit(
                    "require_valid_check_digit is set but no check digit was supplied; "
                    "pass all 14 digits including the check digit"
                )
            if supplied_check_digit != str(self.check_digit):
                raise PyStrichInvalidCheckDigit(
                    f"supplied check digit {supplied_check_digit} is incorrect; "
                    f"expected {self.check_digit}"
                )
        self.full_code = code + str(self.check_digit)
        super().__init__(self.full_code, options)

    @staticmethod
    def calculate_check_digit(code: str) -> int:
        """Compute the GTIN-14 mod-10 check digit for the 13 data digits.

        Working right-to-left, the digits are weighted 3, 1, 3, 1, …; the
        check digit brings the weighted sum up to a multiple of 10.
        """
        total = sum(int(digit) * (3 if i % 2 == 0 else 1) for i, digit in enumerate(reversed(code)))
        return (10 - (total % 10)) % 10

    def init_renderer(self) -> ITFRenderer:
        """Construct an :class:`ITFRenderer`, defaulting the bearer bar on."""
        options = self.options.copy()
        options.setdefault("bearer_width", DEFAULT_ITF14_BEARER_MODULES)
        return ITFRenderer(self.digits, self.bars, options)
