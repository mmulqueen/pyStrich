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


def _check_range(value: float, *, name: str, min_value: int, max_value: int | None) -> None:
    """Reject a value outside ``[min_value, max_value]`` (open above if ``None``)."""
    if value < min_value or (max_value is not None and value > max_value):
        bound = (
            f"at least {min_value}" if max_value is None else f"between {min_value} and {max_value}"
        )
        raise PyStrichInvalidOption(f"{name} must be {bound}, got {value}")


def require_valid_int(
    value: object, *, name: str, min_value: int, max_value: int | None = None
) -> None:
    """Reject a value that is not an ``int`` within ``[min_value, max_value]``.

    A wrong type raises ``TypeError``; an out-of-range value raises
    :class:`~pystrich.exceptions.PyStrichInvalidOption`.
    """
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    _check_range(value, name=name, min_value=min_value, max_value=max_value)


def require_valid_number(
    value: object, *, name: str, min_value: int, max_value: int | None = None
) -> None:
    """Reject a value that is not a finite ``int``/``float`` within ``[min_value, max_value]``.

    A wrong type raises ``TypeError``; a non-finite or out-of-range value raises
    :class:`~pystrich.exceptions.PyStrichInvalidOption`.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    if not math.isfinite(value):
        raise PyStrichInvalidOption(f"{name} must be finite, got {value}")
    _check_range(value, name=name, min_value=min_value, max_value=max_value)


def check_cell_size(value: float, *, name: str, allow_float: bool = False) -> None:
    """Reject an invalid cell size before it reaches a renderer: a positive ``int``
    for raster and vector output, or a non-negative finite number for the DXF path.

    The DXF path scales in real-world units and only multiplies by the cell size,
    so a zero (like any vanishingly small value it already accepts) yields a
    degenerate but valid file rather than a crash."""
    if allow_float:
        require_valid_number(value, name=name, min_value=0)
    else:
        require_valid_int(value, name=name, min_value=1)


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
