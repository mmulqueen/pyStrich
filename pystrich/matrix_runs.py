"""Run-length extraction shared by vector renderers (SVG, EPS)."""

from __future__ import annotations

from collections.abc import Iterator, Sequence


def iter_dark_runs(
    matrix: Sequence[Sequence[int | None]],
) -> Iterator[tuple[int, int, int]]:
    """Yield ``(x, y, width)`` for each maximal horizontal run of truthy cells.

    Truthy cells are dark; ``0`` and ``None`` are background.
    """
    for y, row in enumerate(matrix):
        run_start: int | None = None
        for x, cell in enumerate(row):
            if cell:
                if run_start is None:
                    run_start = x
            elif run_start is not None:
                yield (run_start, y, x - run_start)
                run_start = None
        if run_start is not None:
            yield (run_start, y, len(row) - run_start)