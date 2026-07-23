"""Resource limits guarding against oversized renders.

pyStrich turns untrusted input into images whose size is the product of the
symbol's module count and the requested cell size. Both multiplicands can be
driven by a caller, so an unbounded request can exhaust memory (a raster buffer
is materialised pixel-by-pixel) or CPU. The guards here fail such requests fast,
with a typed :class:`~pystrich.exceptions.PyStrichError`, before any allocation.

The two thresholds are plain module attributes; reassign them to raise or lower
a limit process-wide, e.g. ``pystrich.limits.MAX_IMAGE_PIXELS = 400_000_000``.
The guard functions read the current value on each call, so a reassignment takes
effect immediately.
"""

from __future__ import annotations

import math

from pystrich.exceptions import PyStrichInvalidOption, PyStrichInvalidPayloadLength

# Maximum pixel count (width times height) of a rendered raster image. The
# default matches Pillow's own Image.MAX_IMAGE_PIXELS bomb threshold.
MAX_IMAGE_PIXELS: int = 89_478_485

# Fallback maximum payload length (characters) for formats without a specific
# cap -- the 1D symbologies, which have no fixed capacity. Formats that know
# their true maximum set ``EncodableData._MAX_PAYLOAD_LENGTH`` instead. This is a
# coarse anti-DoS ceiling; each format still enforces its own capacity.
MAX_INPUT_LENGTH: int = 8192


def check_cell_size(value: int, *, name: str) -> None:
    """Reject a non-positive cell size before it reaches a renderer."""
    if value <= 0:
        raise PyStrichInvalidOption(f"{name} must be positive, got {value}")


def check_image_pixels(
    width_px: int, height_px: int, *, cellsize: int | None = None, name: str = "cell size"
) -> None:
    """Reject a raster whose pixel count exceeds :data:`MAX_IMAGE_PIXELS`.

    Pass ``cellsize`` (for a symbol whose pixel size is a whole multiple of it)
    to have the message name the largest ``cellsize`` that would still fit;
    ``name`` labels that dimension in the message.
    """
    pixels = width_px * height_px
    if pixels <= MAX_IMAGE_PIXELS:
        return
    hint = ""
    if cellsize:
        cells_w, cells_h = width_px // cellsize, height_px // cellsize
        largest = math.isqrt(MAX_IMAGE_PIXELS // (cells_w * cells_h))
        hint = f" (the largest {name} for this {cells_w}x{cells_h} symbol is {largest})"
    raise PyStrichInvalidOption(
        f"rendered image would be {width_px}x{height_px} = {pixels} pixels, "
        f"exceeding the maximum of {MAX_IMAGE_PIXELS}{hint}; reduce the {name} or "
        f"increase pystrich.limits.MAX_IMAGE_PIXELS"
    )


def check_input_length(length: int, max_length: int | None = None) -> None:
    """Reject a payload longer than ``max_length`` before encoding it.

    ``max_length`` of ``None`` falls back to :data:`MAX_INPUT_LENGTH`.
    """
    limit = MAX_INPUT_LENGTH if max_length is None else max_length
    if length > limit:
        raise PyStrichInvalidPayloadLength(
            f"input is {length} characters, exceeding the maximum of {limit}"
        )
