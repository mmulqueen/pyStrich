"""SVG renderer shared by the 2D matrix encoders.

Both QR Code and Data Matrix produce a 2D matrix of 0/1 module values;
this module turns one of those matrices into an SVG string.
"""

from __future__ import annotations

from collections.abc import Sequence

from pystrich.marks import MarkShape, iter_marks


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

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width * cellsize}" height="{height * cellsize}" '
        f'shape-rendering="{shape_rendering}">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        '<g fill="#000">',
    ]

    for mark in iter_marks(matrix, mark_values_when=not inverse, mark_shape=mark_shape):
        if mark_shape is MarkShape.CIRCULAR_CELLS:
            cx = mark.x + mark.width / 2
            cy = mark.y + mark.height / 2
            r = mark.width / 2
            parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}"/>')
        else:
            parts.append(
                f'<rect x="{mark.x}" y="{mark.y}" '
                f'width="{mark.width}" height="{mark.height}"/>'
            )

    parts.append('</g>')
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'
