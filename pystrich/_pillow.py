"""Guarded access to Pillow, an optional dependency required only for PNG output.

PNG renderers import the Pillow submodules from this module *inside* the
functions that need them, rather than from ``PIL`` at module top level, so the
package stays importable -- and SVG, EPS, DXF and terminal output keep
working -- when Pillow is not installed. Type-only references go through the
re-exported :data:`PILImage` for the same reason, keeping ``PIL`` out of every
module but this one.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pystrich.exceptions import PyStrichPillowNotInstalled

if TYPE_CHECKING:
    # Re-exported so other modules annotate with pystrich._pillow.PILImage and
    # keep PIL out of their imports (enforced by the TID251 ruff rule).
    from PIL.Image import Image as PILImage  # noqa: F401

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError as exc:
    raise PyStrichPillowNotInstalled() from exc

__all__ = ["Image", "ImageDraw", "ImageFont"]
