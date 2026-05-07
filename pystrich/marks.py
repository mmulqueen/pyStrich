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
