"""Helpers shared by ``pystrich.svg`` and ``pystrich.eps`` for placing
labels (``TextLabel``) using the bundled Courier Prime glyph outlines in
``pystrich._courier_glyphs``.

Conventions:

* Coordinates returned by these helpers use the SVG y-down convention
  (``y`` increases downward), matching ``TextLabel.y`` semantics. EPS
  callers are responsible for the page-level y-flip.
* The "scale" returned converts em-space coordinates (in which the
  glyph data is stored) into pixels.
"""

from __future__ import annotations

from collections.abc import Iterable

from pystrich._courier_glyphs import ADVANCE, ASCENT, DESCENT, EM_SIZE, GLYPHS
from pystrich.marks import TextLabel


def glyph_id(char: str) -> str:
    """Stable identifier for a printable-ASCII glyph.

    Doubles as the SVG ``<symbol id>`` and the EPS procedure name, e.g.
    ``"0"`` -> ``"g_30"``.
    """
    return f"g_{ord(char):02X}"


def make_text_label(
    text: str,
    x: float,
    y: float,
    font_size: int,
    anchor: str = "start",
) -> TextLabel:
    """Construct a :class:`TextLabel` for SVG/EPS rendering.

    Characters with no embedded glyph outline are dropped from ``text``.
    The bundled glyph set covers printable ASCII (0x20-0x7E); Code 128
    accepts charset-A controls (0x00-0x1F) which have no visible
    representation, so the SVG/EPS label silently omits them rather than
    crashing the renderer. Downstream helpers in this module assume all
    characters in ``TextLabel.text`` are renderable.
    """
    return TextLabel(
        text="".join(c for c in text if c in GLYPHS),
        x=x,
        y=y,
        font_size=font_size,
        anchor=anchor,
    )


def label_geometry(label: TextLabel) -> tuple[float, float, float]:
    """Return ``(scale, x_start, baseline_y)`` for placing ``label``.

    ``x_start`` is the leftmost pixel of the rendered run after applying
    the label's anchor; ``baseline_y`` is the y of the typographic
    baseline in y-down (SVG) coordinates.
    """
    scale = label.font_size / EM_SIZE
    total_advance = len(label.text) * ADVANCE * scale
    if label.anchor == "start":
        x_start = label.x
    elif label.anchor == "middle":
        x_start = label.x - total_advance / 2
    elif label.anchor == "end":
        x_start = label.x - total_advance
    else:
        raise ValueError(f"Unsupported TextLabel.anchor: {label.anchor!r}")
    baseline_y = label.y + (ASCENT / EM_SIZE) * label.font_size
    return scale, x_start, baseline_y


def label_descent_y(label: TextLabel) -> float:
    """Lowest y-pixel a glyph in ``label`` can reach (font descent included)."""
    return label.y + ((ASCENT + DESCENT) / EM_SIZE) * label.font_size


def used_chars(labels: Iterable[TextLabel]) -> set[str]:
    chars: set[str] = set()
    for label in labels:
        chars.update(label.text)
    return chars


def fmt(value: float) -> str:
    """Format a numeric coordinate compactly for SVG/EPS output.

    Four decimal places keep small per-em scale ratios (e.g. ``0.0088``
    for ``font_size / EM_SIZE`` at small bar widths) precise enough that
    the resulting glyph size error is well under one rendered pixel.
    """
    rendered = f"{value:.4f}".rstrip("0").rstrip(".")
    return rendered or "0"
