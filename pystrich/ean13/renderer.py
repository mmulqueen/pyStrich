"""Rendering code for EAN-13 barcode"""

from __future__ import annotations

from functools import reduce
from typing import TYPE_CHECKING, TypedDict

from PIL import Image, ImageDraw

from pystrich._vector_text import make_text_label
from pystrich.bar_renderer import Bar1DRenderer
from pystrich.fonts import get_font
from pystrich.marks import BarLayout, iter_bar_marks

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

# GS1 specifies an asymmetric quiet zone for EAN-13: 11 modules on the left
# and 7 on the right.
QUIET_LEFT_MODULES = 11
QUIET_RIGHT_MODULES = 7

# Long-standing pyStrich proportions: guards extend to 90% of the image
# height, data bars to 80%. The remaining 10% accommodates the digit
# baseline. Roughly approximates the GS1 nominal of guards extending 5
# modules below the data baseline.
GUARD_HEIGHT_FRACTION = 0.9
DATA_HEIGHT_FRACTION = 0.8

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

    height: int
    """Total image height in pixels (= user units for SVG/EPS at default
    DPI). Defaults to half the symbol's pixel width.

    .. versionadded:: 0.12"""

    first_digit_y_offset: float
    """How far above the other text the first digit sits, as a fraction of
    image height. Defaults to ``0.1`` (the long-standing pyStrich look,
    where the leading number-system digit sits slightly higher than the two
    main digit groups). Set to ``0`` for a level baseline across all three
    groups."""


class EAN13Renderer(Bar1DRenderer):
    """Rendering class - given the code and corresponding
    bar encodings and guard bars,
    it will add edge zones and render to an image"""

    options: EAN13RenderOptions
    code: str
    left_bars: str
    right_bars: str
    guards: tuple[str, str, str]

    def __init__(
        self,
        code: str,
        left_bars: str,
        right_bars: str,
        guards: tuple[str, str, str],
        options: EAN13RenderOptions | None = None,
    ) -> None:
        super().__init__(options)
        self.code = code
        self.left_bars = left_bars
        self.right_bars = right_bars
        self.guards = guards

    @property
    def width(self) -> int:
        """Backwards-compatible alias for :attr:`image_width`.

        .. deprecated:: 0.12
           Use :attr:`image_width` for parity with the other 1D renderers.
        """
        return self.image_width

    @property
    def height(self) -> int:
        """Backwards-compatible alias for :attr:`image_height`.

        .. deprecated:: 0.12
           Use :attr:`image_height` for parity with the other 1D renderers.
        """
        return self.image_height

    def _bar_layout(self, bar_width: int) -> BarLayout:
        """Pixel-precise layout shared by PNG, SVG and EPS rendering."""
        def sum_len(total: int, item: str) -> int:
            return total + len(item)

        num_bars = (7 * 12) + reduce(sum_len, self.guards, 0)
        left_quiet = bar_width * QUIET_LEFT_MODULES
        right_quiet = bar_width * QUIET_RIGHT_MODULES
        image_width = left_quiet + right_quiet + (num_bars * bar_width)
        image_height = self.options.get('height') or image_width // 2

        symbol_top = (left_quiet + right_quiet) // 4
        guard_pixel_height = int(image_height * GUARD_HEIGHT_FRACTION) - symbol_top
        data_pixel_height = int(image_height * DATA_HEIGHT_FRACTION) - symbol_top

        segments: list[tuple[str, int]] = [
            (self.guards[0], guard_pixel_height),
            (self.left_bars, data_pixel_height),
            (self.guards[1], guard_pixel_height),
            (self.right_bars, data_pixel_height),
            (self.guards[2], guard_pixel_height),
        ]
        heights = [h if c == "1" else 0 for bars, h in segments for c in bars]

        # Space below tallest bars: where the digit baseline goes in PNG;
        # left blank in SVG/EPS so total canvas height matches.
        quiet_bottom = image_height - symbol_top - guard_pixel_height

        font_size = font_sizes.get(bar_width, 24)
        text_y = image_height * 0.8
        first_digit_y = text_y - image_height * self.options.get(
            "first_digit_y_offset", 0.1
        )
        labels = (
            make_text_label(self.code[0], 1 * bar_width, first_digit_y, font_size),
            make_text_label(self.code[1:7], left_quiet + 7 * bar_width, text_y, font_size),
            make_text_label(self.code[7:], left_quiet + 54 * bar_width, text_y, font_size),
        )

        return BarLayout(
            heights=heights,
            bar_width=bar_width,
            quiet_left=left_quiet,
            quiet_right=right_quiet,
            quiet_top=symbol_top,
            quiet_bottom=quiet_bottom,
            labels=labels,
        )

    def get_pilimage(self, bar_width: int) -> PILImage:
        layout = self._bar_layout(bar_width)
        self.image_width = (
            layout.quiet_left
            + len(layout.heights) * layout.bar_width
            + layout.quiet_right
        )
        self.image_height = layout.quiet_top + max(layout.heights) + layout.quiet_bottom

        img = Image.new('L', (self.image_width, self.image_height), 255)
        draw = ImageDraw.Draw(img)

        for mark in iter_bar_marks(
            layout.heights,
            layout.bar_width,
            quiet_left=layout.quiet_left,
            quiet_top=layout.quiet_top,
        ):
            draw.rectangle(
                (mark.x, mark.y, mark.x + mark.width - 1, mark.y + mark.height - 1),
                fill=0,
            )

        for label in layout.labels:
            font = get_font("courR", label.font_size)
            draw.text((label.x, int(label.y)), label.text, font=font)
        return img
