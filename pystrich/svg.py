"""SVG renderer shared by the 2D matrix encoders.

Both QR Code and Data Matrix produce a 2D matrix of 0/1 module values;
this module turns one of those matrices into an SVG string. Adjacent
dark cells in a row are merged into a single ``<rect>`` to keep the
output compact.
"""

from __future__ import annotations

from collections.abc import Sequence


def matrix_to_svg(matrix: Sequence[Sequence[int | None]], cellsize: int) -> str:
    """Render a 2D module matrix as an SVG string.

    Truthy cells become dark squares; ``0`` and ``None`` are background.
    The ``viewBox`` is in module units; ``width`` and ``height`` scale
    by ``cellsize``.
    """
    height = len(matrix)
    width = len(matrix[0]) if height else 0

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width * cellsize}" height="{height * cellsize}" '
        'shape-rendering="crispEdges">',
        f'<rect width="{width}" height="{height}" fill="#fff"/>',
        '<g fill="#000">',
    ]

    for y, row in enumerate(matrix):
        run_start: int | None = None
        for x, cell in enumerate(row):
            if cell:
                if run_start is None:
                    run_start = x
            elif run_start is not None:
                parts.append(
                    f'<rect x="{run_start}" y="{y}" '
                    f'width="{x - run_start}" height="1"/>'
                )
                run_start = None
        if run_start is not None:
            parts.append(
                f'<rect x="{run_start}" y="{y}" '
                f'width="{len(row) - run_start}" height="1"/>'
            )

    parts.append('</g>')
    parts.append('</svg>')
    return '\n'.join(parts) + '\n'
