"""SVG renderers shared by the matrix and bar-list encoders.

The 2D encoders (QR Code, Data Matrix) produce a matrix of 0/1 module
values; ``matrix_to_svg`` renders that. The 1D encoders (Code 39, Code
128, EAN-13) produce a flat list of bar heights in module units;
``bars_to_svg`` renders that.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pystrich.marks import BarLayout, MarkShape, MatrixMark, iter_bar_marks, iter_marks


def _wrap_svg(
    view_w: int,
    view_h: int,
    cellsize: int,
    *,
    shape_rendering: str,
    body: Sequence[str],
) -> str:
    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {view_w} {view_h}" '
        f'width="{view_w * cellsize}" height="{view_h * cellsize}" '
        f'shape-rendering="{shape_rendering}">',
        f'<rect width="{view_w}" height="{view_h}" fill="#fff"/>',
        '<g fill="#000">',
        *body,
        '</g>',
        '</svg>',
    ]
    return '\n'.join(parts) + '\n'


def marks_to_svg_rects(marks: Iterable[MatrixMark]) -> list[str]:
    """Render each mark as an SVG ``<rect>`` element."""
    return [
        f'<rect x="{m.x}" y="{m.y}" width="{m.width}" height="{m.height}"/>'
        for m in marks
    ]


def marks_to_svg_circles(marks: Iterable[MatrixMark]) -> list[str]:
    """Render each mark as an SVG ``<circle>`` inscribed in its bounding box."""
    return [
        f'<circle cx="{m.x + m.width / 2}" cy="{m.y + m.height / 2}" '
        f'r="{m.width / 2}"/>'
        for m in marks
    ]


def matrix_to_svg(
    matrix: Sequence[Sequence[int | None]],
    cellsize: int,
    *,
    inverse: bool = False,
    mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
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
        "geometricPrecision"
        if mark_shape is MarkShape.CIRCULAR_CELLS
        else "crispEdges"
    )

    marks = iter_marks(matrix, mark_values_when=not inverse, mark_shape=mark_shape)
    if mark_shape is MarkShape.CIRCULAR_CELLS:
        body = marks_to_svg_circles(marks)
    else:
        body = marks_to_svg_rects(marks)

    return _wrap_svg(width, height, cellsize, shape_rendering=shape_rendering, body=body)


def bars_to_svg(layout: BarLayout) -> str:
    """Render a 1D bar layout as an SVG string.

    The ``viewBox`` and ``width``/``height`` are in pixels (= user units
    at default DPI), matching the dimensions a PNG renderer would
    produce for the same :class:`BarLayout`.
    """
    view_w = (
        layout.quiet_left
        + len(layout.heights) * layout.bar_width
        + layout.quiet_right
    )
    view_h = layout.quiet_top + max(layout.heights, default=0) + layout.quiet_bottom

    body = marks_to_svg_rects(iter_bar_marks(
        layout.heights,
        layout.bar_width,
        quiet_left=layout.quiet_left,
        quiet_top=layout.quiet_top,
    ))

    return _wrap_svg(view_w, view_h, 1, shape_rendering="crispEdges", body=body)
