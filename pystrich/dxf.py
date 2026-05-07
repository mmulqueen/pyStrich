"""DXF renderer shared by the 2D matrix encoders.

Both QR Code and Data Matrix produce a 2D matrix of 0/1 module values;
this module turns one of those matrices into a DXF string suitable for
CAD/CAM tools (e.g. for direct part marking by laser etch or mill).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Literal

from pystrich.exceptions import PyStrichInvalidOption
from pystrich.marks import MarkShape, iter_marks


DxfUnit = Literal["in", "ft", "mi", "mm", "cm", "m"]

# AutoCAD $INSUNITS magic numbers; ``None`` (Unspecified / No units) maps to 0.
_INSUNITS: dict[str | None, int] = {
    None: 0,
    "in": 1,
    "ft": 2,
    "mi": 3,
    "mm": 4,
    "cm": 5,
    "m": 6,
}


def matrix_to_dxf(
    matrix: Sequence[Sequence[int | None]],
    cellsize: float,
    *,
    inverse: bool = True,
    units: DxfUnit | None = "mm",
    mark_shape: MarkShape = MarkShape.SQUARE_CELLS,
) -> str:
    """Render a 2D module matrix as a DXF string.

    By default ``inverse=True`` emits geometry for the light cells (so the
    bounding box frames the symbol including its quiet zone); pass
    ``inverse=False`` to emit only the dark cells. Pass ``units=None`` to
    write ``$INSUNITS=0`` (Unspecified) into the DXF header.
    """
    if units not in _INSUNITS:
        raise PyStrichInvalidOption(
            f"DXF units {units!r} not supported; expected None or one of "
            f"{sorted(u for u in _INSUNITS if u is not None)}."
        )

    matrix_height = len(matrix)
    parts = [
        "0\nSECTION\n2\nHEADER\n",
        # AutoCAD drawing version (AC1006 = R10).
        "9\n$ACADVER\n1\nAC1006\n",
        f"9\n$INSUNITS\n70\n{_INSUNITS[units]}\n",
        "0\nENDSEC\n0\nSECTION\n2\nENTITIES\n",
    ]
    for mark in iter_marks(matrix, mark_values_when=not inverse, mark_shape=mark_shape):
        # DXF y-axis points up, so flip; (x0, y0) is the top-left corner.
        x0 = mark.x * cellsize
        y0 = (matrix_height - mark.y) * cellsize
        x1 = x0 + mark.width * cellsize
        y1 = y0 - mark.height * cellsize
        # Group codes 10/20/30, 11/21/31, 12/22/32, 13/23/33 are X/Y/Z for
        # SOLID corners 0..3; corners 2 and 3 are the bottom edge.
        parts.append(
            "0\nSOLID\n8\nbarcode\n"
            f"10\n{x0}\n20\n{y0}\n30\n0\n"
            f"11\n{x1}\n21\n{y0}\n31\n0\n"
            f"12\n{x0}\n22\n{y1}\n32\n0\n"
            f"13\n{x1}\n23\n{y1}\n33\n0\n"
        )
    parts.append("0\nENDSEC\n0\nEOF\n")
    return "".join(parts)
