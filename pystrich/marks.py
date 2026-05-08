"""Matrix mark extraction shared by vector renderers (SVG, EPS, DXF)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from enum import Enum, auto
from typing import NamedTuple


class MatrixMark(NamedTuple):
    """A rectangular region of a matrix to be drawn as a single shape."""

    x: int
    y: int
    width: int
    height: int


class MarkShape(Enum):
    """How marked cells are grouped and drawn in vector output.

    Each value selects a grouping (one ``MatrixMark`` per cell, or one per
    horizontal run) and -- where the renderer supports it -- the drawing
    primitive used per mark.
    """

    HORIZONTAL_RUNS = auto()
    """Maximal horizontal runs of matched cells, drawn as filled rectangles."""

    SQUARE_CELLS = auto()
    """One 1x1 region per matched cell, drawn as a filled rectangle."""

    CIRCULAR_CELLS = auto()
    """One 1x1 region per matched cell, drawn as a filled circle inscribed in the cell."""


def iter_horizontal_runs(
    matrix: Sequence[Sequence[int | None]],
    *,
    mark_values_when: bool,
) -> Iterator[MatrixMark]:
    """Yield each maximal horizontal run of cells whose truthiness equals ``mark_values_when``.

    ``mark_values_when=True`` marks the dark (truthy) cells; ``False`` marks
    the light cells (``0`` or ``None``). Each yielded mark has ``height=1``.
    """
    for y, row in enumerate(matrix):
        run_start: int | None = None
        for x, cell in enumerate(row):
            if bool(cell) == mark_values_when:
                if run_start is None:
                    run_start = x
            elif run_start is not None:
                yield MatrixMark(run_start, y, x - run_start, 1)
                run_start = None
        if run_start is not None:
            yield MatrixMark(run_start, y, len(row) - run_start, 1)


def iter_cells(
    matrix: Sequence[Sequence[int | None]],
    *,
    mark_values_when: bool,
) -> Iterator[MatrixMark]:
    """Yield a 1x1 mark for every cell whose truthiness equals ``mark_values_when``."""
    for y, row in enumerate(matrix):
        for x, cell in enumerate(row):
            if bool(cell) == mark_values_when:
                yield MatrixMark(x, y, 1, 1)


def iter_marks(
    matrix: Sequence[Sequence[int | None]],
    *,
    mark_values_when: bool,
    mark_shape: MarkShape,
) -> Iterator[MatrixMark]:
    """Yield ``MatrixMark`` regions for the chosen ``mark_shape``."""
    if mark_shape is MarkShape.HORIZONTAL_RUNS:
        return iter_horizontal_runs(matrix, mark_values_when=mark_values_when)
    if mark_shape in (MarkShape.SQUARE_CELLS, MarkShape.CIRCULAR_CELLS):
        return iter_cells(matrix, mark_values_when=mark_values_when)
    raise ValueError(f"Unknown MarkShape: {mark_shape!r}")


class TextLabel(NamedTuple):
    """A run of text to render below the bars in vector output.

    Coordinates are in pixels (= user units for SVG/EPS at default DPI),
    and ``y`` is the *top* edge of the text — matching the convention used
    by ``PIL.ImageDraw.text(xy, ...)`` for the corresponding raster path.
    ``anchor`` controls how ``x`` relates to the text run: ``"start"`` is
    the left edge, ``"middle"`` the centre, ``"end"`` the right edge.
    """

    text: str
    x: float
    y: float
    font_size: int
    anchor: str = "start"


class BarLayout(NamedTuple):
    """Pixel-precise layout of a 1D barcode for any output format.

    All values are in pixels (= user units for SVG/EPS at default DPI).
    ``heights[i]`` is the bar's pixel height at column ``i`` (``0`` is a
    gap). Each column is ``bar_width`` pixels wide. The four quiet zones
    frame the symbol; ``quiet_left`` and ``quiet_top`` shift the bars,
    while ``quiet_right`` and ``quiet_bottom`` only enlarge the canvas.
    ``labels`` carries the human-readable text drawn beneath the bars by
    SVG/EPS renderers; the PNG path renders text via PIL directly and
    ignores this field.
    """

    heights: Sequence[int]
    bar_width: int
    quiet_left: int = 0
    quiet_right: int = 0
    quiet_top: int = 0
    quiet_bottom: int = 0
    labels: Sequence[TextLabel] = ()


def iter_bar_marks(
    heights: Sequence[int],
    bar_width: int,
    *,
    quiet_left: int = 0,
    quiet_top: int = 0,
) -> Iterator[MatrixMark]:
    """Yield a ``MatrixMark`` per maximal run of equal positive heights.

    Coordinates and dimensions are in pixels. ``heights[i]`` is the bar's
    pixel height at column ``i`` (``0`` is a gap; positive values are bars
    sharing a top edge at ``y = quiet_top``). Each column is ``bar_width``
    pixels wide. Adjacent columns with the same positive height collapse
    into one mark.

    Only ``quiet_left`` and ``quiet_top`` are accepted because they are
    the only offsets that affect mark coordinates; the right and bottom
    quiet zones are a renderer concern (canvas / viewBox sizing).
    """
    run_start: int | None = None
    run_height = 0
    for col, h in enumerate(heights):
        if h == run_height and run_start is not None:
            continue
        if run_start is not None:
            yield MatrixMark(
                quiet_left + run_start * bar_width,
                quiet_top,
                (col - run_start) * bar_width,
                run_height,
            )
            run_start = None
            run_height = 0
        if h > 0:
            run_start = col
            run_height = h
    if run_start is not None:
        yield MatrixMark(
            quiet_left + run_start * bar_width,
            quiet_top,
            (len(heights) - run_start) * bar_width,
            run_height,
        )
