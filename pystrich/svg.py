"""SVG renderers shared by the matrix and bar-list encoders.

The 2D encoders (QR Code, Data Matrix) produce a matrix of 0/1 module
values; ``matrix_to_svg`` renders that. The 1D encoders (Code 39, Code
128, EAN-13) produce a flat list of bar heights in module units;
``bars_to_svg`` renders that.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from math import ceil

from pystrich._courier_glyphs import ADVANCE, GLYPHS
from pystrich._vector_text import (
    fmt as _fmt,
)
from pystrich._vector_text import (
    glyph_id,
    label_descent_y,
    label_geometry,
    used_chars,
)
from pystrich.colour import RGBA, resolve_colours
from pystrich.marks import (
    BarLayout,
    MarkShape,
    MatrixMark,
    TextLabel,
    iter_barcode_marks,
    iter_marks,
)


def _shortest_hex(r: int, g: int, b: int) -> str:
    """Shortest equivalent hex, collapsing ``#rrggbb`` to ``#rgb`` when it doubles."""
    pairs = [f"{r:02x}", f"{g:02x}", f"{b:02x}"]
    if all(p[0] == p[1] for p in pairs):
        return "#" + "".join(p[0] for p in pairs)
    return "#" + "".join(pairs)


def _svg_fill(rgba: RGBA) -> str:
    """A colour as SVG ``fill`` attribute(s).

    SVG 1.1 hex colours have no alpha, so a translucent colour is split into an
    RGB ``fill`` plus a separate ``fill-opacity`` for the broadest renderer
    support.
    """
    fill = f'fill="{_shortest_hex(rgba.r, rgba.g, rgba.b)}"'
    if rgba.a == 255:
        return fill
    return f'{fill} fill-opacity="{_fmt(rgba.a / 255)}"'


def _label_defs(chars: Iterable[str]) -> list[str]:
    """Render a ``<defs>`` block defining one ``<symbol>`` per used glyph."""
    parts: list[str] = ["<defs>"]
    for char in sorted(chars):
        glyph = GLYPHS[char]
        parts.append(
            f'<symbol id="{glyph_id(char)}" overflow="visible"><path d="{glyph.svg_d}"/></symbol>'
        )
    parts.append("</defs>")
    return parts


def _label_groups(labels: Sequence[TextLabel]) -> list[str]:
    """Render each label as a transformed ``<g>`` of ``<use>`` references.

    The wrapping group flips y (font is y-up, SVG is y-down) and scales
    em-units to pixels; glyphs are placed via per-character ``<use x=...>``
    in em-space.
    """
    parts: list[str] = ['<g shape-rendering="geometricPrecision">']
    for label in labels:
        scale, x_start, baseline_y = label_geometry(label)
        uses = "".join(
            f'<use href="#{glyph_id(c)}" x="{i * ADVANCE}"/>' for i, c in enumerate(label.text)
        )
        parts.append(
            f'<g transform="translate({_fmt(x_start)} {_fmt(baseline_y)}) '
            f'scale({_fmt(scale)} {_fmt(-scale)})">{uses}</g>'
        )
    parts.append("</g>")
    return parts


def _wrap_svg(
    view_w: int,
    view_h: int,
    cellsize: int,
    *,
    shape_rendering: str,
    body: Sequence[str],
    dark_fill: str,
    light_fill: str,
) -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {view_w} {view_h}" '
        f'width="{view_w * cellsize}" height="{view_h * cellsize}" '
        f'shape-rendering="{shape_rendering}">',
        f'<rect width="{view_w}" height="{view_h}" {light_fill}/>',
        f"<g {dark_fill}>",
        *body,
        "</g>",
        "</svg>",
    ]
    return "\n".join(parts) + "\n"


def marks_to_svg_rects(marks: Iterable[MatrixMark]) -> list[str]:
    """Render each mark as an SVG ``<rect>`` element."""
    return [f'<rect x="{x}" y="{y}" width="{w}" height="{h}"/>' for x, y, w, h in marks]


def marks_to_svg_circles(marks: Iterable[MatrixMark]) -> list[str]:
    """Render each mark as an SVG ``<circle>`` inscribed in its bounding box."""
    return [f'<circle cx="{x + w / 2}" cy="{y + h / 2}" r="{w / 2}"/>' for x, y, w, h in marks]


def matrix_to_svg(
    matrix: Sequence[Sequence[int | None]],
    cellsize: int,
    *,
    inverse: bool = False,
    mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
    dark_hex: str | RGBA | None = None,
    light_hex: str | RGBA | None = None,
) -> str:
    """Render a 2D module matrix as an SVG string.

    By default truthy cells become dark squares and ``0``/``None`` are
    background; pass ``inverse=True`` to mark the light cells instead.
    The ``viewBox`` is in module units; ``width`` and ``height`` scale
    by ``cellsize``.
    """
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    # crispEdges gives axis-aligned rectangles pixel-snapped edges; for circles
    # we want curve fidelity instead.
    shape_rendering = (
        "geometricPrecision" if mark_shape is MarkShape.CIRCULAR_CELLS else "crispEdges"
    )

    marks = iter_marks(matrix, mark_values_when=not inverse, mark_shape=mark_shape)
    if mark_shape is MarkShape.CIRCULAR_CELLS:
        body = marks_to_svg_circles(marks)
    else:
        body = marks_to_svg_rects(marks)

    dark, light = resolve_colours(dark_hex, light_hex)
    return _wrap_svg(
        width,
        height,
        cellsize,
        shape_rendering=shape_rendering,
        body=body,
        dark_fill=_svg_fill(dark),
        light_fill=_svg_fill(light),
    )


def bars_to_svg(
    layout: BarLayout, *, dark_hex: str | RGBA | None = None, light_hex: str | RGBA | None = None
) -> str:
    """Render a 1D bar layout (with optional human-readable labels) as SVG.

    The ``viewBox`` and ``width``/``height`` are in pixels (= user units
    at default DPI). When ``layout.labels`` includes glyphs whose font
    descent extends below the natural canvas height, the canvas is
    enlarged just enough to keep them inside the ``viewBox``.
    """
    view_w = layout.quiet_left + len(layout.heights) * layout.bar_width + layout.quiet_right
    view_h = layout.quiet_top + max(layout.heights, default=0) + layout.quiet_bottom
    if layout.labels:
        view_h = max(view_h, ceil(max(label_descent_y(lbl) for lbl in layout.labels)))

    body: list[str] = []
    if layout.labels:
        body.extend(_label_defs(used_chars(layout.labels)))
    body.extend(marks_to_svg_rects(iter_barcode_marks(layout)))
    if layout.labels:
        body.extend(_label_groups(layout.labels))

    dark, light = resolve_colours(dark_hex, light_hex)
    return _wrap_svg(
        view_w,
        view_h,
        1,
        shape_rendering="crispEdges",
        body=body,
        dark_fill=_svg_fill(dark),
        light_fill=_svg_fill(light),
    )
