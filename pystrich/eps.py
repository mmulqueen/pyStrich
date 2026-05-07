"""EPS renderer shared by the 2D matrix encoders.

Both QR Code and Data Matrix produce a 2D matrix of 0/1 module values;
this module turns one of those matrices into an Encapsulated PostScript
string.
"""

from __future__ import annotations

from collections.abc import Sequence

from pystrich.marks import MarkShape, iter_marks


def matrix_to_eps(
    matrix: Sequence[Sequence[int | None]],
    cellsize: int,
    *,
    inverse: bool = False,
    mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
) -> str:
    """Render a 2D module matrix as an EPS string.

    By default truthy cells become dark squares and ``0``/``None`` are
    background; pass ``inverse=True`` to mark the light cells instead.
    Coordinates inside the EPS body are in module units (after the
    ``cellsize cellsize scale``); the ``%%BoundingBox`` is in PostScript
    points and so scales by ``cellsize``.
    """
    height = len(matrix)
    width = len(matrix[0]) if height else 0
    bbox_w = width * cellsize
    bbox_h = height * cellsize

    parts = [
        "%!PS-Adobe-3.0 EPSF-3.0",
        "%%Creator: pyStrich",
        f"%%BoundingBox: 0 0 {bbox_w} {bbox_h}",
        f"%%HiResBoundingBox: 0 0 {bbox_w} {bbox_h}",
        "%%EndComments",
        "gsave",
        f"{cellsize} {cellsize} scale",
        "1 setgray",
        f"0 0 {width} {height} rectfill",
        "0 setgray",
    ]

    for mark in iter_marks(matrix, mark_values_when=not inverse, mark_shape=mark_shape):
        if mark_shape is MarkShape.CIRCULAR_CELLS:
            # PostScript y-axis points up, so flip the centre. ``newpath`` is
            # required because ``arc`` adds to the current path.
            cx = mark.x + mark.width / 2
            cy = height - mark.y - mark.height / 2
            r = mark.width / 2
            parts.append(f"newpath {cx} {cy} {r} 0 360 arc fill")
        else:
            parts.append(
                f"{mark.x} {height - mark.y - mark.height} "
                f"{mark.width} {mark.height} rectfill"
            )

    parts.append("grestore")
    parts.append("%%EOF")
    return "\n".join(parts) + "\n"
