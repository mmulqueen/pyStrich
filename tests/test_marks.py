"""Direct unit tests for pystrich.marks.iter_bar_marks and the get_rect_marks() surface."""

from xml.etree import ElementTree

import pytest

from pystrich.aztec import AztecEncoder
from pystrich.code128 import Code128Encoder
from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder
from pystrich.ean13 import EAN13Encoder
from pystrich.itf import ITF14Encoder, ITFEncoder
from pystrich.marks import SymbolMarks, iter_bar_marks
from pystrich.pdf417 import PDF417Encoder
from pystrich.qrcode import QRCodeEncoder


@pytest.mark.parametrize(
    "heights, expected",
    [
        pytest.param([], [], id="empty"),
        pytest.param([0, 0, 0], [], id="all-gaps"),
        pytest.param([5], [(0, 0, 1, 5)], id="single-bar"),
        pytest.param(
            [5, 5, 5],
            [(0, 0, 3, 5)],
            id="merge-equal-heights",
        ),
        pytest.param(
            [5, 3],
            [(0, 0, 1, 5), (1, 0, 1, 3)],
            id="adjacent-different-heights-do-not-merge",
        ),
        pytest.param(
            [0, 5, 5, 0, 3, 3, 3, 0],
            [(1, 0, 2, 5), (4, 0, 3, 3)],
            id="gaps-terminate-runs",
        ),
        pytest.param(
            [5, 5],
            [(0, 0, 2, 5)],
            id="run-terminates-at-end",
        ),
        pytest.param(
            [5, 3, 3, 5],
            [
                (0, 0, 1, 5),
                (1, 0, 2, 3),
                (3, 0, 1, 5),
            ],
            id="height-changes-without-gap",
        ),
    ],
)
def test_iter_bar_marks_runs(heights, expected):
    """At bar_width=1, the column index equals the pixel x coordinate."""
    assert list(iter_bar_marks(heights, 1)) == expected


@pytest.mark.parametrize(
    "bar_width, expected",
    [
        pytest.param(
            1,
            [(0, 0, 2, 5), (3, 0, 1, 3)],
            id="bar_width=1",
        ),
        pytest.param(
            3,
            [(0, 0, 6, 5), (9, 0, 3, 3)],
            id="bar_width=3-scales-x-and-width",
        ),
        pytest.param(
            5,
            [(0, 0, 10, 5), (15, 0, 5, 3)],
            id="bar_width=5-scales-x-and-width",
        ),
    ],
)
def test_bar_width_scales_x_and_width(bar_width, expected):
    """bar_width scales the x and width of yielded marks; height is untouched."""
    assert list(iter_bar_marks([5, 5, 0, 3], bar_width)) == expected


def test_quiet_left_offsets_x_only():
    assert list(iter_bar_marks([5, 5, 0, 3], 1, quiet_left=10)) == [
        (10, 0, 2, 5),
        (13, 0, 1, 3),
    ]


def test_quiet_top_offsets_y_only():
    assert list(iter_bar_marks([5, 0, 3], 1, quiet_top=4)) == [
        (0, 4, 1, 5),
        (2, 4, 1, 3),
    ]


def test_quiet_offsets_combine():
    assert list(iter_bar_marks([7, 7], 1, quiet_left=11, quiet_top=2)) == [
        (11, 2, 2, 7),
    ]


@pytest.mark.parametrize(
    "make_encoder",
    [
        pytest.param(
            lambda: DataMatrixEncoder(DataMatrixData("HELLO", auto_encoding=True)),
            id="datamatrix",
        ),
        pytest.param(lambda: QRCodeEncoder("HELLO"), id="qrcode"),
        pytest.param(lambda: AztecEncoder("HELLO"), id="aztec"),
        pytest.param(lambda: PDF417Encoder("HELLO"), id="pdf417"),
        pytest.param(lambda: Code128Encoder("HELLO"), id="code128"),
        pytest.param(lambda: EAN13Encoder("5050070007664"), id="ean13"),
        pytest.param(lambda: ITF14Encoder("1540141453698"), id="itf14"),
    ],
)
def test_get_rect_marks_fit_within_extent(make_encoder):
    """Every symbology returns non-empty marks that fit inside its extent."""
    symbol = make_encoder().get_rect_marks()
    assert isinstance(symbol, SymbolMarks)
    assert symbol.marks
    assert symbol.width > 0
    assert symbol.height > 0
    for x, y, width, height in symbol.marks:
        assert 0 <= x and x + width <= symbol.width
        assert 0 <= y and y + height <= symbol.height


def test_ean13_guard_bars_are_taller_than_data_bars():
    symbol = EAN13Encoder("5050070007664").get_rect_marks()
    assert len({height for _, _, _, height in symbol.marks}) >= 2


def test_itf14_draws_a_bearer_frame_absent_from_plain_itf():
    """The bearer's full-width rules only appear for ITF-14."""
    itf14 = ITF14Encoder("1540141453698").get_rect_marks()
    plain = ITFEncoder("1234567890").get_rect_marks()
    assert any(width == itf14.width for _, _, width, _ in itf14.marks)
    assert not any(width == plain.width for _, _, width, _ in plain.marks)


@pytest.mark.parametrize("options", [{}, {"show_label": False}])
def test_1d_extent_matches_svg_canvas(options):
    """The marks span the same canvas SVG draws, with or without a label."""
    encoder = Code128Encoder("HELLO", options=options)
    symbol = encoder.get_rect_marks()
    view_box = ElementTree.fromstring(encoder.get_svg(1)).get("viewBox")
    assert view_box == f"0 0 {symbol.width} {symbol.height}"


def test_1d_extent_shrinks_without_label():
    labelled = Code128Encoder("HELLO").get_rect_marks()
    bare = Code128Encoder("HELLO", options={"show_label": False}).get_rect_marks()
    assert bare.height < labelled.height
    assert bare.width == labelled.width
