"""EAN-13 barcode encoder

All needed by the user is done via the EAN13Encoder class:

>>> encoder = EAN13Encoder("012345678901")
>>> encoder.save("test.png")

Implemented by Helen Taylor for HUDORA GmbH.
Updated and ported to Python 3 by Michael Mulqueen for Method B Ltd.

Detailed documentation on the format here:
http://www.barcodeisland.com/ean13.phtml

You may use this under a BSD License.
"""

from __future__ import annotations

import os
from functools import reduce
from typing import TYPE_CHECKING

from . import encoding
from .renderer import EAN13Renderer, EAN13RenderOptions
from pystrich.exceptions import PyStrichInvalidInput

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


GUARDS = ("101", "01010", "101")


class EAN13Encoder:
    """Encode a 12- or 13-digit code as an EAN-13 1D barcode.

    The check digit is computed for you. If a 13-digit code is supplied, its
    final digit is discarded and recomputed.

    Typical use::

        encoder = EAN13Encoder("012345678901")
        encoder.save("ean13.png")

    :ivar code: The 12-digit input (number system + manufacturer + product).
    :ivar check_digit: The computed mod-10 check digit.
    :ivar full_code: The 13-digit code including check digit.
    :ivar left_bars: Bar pattern for the left half of the symbol.
    :ivar right_bars: Bar pattern for the right half.
    :ivar options: Render-time options dict (empty if none were supplied).
    :ivar width: Pixel width of the most recently rendered image.
    :ivar height: Pixel height of the most recently rendered image.
    """

    code: str
    check_digit: int
    full_code: str
    left_bars: str
    right_bars: str
    options: EAN13RenderOptions
    width: int
    height: int

    def __init__(
        self,
        code: str,
        options: EAN13RenderOptions | None = None,
    ) -> None:
        """Validate ``code`` and compute its check digit.

        :param code: A string of 12 digits in the form ``nnmmmmmppppp``,
            where ``n`` is the number system, ``m`` is the manufacturer code
            and ``p`` is the product code. A 13-digit code is also accepted;
            its final digit is treated as a check digit and recomputed.
        :param options: Optional dict tweaking the rendered output. See
            :class:`pystrich.ean13.EAN13RenderOptions` for accepted keys.
        :raises pystrich.exceptions.PyStrichInvalidInput: if ``code`` is not
            exactly 12 (or 13) digits.
        """

        # Normalise to 12 digits: a 13-digit input has its trailing check
        # digit dropped (we recompute it below).
        if len(code) == 13:
            code = code[:-1]
        if code.isdigit() and len(code) == 12:
            self.code = code
            self.check_digit = self.calculate_check_digit()
            self.full_code = self.code + str(self.check_digit)
            self.left_bars = ""
            self.right_bars = ""
            self.options = options or {}
            self.height = 0
            self.width = 0
            self.encode()
        else:
            raise PyStrichInvalidInput("code must be 12 or 13 digits long")

    def encode(self) -> tuple[str, str]:
        """Encode the barcode number and return the left and right
        data strings"""

        parity_values = self.get_parity()

        self.left_bars = ""
        self.right_bars = ""

        # Exclude the first number system digit, this was
        # for determining the left parity
        for parity, digit in zip(parity_values, self.full_code[1:7]):
            self.left_bars += encoding.get_left_encoded(int(digit), parity)
        for digit in self.full_code[7:]:
            self.right_bars += encoding.get_right_encoded(int(digit))

        return self.left_bars, self.right_bars

    def get_parity(self) -> tuple[int, int, int, int, int, int]:
        """Return the parity mappings applicable to this code"""
        return encoding.parity_table[int(self.code[0])]

    def calculate_check_digit(self) -> int:
        """Compute the EAN-13 mod-10 check digit for :attr:`code`.

        Working right-to-left across the 12-digit input, odd-positioned
        digits are weighted by 3 and even-positioned digits by 1; the check
        digit is the value that brings the weighted sum to a multiple of 10.
        """

        def sum_str(total, digit):
            """add a stringified digit to the total sum"""
            return total + int(digit)

        # sum the "odd" digits (1,3,5,7,9,11) and multiply by 3
        oddsum = reduce(sum_str, self.code[1::2], 0)

        # sum the "even" digits (0,2,4,6,8,10)
        evensum = reduce(sum_str, self.code[:12:2], 0)

        # add them up
        total = oddsum * 3 + evensum

        # check digit is the number that can be added to the total
        # to get to a multiple of 10
        return (10 - (total % 10)) % 10

    def get_imagedata(self, bar_width: int = 3) -> bytes:
        """Render the barcode and return PNG bytes.

        :param bar_width: Width in pixels of the narrowest bar.
        :returns: PNG-encoded image data.
        :rtype: bytes
        """
        barcode = EAN13Renderer(
            self.full_code, self.left_bars, self.right_bars, GUARDS,
            self.options)
        imagedata = barcode.get_imagedata(bar_width)
        self.height = barcode.height
        self.width = barcode.width
        return imagedata

    def get_pilimage(self, bar_width: int = 3) -> PILImage:
        """Render the barcode and return a Pillow image.

        :param bar_width: Width in pixels of the narrowest bar.
        :returns: The rendered barcode.
        :rtype: PIL.Image.Image

        .. versionadded:: 0.11
        """
        barcode = EAN13Renderer(
            self.full_code, self.left_bars, self.right_bars, GUARDS,
            self.options)
        img = barcode.get_pilimage(bar_width)
        self.height = barcode.height
        self.width = barcode.width
        return img

    def save(self, filename: str | os.PathLike[str], bar_width: int = 3) -> None:
        """Render the barcode to a PNG file.

        :param filename: Path to write the PNG to.
        :param bar_width: Width in pixels of the narrowest bar.
        """
        EAN13Renderer(self.full_code,
                      self.left_bars,
                      self.right_bars,
                      GUARDS,
                      self.options).write_file(filename, bar_width)
