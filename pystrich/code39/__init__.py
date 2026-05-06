"""Code-39 barcode encoder

All needed by the user is done via the Code39Encoder class:

>>> encoder = Code39Encoder("MIL-STD-1189")
>>> encoder.save("test.png")

You may use this under a BSD License.
"""
from .textencoder import TextEncoder
from .renderer import Code39Renderer
import logging

log = logging.getLogger("code39")


class Code39Encoder:
    """Encode a string as a Code 39 1D barcode.

    By default only the standard Code 39 character set is accepted
    (``0-9``, ``A-Z``, space, and ``-.$/+%``). Pass ``full_ascii=True`` to
    use the Full ASCII extension, which encodes any 7-bit character via
    paired symbols.

    Typical use::

        encoder = Code39Encoder("ABC-123")
        encoder.save("barcode.png")

    :ivar text: The original input text.
    :ivar encoded_text: List of code values produced by the text encoder.
    :ivar bars: The bar/space pattern as a string of ``"1"`` and ``"0"``.
    :ivar options: The options dict passed to ``__init__``, or ``None``.
    :ivar width: Pixel width of the most recently rendered image.
    :ivar height: Pixel height of the most recently rendered image.
    """

    def __init__(self, text, full_ascii=False, options=None):
        """Encode ``text`` as Code 39.

        :param text: The data to encode.
        :param full_ascii: If ``True``, use the Full ASCII extension so any
            7-bit character can be represented (each non-standard character
            becomes a pair of symbols).
        :param options: Optional dict tweaking the rendered output. Supported
            keys:

            * ``ttf_font`` -- absolute path to a TrueType font for the label.
              Defaults to a bundled bitmap font.
            * ``ttf_fontsize`` -- font size in points.
            * ``show_label`` -- whether to render the human-readable label
              underneath the bars (defaults to ``True``).
            * ``height`` -- total image height in pixels (defaults to ``120``).
            * ``label_border`` -- pixels of space between barcode and label.
            * ``bottom_border`` -- pixels of space between label and the
              bottom edge.
        """

        self.options = options
        self.text = text
        self.height = 0
        self.width = 0
        encoder = TextEncoder()

        self.encoded_text = encoder.encode(self.text, full_ascii)
        log.debug("Encoded text is %s", self.encoded_text)

        self.bars = encoder.get_bars(self.encoded_text)
        log.debug("Bars: %s", self.bars)

    def get_imagedata(self, bar_width=3):
        """Render the barcode and return PNG bytes.

        :param bar_width: Width in pixels of the narrowest bar.
        :returns: PNG-encoded image data.
        :rtype: bytes
        """
        barcode = Code39Renderer(self.bars, self.text, self.options)
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
        barcode = Code39Renderer(self.bars, self.text, self.options)
        img = barcode.get_pilimage(bar_width)
        self.width = barcode.image_width
        self.height = barcode.image_height
        return img

    def save(self, filename, bar_width=3):
        """Render the barcode to a PNG file.

        :param filename: Path to write the PNG to.
        :param bar_width: Width in pixels of the narrowest bar.
        """
        Code39Renderer(
            self.bars, self.text, self.options).write_file(filename, bar_width)
