"""EPS renderer shared by the 2D matrix encoders.

Both QR Code and Data Matrix produce a 2D matrix of 0/1 module values;
this module turns one of those matrices into an Encapsulated PostScript
string. Adjacent dark cells in a row are merged into a single
``rectfill`` call to keep the output compact.
"""

from __future__ import annotations

from collections.abc import Sequence

from pystrich.matrix_runs import iter_dark_runs


def matrix_to_eps(matrix: Sequence[Sequence[int | None]], cellsize: int) -> str:
    """Render a 2D module matrix as an EPS string.

    Truthy cells become dark squares; ``0`` and ``None`` are background.
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

    for x, y, w in iter_dark_runs(matrix):
        parts.append(f"{x} {height - 1 - y} {w} 1 rectfill")

    parts.append("grestore")
    parts.append("%%EOF")
    return "\n".join(parts) + "\n"