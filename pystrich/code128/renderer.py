"""Rendering code for code128 barcode"""

from __future__ import annotations

import logging
import os
from io import BytesIO
from typing import TYPE_CHECKING

from PIL import Image, ImageFont, ImageDraw

from pystrich.fonts import get_font
from pystrich.types import BarcodeRenderOptions

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

log = logging.getLogger("code128")

# maps bar width against font size
FONT_SIZES = {
    1: 8,
    2: 14,
    3: 18,
    4: 24
}


class Code128Renderer:
    """Rendering class for code128 - given the bars and the original
    text, it will render an image of the barcode, including edge
    zones and text."""

    options: BarcodeRenderOptions
    bars: str
    text: str
    image_width: int
    image_height: int

    def __init__(
        self,
        bars: str,
        text: str,
        options: BarcodeRenderOptions | None = None,
    ) -> None:
        """See :class:`pystrich.types.BarcodeRenderOptions` for accepted keys."""
        self.options = options or {}
        self.bars = bars
        self.text = text
        self.image_width = 0
        self.image_height = 0

    def get_pilimage(self, bar_width: int) -> PILImage:
        """Return the barcode as a PIL object"""

        show_label = self.options.get('show_label', True)

        # 11 bars per character, plus the stop
        num_bars = len(self.bars)

        log.debug("There are %d bars", num_bars)

        # Quiet zone is 10 bar widths on each side
        quiet_width = bar_width * 10

        fontsize = 0
        if show_label:
            default_fontsize = FONT_SIZES.get(bar_width, 24)
            fontsize = self.options.get('ttf_fontsize', default_fontsize)
            ttf_font = self.options.get('ttf_font')
            if ttf_font:
                font = ImageFont.truetype(ttf_font, fontsize)
            else:
                font = get_font("courR", fontsize)

        # Total image width
        self.image_width = (2 * quiet_width) + (num_bars * bar_width)

        # Image height 30% of width
        label_border = self.options.get('label_border', 0)
        self.image_height = self.options.get('height') or (self.image_width // 3)
        bar_height = self.image_height - label_border - fontsize

        # Image: has a white background
        bottom_border = self.options.get('bottom_border', 0)
        img = Image.new('L', (
            self.image_width, self.image_height + bottom_border), 255)

        class BarWriter:
            """Class which moves across the image, writing out bars"""
            def __init__(self, img, bar_height):
                self.img = img
                self.current_x = quiet_width
                if show_label:
                    self.symbol_top = quiet_width // 2
                else:
                    self.symbol_top = 0
                self.bar_height = bar_height

            def write_bar(self, value):
                """Draw a bar at the current position,
                if the value is 1, otherwise move on silently"""

                # only write anything to the image if bar value is 1
                if value == 1:
                    for ypos in range(self.symbol_top, self.bar_height):
                        for xpos in range(self.current_x,
                                          self.current_x + bar_width):
                            img.putpixel((xpos, ypos), 0)
                self.current_x += bar_width

            def write_bars(self, bars):
                """write all bars to the image"""
                for bar in bars:
                    self.write_bar(int(bar))

        # draw the barcode bars themselves
        writer = BarWriter(img, bar_height)
        writer.write_bars(self.bars)

        # Draw the text
        draw = ImageDraw.Draw(img)
        if show_label:
            xtextwidth = font.getlength(self.text)
            xtextpos = self.image_width / 2 - (xtextwidth / 2)
            ytextpos = bar_height + label_border
            draw.text((xtextpos, ytextpos), self.text, font=font)
        return img

    def write_file(self, filename: str | os.PathLike[str], bar_width: int) -> None:
        """Write barcode data out to image file
        filename - the name of the image file or an file object
        bar_width - the desired width in pixels of each bar"""
        img = self.get_pilimage(bar_width)
        img.save(filename, 'PNG')

    def get_imagedata(self, bar_width: int) -> bytes:
        """Write the matrix out as PNG to an bytestream"""
        imagedata = BytesIO()
        img = self.get_pilimage(bar_width)
        img.save(imagedata, "PNG")
        return imagedata.getvalue()
