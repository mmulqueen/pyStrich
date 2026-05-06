"""Rendering code for EAN-13 barcode"""

from functools import reduce
from io import BytesIO

from PIL import Image, ImageFont, ImageDraw

from pystrich.fonts import get_font
# maps bar width against font size
font_sizes = {
    1: 8,
    2: 14,
    3: 18,
    4: 24
}


class EAN13Renderer:
    """Rendering class - given the code and corresponding
    bar encodings and guard bars,
    it will add edge zones and render to an image"""

    width = None
    height = None

    def __init__(self, code, left_bars, right_bars, guards):
        self.code = code
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.guards = guards

    def get_pilimage(self, bar_width):
        def sum_len(total, item):
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
        draw.text((1 * bar_width, int(image_height * 0.7)),
                  self.code[0], font=font)
        draw.text((left_quiet + 7 * bar_width, int(image_height * 0.8)),
                  self.code[1:7], font=font)
        draw.text((left_quiet + 54 * bar_width, int(image_height * 0.8)),
                  self.code[7:], font=font)
        self.width = image_width
        self.height = image_height
        return img

    def write_file(self, filename, bar_width):
        """Write barcode data out to image file
        filename - the name of the image file
        bar_width - the desired width of each bar"""
        img = self.get_pilimage(bar_width)
        img.save(filename, "PNG")

    def get_imagedata(self, bar_width):
        """Write the matrix out as PNG to a bytestream"""
        buffer = BytesIO()
        img = self.get_pilimage(bar_width)
        img.save(buffer, "PNG")
        return buffer.getvalue()
