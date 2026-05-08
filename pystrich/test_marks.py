"""Direct unit tests for pystrich.marks.iter_bar_marks."""

import pytest

from pystrich.marks import MatrixMark, iter_bar_marks


@pytest.mark.parametrize("heights, expected", [
    pytest.param([], [], id="empty"),
    pytest.param([0, 0, 0], [], id="all-gaps"),
    pytest.param([5], [MatrixMark(0, 0, 1, 5)], id="single-bar"),
    pytest.param(
        [5, 5, 5],
        [MatrixMark(0, 0, 3, 5)],
        id="merge-equal-heights",
    ),
    pytest.param(
        [5, 3],
        [MatrixMark(0, 0, 1, 5), MatrixMark(1, 0, 1, 3)],
        id="adjacent-different-heights-do-not-merge",
    ),
    pytest.param(
        [0, 5, 5, 0, 3, 3, 3, 0],
        [MatrixMark(1, 0, 2, 5), MatrixMark(4, 0, 3, 3)],
        id="gaps-terminate-runs",
    ),
    pytest.param(
        [5, 5],
        [MatrixMark(0, 0, 2, 5)],
        id="run-terminates-at-end",
    ),
    pytest.param(
        [5, 3, 3, 5],
        [
            MatrixMark(0, 0, 1, 5),
            MatrixMark(1, 0, 2, 3),
            MatrixMark(3, 0, 1, 5),
        ],
        id="height-changes-without-gap",
    ),
])
def test_iter_bar_marks_runs(heights, expected):
    """At bar_width=1, the column index equals the pixel x coordinate."""
    assert list(iter_bar_marks(heights, 1)) == expected


@pytest.mark.parametrize("bar_width, expected", [
    pytest.param(
        1,
        [MatrixMark(0, 0, 2, 5), MatrixMark(3, 0, 1, 3)],
        id="bar_width=1",
    ),
    pytest.param(
        3,
        [MatrixMark(0, 0, 6, 5), MatrixMark(9, 0, 3, 3)],
        id="bar_width=3-scales-x-and-width",
    ),
    pytest.param(
        5,
        [MatrixMark(0, 0, 10, 5), MatrixMark(15, 0, 5, 3)],
        id="bar_width=5-scales-x-and-width",
    ),
])
def test_bar_width_scales_x_and_width(bar_width, expected):
    """bar_width scales the x and width of yielded marks; height is untouched."""
    assert list(iter_bar_marks([5, 5, 0, 3], bar_width)) == expected


def test_quiet_left_offsets_x_only():
    assert list(iter_bar_marks([5, 5, 0, 3], 1, quiet_left=10)) == [
        MatrixMark(10, 0, 2, 5),
        MatrixMark(13, 0, 1, 3),
    ]


def test_quiet_top_offsets_y_only():
    assert list(iter_bar_marks([5, 0, 3], 1, quiet_top=4)) == [
        MatrixMark(0, 4, 1, 5),
        MatrixMark(2, 4, 1, 3),
    ]


def test_quiet_offsets_combine():
    assert list(iter_bar_marks([7, 7], 1, quiet_left=11, quiet_top=2)) == [
        MatrixMark(11, 2, 2, 7),
    ]
