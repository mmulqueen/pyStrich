"""Direct unit tests for pystrich.svg.matrix_to_svg.

The SVG is parsed via xml.etree.ElementTree so an ill-formed document
fails fast at parse time and rect coordinates can be asserted as
NamedTuples rather than as substrings.
"""

import xml.etree.ElementTree as ET
from typing import NamedTuple

import pytest

from pystrich.svg import matrix_to_svg

SVG_NS = "http://www.w3.org/2000/svg"


class Rect(NamedTuple):
    x: int
    y: int
    width: int
    height: int


def _rect(elem: ET.Element) -> Rect:
    return Rect(
        x=int(elem.get("x", "0")),
        y=int(elem.get("y", "0")),
        width=int(elem.get("width", "0")),
        height=int(elem.get("height", "0")),
    )


def get_rects_in_group_with_fill(svg: str, fill: str) -> list[Rect]:
    """Return the rects inside the first ``<g fill={fill!r}>`` element."""
    root = ET.fromstring(svg)
    for g in root.findall(f"{{{SVG_NS}}}g"):
        if g.get("fill") == fill:
            return [_rect(r) for r in g.findall(f"{{{SVG_NS}}}rect")]
    raise AssertionError(f"No <g fill={fill!r}> found in SVG")


def get_background_rect(svg: str) -> Rect:
    """Return the direct-child ``<rect fill="#fff"/>`` (the background)."""
    root = ET.fromstring(svg)
    rect = root.find(f"{{{SVG_NS}}}rect")
    assert rect is not None, "No background rect found"
    assert rect.get("fill") == "#fff", f"Expected fill='#fff', got {rect.get('fill')!r}"
    return _rect(rect)


@pytest.mark.parametrize(
    "matrix, expected_rects",
    [
        pytest.param(
            [[1, 1, 0, 1, 1]],
            [Rect(0, 0, 2, 1), Rect(3, 0, 2, 1)],
            id="merge-adjacent-cells",
        ),
        pytest.param(
            [[1, 1, 1]],
            [Rect(0, 0, 3, 1)],
            id="run-terminates-at-end-of-row",
        ),
        pytest.param(
            [[1, 1], [1, 1]],
            [Rect(0, 0, 2, 1), Rect(0, 1, 2, 1)],
            id="rows-are-independent",
        ),
        pytest.param(
            [[1, 0, 1]],
            [Rect(0, 0, 1, 1), Rect(2, 0, 1, 1)],
            id="zero-as-background",
        ),
        pytest.param(
            [[1, None, 1]],
            [Rect(0, 0, 1, 1), Rect(2, 0, 1, 1)],
            id="none-as-background",
        ),
        pytest.param([[0, 0], [0, 0]], [], id="all-white"),
    ],
)
def test_foreground_rects(matrix, expected_rects):
    svg = matrix_to_svg(matrix, cellsize=5)
    assert get_rects_in_group_with_fill(svg, "#000") == expected_rects


def test_foreground_rects_omit_fill_attribute():
    """Per-rect fill is not emitted; the <g fill="#000"> wrapper provides it."""
    svg = matrix_to_svg([[1, 0, 1, 1, 0, 1]], cellsize=5)
    root = ET.fromstring(svg)
    g = next(g for g in root.findall(f"{{{SVG_NS}}}g") if g.get("fill") == "#000")
    for rect in g.findall(f"{{{SVG_NS}}}rect"):
        assert rect.get("fill") is None


def test_root_attributes():
    svg = matrix_to_svg([[0] * 3] * 4, cellsize=7)
    root = ET.fromstring(svg)
    assert root.tag == f"{{{SVG_NS}}}svg"
    assert root.get("viewBox") == "0 0 3 4"
    assert root.get("width") == "21"
    assert root.get("height") == "28"
    assert root.get("shape-rendering") == "crispEdges"


def test_background_spans_full_matrix_in_module_units():
    """The background rect tracks viewBox, not pixel dims."""
    svg = matrix_to_svg([[0] * 3] * 4, cellsize=7)
    assert get_background_rect(svg) == Rect(0, 0, 3, 4)


def test_background_drawn_before_foreground():
    """Background rect must precede the <g> so foreground stacks on top."""
    root = ET.fromstring(matrix_to_svg([[1]], cellsize=5))
    children = list(root)
    rect_idx = next(i for i, c in enumerate(children) if c.tag == f"{{{SVG_NS}}}rect")
    g_idx = next(i for i, c in enumerate(children) if c.tag == f"{{{SVG_NS}}}g")
    assert rect_idx < g_idx
