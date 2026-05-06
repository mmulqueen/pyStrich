"""Code-128 barcode encoder

All needed by the user is done via the Code128Encoder class:

>>> encoder = Code128Encoder("HuDoRa")
>>> encoder.save("test.png")

Implemented by Helen Taylor for HUDORA GmbH.
Updated and ported to Python 3 by Michael Mulqueen for Method B Ltd.

Detailed documentation on the format here:
http://www.barcodeisland.com/code128.phtml
http://www.adams1.com/pub/russadam/128code.html

You may use this under a BSD License.
"""
from .textencoder import TextEncoder
from .renderer import Code128Renderer
import logging

log = logging.getLogger("code128")


class Code128Encoder:
    """Encode a string as a Code 128 1D barcode.

    Code sets A, B and C are switched between automatically to minimise symbol
    length. The mod-103 checksum is computed and appended for you.

    Typical use::

        encoder = Code128Encoder("ABC-12345")
        encoder.save("barcode.png")

    :ivar text: The original input text.
    :ivar encoded_text: List of code values produced by the text encoder,
        including start codes and code-set switches.
    :ivar checksum: The mod-103 checksum value.
    :ivar bars: The bar/space pattern as a string of ``"1"`` and ``"0"``.
    :ivar options: The options dict passed to ``__init__``, or ``None``.
    :ivar width: Pixel width of the most recently rendered image. ``0`` until a
        render method has been called.
    :ivar height: Pixel height of the most recently rendered image.
    """

    def __init__(self, text, options=None):
        """Encode ``text`` as Code 128 and compute the checksum.

        :param text: The data to encode. Any character in the Code 128 set
            (ASCII 0-127, plus the FNC controls via the dedicated text
            encoder) is permitted.
        :param options: Optional dict tweaking the rendered output. Supported
            keys:

            * ``ttf_font`` -- absolute path to a TrueType font for the label.
              Defaults to a bundled bitmap font.
            * ``ttf_fontsize`` -- font size in points.
            * ``show_label`` -- whether to render the human-readable label
              underneath the bars (defaults to ``True``).
            * ``height`` -- total image height in pixels (defaults to a third
              of the image width).
            * ``label_border`` -- pixels of space between barcode and label.
            * ``bottom_border`` -- pixels of space between label and the
              bottom edge.
        """

        self.options = options
        self.text = text
        self.height = 0
        self.width = 0
        encoder = TextEncoder()

        self.encoded_text = encoder.encode(self.text)
        log.debug("Encoded text is %s", self.encoded_text)

        self.checksum = self.calculate_check_sum()
        log.debug("Checksum is %d", self.checksum)

        self.bars = encoder.get_bars(self.encoded_text, self.checksum)
        log.debug("Bars: %s", self.bars)

    def calculate_check_sum(self):
        """Compute the Code 128 mod-103 checksum for :attr:`encoded_text`.

        The start code contributes with weight 1; subsequent symbols are
        weighted by their 1-based position before the modulo is taken.
        """

        checksum = self.encoded_text[0]

        for index, char in enumerate(self.encoded_text):
            if index > 0:
                checksum += (index * char)

        return checksum % 103

    def get_imagedata(self, bar_width=3):
        """Render the barcode and return PNG bytes.

        :param bar_width: Width in pixels of the narrowest bar.
        :returns: PNG-encoded image data.
        :rtype: bytes
        """

        barcode = Code128Renderer(self.bars, self.text, self.options)
        imagedata = barcode.get_imagedata(bar_width)
        self.width = barcode.image_width
        self.height = barcode.image_height
        return imagedata

    def get_pilimage(self, bar_width=3):
        """Render the barcode and return a Pillow image.

        :param bar_width: Width in pixels of the narrowest bar.
        :returns: The rendered barcode.
        :rtype: PIL.Image.Image

        .. versionadded:: 0.11
        """
        barcode = Code128Renderer(self.bars, self.text, self.options)
        img = barcode.get_pilimage(bar_width)
        self.width = barcode.image_width
        self.height = barcode.image_height
        return img

    def save(self, filename, bar_width=3):
        """Render the barcode to a PNG file.

        :param filename: Path to write the PNG to.
        :param bar_width: Width in pixels of the narrowest bar.
        """
        Code128Renderer(
            self.bars, self.text, self.options).write_file(filename, bar_width)
