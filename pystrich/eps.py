"""EPS renderers shared by the matrix and bar-list encoders.

The 2D encoders (QR Code, Data Matrix) produce a matrix of 0/1 module
values; ``matrix_to_eps`` renders that. The 1D encoders (Code 39, Code
128, EAN-13) produce a flat list of bar heights in module units;
``bars_to_eps`` renders that.
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
from pystrich.marks import (
    BarLayout,
    MarkShape,
    MatrixMark,
    TextLabel,
    iter_bar_marks,
    iter_marks,
)


def _label_procs(chars: Iterable[str]) -> list[str]:
    """Define one PostScript procedure per used glyph (e.g. ``/g_30``)."""
    parts: list[str] = []
    for char in sorted(chars):
        glyph = GLYPHS[char]
        body = glyph.eps_body
        # An empty body (e.g. the space glyph) still needs to be a defined
        # procedure so callers can invoke it unconditionally.
        body_clause = f"newpath {body} fill" if body else ""
        parts.append(f"/{glyph_id(char)} {{ {body_clause} }} def")
    return parts


def _label_blocks(labels: Sequence[TextLabel], view_h: int) -> list[str]:
    """Render each label as a ``gsave``/``translate``/``scale`` block.

    Inside the block, glyphs are drawn at successive em-unit advances. The
    page-level y-flip is applied by the initial ``translate`` (PostScript's
    y-axis points up, while ``TextLabel.y`` is y-down); within the block,
    coordinates are in em-space (font is also y-up), so no y-axis flip is
    needed when drawing the glyph itself.
    """
    parts: list[str] = []
    for label in labels:
        scale, x_start, baseline_y = label_geometry(label)
        eps_baseline = view_h - baseline_y
        block = [
            "gsave",
            f"{_fmt(x_start)} {_fmt(eps_baseline)} translate",
            f"{_fmt(scale)} {_fmt(scale)} scale",
        ]
        for i, char in enumerate(label.text):
            if i > 0:
                block.append(f"{ADVANCE} 0 translate")
            block.append(glyph_id(char))
        block.append("grestore")
        parts.append(" ".join(block))
    return parts


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
    return [f"{m.x} {view_h - m.y - m.height} {m.width} {m.height} rectfill" for m in marks]


def marks_to_eps_circles(marks: Iterable[MatrixMark], view_h: int) -> list[str]:
    """Render each mark as a PostScript filled circle inscribed in its bounding box.

    ``newpath`` is required because ``arc`` adds to the current path.
    """
    return [
        f"newpath {m.x + m.width / 2} {view_h - m.y - m.height / 2} {m.width / 2} 0 360 arc fill"
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
    """Render a 1D bar layout (with optional human-readable labels) as EPS.

    The ``%%BoundingBox`` is in PostScript points (1 pt = 1/72 in). When
    ``layout.labels`` includes glyphs whose font descent extends below the
    natural canvas height, the canvas is enlarged just enough to keep them
    inside the bounding box.
    """
    view_w = layout.quiet_left + len(layout.heights) * layout.bar_width + layout.quiet_right
    view_h = layout.quiet_top + max(layout.heights, default=0) + layout.quiet_bottom
    if layout.labels:
        view_h = max(view_h, ceil(max(label_descent_y(lbl) for lbl in layout.labels)))

    body: list[str] = []
    if layout.labels:
        body.extend(_label_procs(used_chars(layout.labels)))
    body.extend(
        marks_to_eps_rects(
            iter_bar_marks(
                layout.heights,
                layout.bar_width,
                quiet_left=layout.quiet_left,
                quiet_top=layout.quiet_top,
            ),
            view_h,
        )
    )
    if layout.labels:
        body.extend(_label_blocks(layout.labels, view_h))

    return _wrap_eps(view_w, view_h, 1, body=body)
