"""Rendering code for EAN-13 barcode"""

from __future__ import annotations

import os
from functools import reduce
from io import BytesIO
from typing import TYPE_CHECKING, TypedDict

from PIL import Image, ImageFont, ImageDraw

from pystrich.fonts import get_font

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage
# maps bar width against font size
font_sizes = {
    1: 8,
    2: 14,
    3: 18,
    4: 24
}


class EAN13RenderOptions(TypedDict, total=False):
    """Optional render-time tweaks for EAN-13 barcodes.

    The label layout in EAN-13 is fixed by the standard, so this is a small
    set of cosmetic toggles. All keys are optional; omitted keys fall back
    to library defaults.

    .. versionadded:: 0.11
    """

    first_digit_y_offset: float
    """How far above the other text the first digit sits, as a fraction of
    image height. Defaults to ``0.1`` (the long-standing pyStrich look,
    where the leading number-system digit sits slightly higher than the two
    main digit groups). Set to ``0`` for a level baseline across all three
    groups."""


class EAN13Renderer:
    """Rendering class - given the code and corresponding
    bar encodings and guard bars,
    it will add edge zones and render to an image"""

    width: int
    height: int
    code: str
    left_bars: str
    right_bars: str
    guards: tuple[str, str, str]
    options: EAN13RenderOptions

    def __init__(
        self,
        code: str,
        left_bars: str,
        right_bars: str,
        guards: tuple[str, str, str],
        options: EAN13RenderOptions | None = None,
    ) -> None:
        self.code = code
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.guards = guards
        self.options = options or {}
        self.width = 0
        self.height = 0

    def get_pilimage(self, bar_width: int) -> PILImage:
        def sum_len(total: int, item: str) -> int:
            """add the length of a given item to the total"""
            return total + len(item)

        num_bars = (7 * 12) + reduce(sum_len, self.guards, 0)

        # GS1 mandates an asymmetric quiet zone: 11 modules on the left,
        # 7 on the right. Anything narrower on the left risks rejection by
        # retail scanners.
        left_quiet = bar_width * 11
        right_quiet = bar_width * 7
        image_width = left_quiet + right_quiet + (num_bars * bar_width)
        image_height = image_width // 2

        img = Image.new('L', (image_width, image_height), 255)

        class BarWriter:
            """Class which moves across the image, writing out bars"""
            def __init__(self, img):
                self.img = img
                self.current_x = left_quiet
                self.symbol_top = (left_quiet + right_quiet) // 4

            def write_bar(self, value, full=False):
                """Draw a bar at the current position,
                if the value is 1, otherwise move on silently"""

                # only write anything to the image if bar value is 1
                bar_height = int(image_height * (full and 0.9 or 0.8))
                if value == 1:
                    for ypos in range(self.symbol_top, bar_height):
                        for xpos in range(self.current_x,
                                          self.current_x + bar_width):
                            img.putpixel((xpos, ypos), 0)
                self.current_x += bar_width

            def write_bars(self, bars, full=False):
                """write all bars to the image"""
                for bar in bars:
                    self.write_bar(int(bar), full)

        # Draw the bars
        writer = BarWriter(img)
        writer.write_bars(self.guards[0], full=True)
        writer.write_bars(self.left_bars)
        writer.write_bars(self.guards[1], full=True)
        writer.write_bars(self.right_bars)
        writer.write_bars(self.guards[2], full=True)

        # Draw the text
        font_size = font_sizes.get(bar_width, 24)

        font = get_font("courR", font_size)
        draw = ImageDraw.Draw(img)
        text_y = 0.8
        first_digit_y = text_y - self.options.get("first_digit_y_offset", 0.1)
        draw.text((1 * bar_width, int(image_height * first_digit_y)),
                  self.code[0], font=font)
        draw.text((left_quiet + 7 * bar_width, int(image_height * text_y)),
                  self.code[1:7], font=font)
        draw.text((left_quiet + 54 * bar_width, int(image_height * text_y)),
                  self.code[7:], font=font)
        self.width = image_width
        self.height = image_height
        return img

    def write_file(self, filename: str | os.PathLike[str], bar_width: int) -> None:
        """Write barcode data out to image file
        filename - the name of the image file
        bar_width - the desired width of each bar"""
        img = self.get_pilimage(bar_width)
        img.save(filename, "PNG")

    def get_imagedata(self, bar_width: int) -> bytes:
        """Write the matrix out as PNG to a bytestream"""
        buffer = BytesIO()
        img = self.get_pilimage(bar_width)
        img.save(buffer, "PNG")
        return buffer.getvalue()
