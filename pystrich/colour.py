"""Shared colour parsing for the renderers.

.. versionadded:: 0.16
"""

from __future__ import annotations

import string
from dataclasses import dataclass

from pystrich.exceptions import PyStrichInvalidOption

# A Pillow fill/pixel value: a scalar for mode "L", a channel tuple otherwise.
Fill = int | tuple[int, ...]


@dataclass(frozen=True)
class RGBA:
    """An 8-bit red/green/blue/alpha colour. Alpha defaults to fully opaque."""

    r: int
    g: int
    b: int
    a: int = 255

    def __post_init__(self) -> None:
        if not all(0 <= channel <= 255 for channel in (self.r, self.g, self.b, self.a)):
            raise PyStrichInvalidOption(
                f"colour channels must be 0-255, got {(self.r, self.g, self.b, self.a)}"
            )

    @classmethod
    def parse_hex(cls, value: str) -> RGBA:
        """Parse a 3-, 6- or 8-hex-digit colour.

        The leading ``#`` is optional and three-digit shorthand is expanded.
        The alpha channel defaults to fully opaque when no fourth pair is given.

        :param value: Colour as 3, 6 or 8 hexadecimal digits, optionally
            prefixed with ``#``.
        :raises PyStrichInvalidOption: If ``value`` is not a valid hex colour code.
        """
        digits = value[1:] if value.startswith("#") else value
        if len(digits) not in (3, 6, 8) or not all(c in string.hexdigits for c in digits):
            raise PyStrichInvalidOption(f"colour must be 3, 6 or 8 hex digits, got {value!r}")
        if len(digits) == 3:
            digits = "".join(c * 2 for c in digits)
        if len(digits) == 6:
            digits += "ff"
        r, g, b, a = (int(digits[i : i + 2], 16) for i in range(0, 8, 2))
        return cls(r, g, b, a)

    @classmethod
    def coerce(cls, value: str | RGBA) -> RGBA:
        """Return ``value`` as an :class:`RGBA`, parsing a hex string if needed."""
        if not isinstance(value, RGBA):
            return cls.parse_hex(value)
        return value


BLACK = RGBA(0, 0, 0)
WHITE = RGBA(255, 255, 255)


def resolve_colours(dark_hex: str | RGBA | None, light_hex: str | RGBA | None) -> tuple[RGBA, RGBA]:
    """Resolve a ``(dark, light)`` colour pair, defaulting to black on white."""
    dark = RGBA.coerce(dark_hex) if dark_hex is not None else BLACK
    light = RGBA.coerce(light_hex) if light_hex is not None else WHITE
    return dark, light


def require_opaque(rgba: RGBA) -> None:
    """Reject a translucent colour, for formats with no alpha channel (e.g. EPS)."""
    if rgba.a != 255:
        raise PyStrichInvalidOption(
            f"this output cannot use a transparent colour: "
            f"#{rgba.r:02x}{rgba.g:02x}{rgba.b:02x}{rgba.a:02x} "
            "(use a 3- or 6-digit hex, or 8 digits ending in FF)"
        )


def pil_mode(dark: RGBA, light: RGBA) -> str:
    """The narrowest Pillow image mode representing both colours."""
    colours = (dark, light)
    if any(c.a != 255 for c in colours):
        return "RGBA"
    if all(c.r == c.g == c.b for c in colours):
        return "L"
    return "RGB"


def pil_value(rgba: RGBA, mode: str) -> Fill:
    """A colour as a Pillow fill for ``mode`` (a scalar for ``"L"``)."""
    if mode == "L":
        return rgba.r
    if mode == "RGB":
        return (rgba.r, rgba.g, rgba.b)
    return (rgba.r, rgba.g, rgba.b, rgba.a)


def resolve_pil_palette(
    dark_hex: str | RGBA | None, light_hex: str | RGBA | None
) -> tuple[str, Fill, Fill]:
    """Resolve a hex pair into a ``(mode, dark_fill, light_fill)`` for Pillow.

    The raster path always permits alpha, since PNG carries it.
    """
    dark, light = resolve_colours(dark_hex, light_hex)
    mode = pil_mode(dark, light)
    return mode, pil_value(dark, mode), pil_value(light, mode)
