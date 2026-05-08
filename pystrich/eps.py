"""EPS renderers shared by the matrix and bar-list encoders.

The 2D encoders (QR Code, Data Matrix) produce a matrix of 0/1 module
values; ``matrix_to_eps`` renders that. The 1D encoders (Code 39, Code
128, EAN-13) produce a flat list of bar heights in module units;
``bars_to_eps`` renders that.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from pystrich.marks import BarLayout, MarkShape, MatrixMark, iter_bar_marks, iter_marks


def _wrap_eps(
    view_w: int,
    view_h: int,
    cellsize: int,
    *,
    body: Sequence[str],
) -> str:
    bbox_w = view_w * cellsize
    bbox_h = view_h * cellsize
    parts = [
        "%!PS-Adobe-3.0 EPSF-3.0",
        "%%Creator: pyStrich",
        f"%%BoundingBox: 0 0 {bbox_w} {bbox_h}",
        f"%%HiResBoundingBox: 0 0 {bbox_w} {bbox_h}",
        "%%EndComments",
        "gsave",
        f"{cellsize} {cellsize} scale",
        "1 setgray",
        f"0 0 {view_w} {view_h} rectfill",
        "0 setgray",
        *body,
        "grestore",
        "%%EOF",
    ]
    return "\n".join(parts) + "\n"


def marks_to_eps_rects(marks: Iterable[MatrixMark], view_h: int) -> list[str]:
    """Render each mark as a PostScript ``rectfill``.

    PostScript's y-axis points up, so y is flipped against ``view_h``.
    """
    return [
        f"{m.x} {view_h - m.y - m.height} {m.width} {m.height} rectfill"
        for m in marks
    ]


def marks_to_eps_circles(marks: Iterable[MatrixMark], view_h: int) -> list[str]:
    """Render each mark as a PostScript filled circle inscribed in its bounding box.

    ``newpath`` is required because ``arc`` adds to the current path.
    """
    return [
        f"newpath {m.x + m.width / 2} {view_h - m.y - m.height / 2} "
        f"{m.width / 2} 0 360 arc fill"
        for m in marks
    ]


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

    marks = iter_marks(matrix, mark_values_when=not inverse, mark_shape=mark_shape)
    if mark_shape is MarkShape.CIRCULAR_CELLS:
        body = marks_to_eps_circles(marks, height)
    else:
        body = marks_to_eps_rects(marks, height)

    return _wrap_eps(width, height, cellsize, body=body)


def bars_to_eps(layout: BarLayout) -> str:
    """Render a 1D bar layout as an EPS string.

    The ``%%BoundingBox`` is in PostScript points (1 pt = 1/72 in) and
    matches the pixel dimensions a PNG renderer would produce for the
    same :class:`BarLayout`.
    """
    view_w = (
        layout.quiet_left
        + len(layout.heights) * layout.bar_width
        + layout.quiet_right
    )
    view_h = layout.quiet_top + max(layout.heights, default=0) + layout.quiet_bottom

    body = marks_to_eps_rects(
        iter_bar_marks(
            layout.heights,
            layout.bar_width,
            quiet_left=layout.quiet_left,
            quiet_top=layout.quiet_top,
        ),
        view_h,
    )

    return _wrap_eps(view_w, view_h, 1, body=body)
