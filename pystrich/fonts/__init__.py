from __future__ import annotations

import os

from PIL import ImageFont


def get_font(font_name: str, font_size: int) -> ImageFont.ImageFont:
    fontdir = os.path.dirname(os.path.abspath(__file__))
    fontfile = os.path.join(fontdir, f"{font_name}{font_size:02d}.pil")
    return ImageFont.load_path(fontfile)
