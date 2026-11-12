"""Direct unit tests for pystrich.svg.

The SVG is parsed via xml.etree.ElementTree so an ill-formed document
fails fast at parse time and rect coordinates can be asserted as
NamedTuples rather than as substrings.
"""

import xml.etree.ElementTree as ET
from typing import NamedTuple
from urllib.parse import unquote

import pytest

from pystrich.code39 import Code39Encoder
from pystrich.code128 import Code128Encoder
from pystrich.ean13 import EAN13Encoder
from pystrich.qrcode import QRCodeEncoder
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


BAR_ENCODERS = [
    pytest.param(lambda: EAN13Encoder("400638133393"), id="ean13"),
    pytest.param(lambda: Code128Encoder("ABC-123"), id="code128"),
    pytest.param(lambda: Code39Encoder("ABC-123"), id="code39"),
]


def ids_and_hrefs(svg: str) -> tuple[set[str], list[str]]:
    root = ET.fromstring(svg)
    ids = {i for e in root.iter() if (i := e.get("id")) is not None}
    hrefs = [e.get("href", "") for e in root.iter(f"{{{SVG_NS}}}use")]
    return ids, hrefs


@pytest.mark.parametrize("make", BAR_ENCODERS)
def test_prefix_applied_to_every_id_and_href(make):
    ids, hrefs = ids_and_hrefs(make().get_svg(id_prefix="bc1-"))
    assert ids
    assert all(i.startswith("bc1-g_") for i in ids)
    assert {h.removeprefix("#") for h in hrefs} == ids


@pytest.mark.parametrize("make", BAR_ENCODERS)
def test_prefix_changes_nothing_but_ids(make):
    enc = make()
    prefixed = enc.get_svg(id_prefix="bc1-")
    assert prefixed.replace('"bc1-g_', '"g_').replace('"#bc1-g_', '"#g_') == enc.get_svg()


def test_bar_svg_dataurl_and_save_svg_pass_prefix_through(tmp_path):
    enc = EAN13Encoder("400638133393")
    expected = enc.get_svg(id_prefix="bc1-")
    assert unquote(enc.svg_dataurl(id_prefix="bc1-").split(",", 1)[1]) == expected
    path = tmp_path / "ean13.svg"
    enc.save_svg(path, id_prefix="bc1-")
    assert path.read_text(encoding="utf-8") == expected


def test_matrix_svg_accepts_prefix_but_has_no_ids(tmp_path):
    enc = QRCodeEncoder("hello")
    svg = enc.get_svg(id_prefix="qr1-")
    assert svg == enc.get_svg()
    assert ids_and_hrefs(svg) == (set(), [])
    assert unquote(enc.svg_dataurl(id_prefix="qr1-").split(",", 1)[1]) == svg
    path = tmp_path / "qr.svg"
    enc.save_svg(path, id_prefix="qr1-")
    assert path.read_text(encoding="utf-8") == svg


@pytest.mark.parametrize("prefix", ["a", "_", "Barcode-1_", "x-"])
def test_valid_prefixes_accepted(prefix):
    EAN13Encoder("400638133393").get_svg(id_prefix=prefix)
    QRCodeEncoder("hello").get_svg(id_prefix=prefix)


@pytest.mark.parametrize(
    "prefix",
    [
        pytest.param("1a", id="leading-digit"),
        pytest.param("-a", id="leading-hyphen"),
        pytest.param("a b", id="space"),
        pytest.param('a"', id="quote"),
        pytest.param("a<", id="angle-bracket"),
        pytest.param("a.b", id="dot"),
        pytest.param("a:b", id="colon"),
        pytest.param("é", id="non-ascii"),
    ],
)
@pytest.mark.parametrize(
    "make",
    [
        pytest.param(lambda: EAN13Encoder("400638133393"), id="ean13"),
        pytest.param(lambda: QRCodeEncoder("hello"), id="qrcode"),
    ],
)
def test_invalid_prefixes_rejected(make, prefix):
    with pytest.raises(ValueError, match="id_prefix"):
        make().get_svg(id_prefix=prefix)


def test_non_str_prefix_rejected():
    with pytest.raises(TypeError):
        EAN13Encoder("400638133393").get_svg(id_prefix=1)  # type: ignore[arg-type]
