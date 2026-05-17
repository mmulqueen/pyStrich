"""Damage simulators for the docs damage-tolerance demos and matching tests.

Each ``*_smudge_demo`` function builds a damaged barcode image with the
parameters used in ``docs/printing.rst``. The corresponding
``test_*_smudge_tolerance`` tests assert zxing-cpp still decodes the
result; if the parameters drift the tests fail.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PIL import Image, ImageChops, ImageDraw, ImageFilter

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage


def motion_blur_smudge(
    img: PILImage,
    *,
    distance: int,
    angle_deg: float,
    bbox_rel: tuple[float, float, float, float],
    feather: int,
) -> PILImage:
    """Apply a directional motion-blur smudge over an elliptical region.

    :param img: source image (any mode; result is "L").
    :param distance: number of pixel-step averages along the smear direction.
    :param angle_deg: smear direction, degrees from horizontal.
    :param bbox_rel: ``(x0, y0, x1, y1)`` mask bbox as fractions of width/height.
    :param feather: Gaussian-blur radius applied to the mask, in pixels.
    """
    img = img.convert("L")
    w, h = img.size

    dx_per_step = math.cos(math.radians(angle_deg))
    dy_per_step = math.sin(math.radians(angle_deg))
    blurred = img.copy()
    for t in range(1, distance):
        shifted = ImageChops.offset(img, round(dx_per_step * t), round(dy_per_step * t))
        blurred = Image.blend(blurred, shifted, 1 / (t + 1))

    x0, y0, x1, y1 = bbox_rel
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([w * x0, h * y0, w * x1, h * y1], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=feather))

    return Image.composite(blurred, img, mask)


def aztec_smudge_demo(text: str) -> PILImage:
    """Aztec at ``ecc=50`` with a diagonal smudge over the lower-right corner."""
    from pystrich.aztec import AztecEncoder

    return motion_blur_smudge(
        AztecEncoder(text, ecc=50).get_pilimage(cellsize=10),
        distance=45,
        angle_deg=25,
        bbox_rel=(0.50, 0.55, 1.00, 1.00),
        feather=15,
    )


def datamatrix_smudge_demo(text: str) -> PILImage:
    """Data Matrix with a diagonal smudge over the interior.

    The smudge stays clear of all four edges, which carry the L-finder
    and clock-track fixed patterns.
    """
    from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

    return motion_blur_smudge(
        DataMatrixEncoder(DataMatrixData(text, auto_encoding=True)).get_pilimage(cellsize=10),
        distance=45,
        angle_deg=25,
        bbox_rel=(0.25, 0.30, 0.75, 0.70),
        feather=15,
    )


def qrcode_smudge_demo(text: str) -> PILImage:
    """QR Code at ``ecl="H"`` with a diagonal smudge over the middle.

    The smudge stays clear of the three finder patterns at the corners.
    """
    from pystrich.qrcode import QRCodeEncoder

    return motion_blur_smudge(
        QRCodeEncoder(text, ecl="H").get_pilimage(cellsize=10),
        distance=55,
        angle_deg=25,
        bbox_rel=(0.20, 0.30, 0.80, 0.70),
        feather=18,
    )
