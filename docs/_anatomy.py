"""Anatomy-diagram generators for docs/{aztec,datamatrix,qrcode}.rst.

Each ``*_anatomy_svg`` builds an annotated SVG: the symbol is tinted
by region using the Okabe-Ito colour-blind-safe palette, and a key
shows the same tint overlaid on a black/white triangle swatch so the
reader sees how the colour appears on both dark and light cells.
"""

from __future__ import annotations

import re

from pystrich.aztec import AztecEncoder
from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder
from pystrich.qrcode import QRCodeEncoder

# Okabe-Ito (Wong, 2011).
_VERMILLION = "#D55E00"
_PURPLE = "#CC79A7"
_SKY_BLUE = "#56B4E9"
_ORANGE = "#E69F00"
_GREEN = "#009E73"

_TINT_OPACITY = 0.45
_CANVAS_BG = "#e8e8e8"


def _strip_svg_wrapper(svg: str, expected_size: int, label: str) -> str:
    """Return SVG inner XML and assert the root viewBox is square at ``expected_size``.

    Overlay coordinates in each anatomy generator assume a specific
    rendered symbol size. If a future encoder change picks a different
    size for the same payload, the assert fires so the overlays get
    updated rather than silently misaligning.
    """
    m = re.match(r'<svg[^>]*\bviewBox="0 0 (\d+) (\d+)"', svg)
    assert m is not None, f"{label} anatomy: expected viewBox on root <svg>"
    w, h = int(m.group(1)), int(m.group(2))
    assert (w, h) == (expected_size, expected_size), (
        f"{label} anatomy expects a {expected_size}x{expected_size} viewBox, "
        f"got {w}x{h}. Encoder geometry has changed -- pick a payload that "
        "still produces the expected size, or update the overlay coordinates."
    )
    inner = re.sub(r"^<svg[^>]*>\s*", "", svg, count=1)
    return re.sub(r"</svg>\s*$", "", inner)


def _swatch_xml(colour: str | None) -> str:
    """22x22 swatch: black/white diagonal halves, optionally tinted on top."""
    # Triangles span y=2..24 to align with the text baseline below.
    parts = [
        '<polygon points="0,2 22,2 0,24" fill="#000"/>',
        '<polygon points="22,2 22,24 0,24" fill="#fff"/>',
    ]
    if colour is not None:
        parts.append(
            f'<rect x="0" y="2" width="22" height="22" '
            f'fill="{colour}" fill-opacity="{_TINT_OPACITY}"/>'
        )
    return "".join(parts)


def _compose_anatomy_svg(
    barcode_inner: str,
    barcode_viewbox: int,
    overlays: list[str],
    key_entries: list[tuple[str, str, str | None]],
) -> str:
    """Wrap a barcode SVG and tint overlays into a final diagram with key."""
    overlay_group = f'<g opacity="{_TINT_OPACITY}">\n  ' + "\n  ".join(overlays) + "\n</g>"

    barcode_px = 410
    key_x = barcode_px + 30
    key_entry_h = 50
    total_w = key_x + 470
    total_h = max(barcode_px + 20, key_entry_h * len(key_entries) + 40)

    key_items: list[str] = []
    for i, (label, desc, colour) in enumerate(key_entries):
        y = i * key_entry_h
        key_items.append(
            f'<g transform="translate(0, {y})">'
            f"{_swatch_xml(colour)}"
            f'<text x="32" y="16" font-family="sans-serif" font-size="13" '
            f'font-weight="600" fill="#222">{label}</text>'
            f'<text x="32" y="32" font-family="sans-serif" font-size="11" '
            f'fill="#222">{desc}</text>'
            f"</g>"
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {total_w} {total_h}" width="{total_w}" '
        f'height="{total_h}" shape-rendering="crispEdges">\n'
        f'<rect width="{total_w}" height="{total_h}" fill="{_CANVAS_BG}"/>\n'
        f'<svg x="10" y="10" width="{barcode_px}" height="{barcode_px}" '
        f'viewBox="0 0 {barcode_viewbox} {barcode_viewbox}">\n'
        f"{barcode_inner}\n"
        f"{overlay_group}\n"
        f"</svg>\n"
        f'<g transform="translate({key_x}, 30)">\n' + "\n".join(key_items) + "\n</g>\n"
        "</svg>\n"
    )


def aztec_anatomy_svg() -> str:
    """Annotated full-range 5-layer Aztec Code (37x37, 41x41 viewBox)."""
    qz = 2
    sym = 37
    encoder = AztecEncoder(
        "Aztec Code anatomy",
        symbol_kind="full",
        layers=5,
        quiet_zone=qz,
    )
    barcode_inner = _strip_svg_wrapper(encoder.get_svg(cellsize=1), qz + sym + qz, "Aztec")

    core_start = 11
    core_size = 15

    def mod(rc: int) -> int:
        return qz + rc

    overlays: list[str] = []

    # Data layers: four strips around the central 15x15 core.
    above_h = core_start
    below_y = mod(core_start + core_size)
    below_h = sym - (core_start + core_size)
    overlays += [
        f'<rect x="{mod(0)}" y="{mod(0)}" width="{sym}" height="{above_h}" fill="{_GREEN}"/>',
        f'<rect x="{mod(0)}" y="{below_y}" width="{sym}" height="{below_h}" fill="{_GREEN}"/>',
        f'<rect x="{mod(0)}" y="{mod(core_start)}" width="{core_start}" '
        f'height="{core_size}" fill="{_GREEN}"/>',
        f'<rect x="{mod(core_start + core_size)}" y="{mod(core_start)}" '
        f'width="{below_h}" height="{core_size}" fill="{_GREEN}"/>',
    ]

    # Reference grid: cells on rows/cols 2 and 34 of the symbol.
    overlays += [
        f'<rect x="{mod(0)}" y="{mod(2)}" width="{sym}" height="1" fill="{_ORANGE}"/>',
        f'<rect x="{mod(0)}" y="{mod(34)}" width="{sym}" height="1" fill="{_ORANGE}"/>',
        f'<rect x="{mod(2)}" y="{mod(0)}" width="1" height="{sym}" fill="{_ORANGE}"/>',
        f'<rect x="{mod(34)}" y="{mod(0)}" width="1" height="{sym}" fill="{_ORANGE}"/>',
    ]

    # Mode message: 1-cell perimeter of the 15x15 core.
    mcs = mod(core_start)
    overlays += [
        f'<rect x="{mcs}" y="{mcs}" width="{core_size}" height="1" fill="{_SKY_BLUE}"/>',
        f'<rect x="{mcs}" y="{mcs + core_size - 1}" width="{core_size}" '
        f'height="1" fill="{_SKY_BLUE}"/>',
        f'<rect x="{mcs}" y="{mcs}" width="1" height="{core_size}" fill="{_SKY_BLUE}"/>',
        f'<rect x="{mcs + core_size - 1}" y="{mcs}" width="1" '
        f'height="{core_size}" fill="{_SKY_BLUE}"/>',
    ]

    # Bullseye: inner 13x13 within the core.
    overlays.append(
        f'<rect x="{mod(core_start + 1)}" y="{mod(core_start + 1)}" '
        f'width="13" height="13" fill="{_VERMILLION}"/>'
    )

    # Orientation marks: L-shaped 3-cell group at each core corner.
    c0 = mod(core_start)
    c1 = mod(core_start + 1)
    cn = mod(core_start + core_size - 1)
    cnm1 = mod(core_start + core_size - 2)
    for x, y in [
        (c0, c0),
        (c1, c0),
        (c0, c1),
        (cn, c0),
        (cnm1, c0),
        (cn, c1),
        (c0, cn),
        (c1, cn),
        (c0, cnm1),
        (cn, cn),
        (cnm1, cn),
        (cn, cnm1),
    ]:
        overlays.append(f'<rect x="{x}" y="{y}" width="1" height="1" fill="{_PURPLE}"/>')

    key = [
        ("Bullseye finder", "Central concentric squares; scanners lock onto this.", _VERMILLION),
        ("Orientation marks", "Asymmetric corners encoding which way is up.", _PURPLE),
        ("Mode message", "Layer count and codeword count around the core.", _SKY_BLUE),
        ("Reference grid", "Alignment strips through full-range symbols.", _ORANGE),
        ("Data layers", "Concentric rings of payload + Reed-Solomon error correction.", _GREEN),
        ("Quiet zone", "White margin (2 modules by default; not required by spec).", None),
    ]
    return _compose_anatomy_svg(barcode_inner, qz + sym + qz, overlays, key)


def datamatrix_anatomy_svg() -> str:
    """Annotated 36x36 ECC200 Data Matrix (2x2 regions of 16x16, 40x40 viewBox)."""
    qz = 2
    region_outer = 18  # 16 data + 1 L + 1 timing
    expected_size = qz + 2 * region_outer + qz  # 40

    payload = "Data Matrix anatomy: https://www.method-b.uk/pyStrich/docs/datamatrix.html"
    encoder = DataMatrixEncoder(DataMatrixData(payload, encoding="ascii"), quiet_zone=qz)
    assert encoder.regions == 2, (
        f"Data Matrix anatomy expects a 2x2-region symbol, got regions={encoder.regions}. "
        "Pick a payload that still encodes to a 36x36 symbol."
    )
    barcode_inner = _strip_svg_wrapper(encoder.get_svg(cellsize=1), expected_size, "Data Matrix")

    region_origins_xy = [
        (qz + xi * region_outer, qz + yi * region_outer) for xi in (0, 1) for yi in (0, 1)
    ]

    overlays: list[str] = []

    # Data area: cover the whole interior, then overpaint L/timing on top.
    overlays.append(
        f'<rect x="{qz}" y="{qz}" width="{2 * region_outer}" '
        f'height="{2 * region_outer}" fill="{_GREEN}"/>'
    )

    # Solid L finder: left column and bottom row of each region.
    for x0, y0 in region_origins_xy:
        x_left = x0
        y_bottom = y0 + region_outer - 1
        overlays.append(
            f'<rect x="{x_left}" y="{y0}" width="1" height="{region_outer}" fill="{_VERMILLION}"/>'
        )
        overlays.append(
            f'<rect x="{x0}" y="{y_bottom}" width="{region_outer}" height="1" '
            f'fill="{_VERMILLION}"/>'
        )

    # Timing pattern: top row and right column of each region.
    for x0, y0 in region_origins_xy:
        y_top = y0
        x_right = x0 + region_outer - 1
        overlays.append(
            f'<rect x="{x0}" y="{y_top}" width="{region_outer}" height="1" fill="{_SKY_BLUE}"/>'
        )
        overlays.append(
            f'<rect x="{x_right}" y="{y0}" width="1" height="{region_outer}" fill="{_SKY_BLUE}"/>'
        )

    key = [
        (
            "Solid L finder",
            "Two solid edges per region; defines size and orientation.",
            _VERMILLION,
        ),
        (
            "Timing pattern",
            "Alternating cells on the opposite two edges of each region.",
            _SKY_BLUE,
        ),
        ("Data area", "Codewords (payload + Reed-Solomon error correction).", _GREEN),
        ("Quiet zone", "White margin (2 modules by default; 1 module is the spec minimum).", None),
    ]
    return _compose_anatomy_svg(barcode_inner, expected_size, overlays, key)


def qrcode_anatomy_svg() -> str:
    """Annotated Version-5 QR Code (37x37 matrix, 45x45 viewBox with 4-module quiet zone)."""
    qz = 4
    sym = 37  # Version 5
    payload = "QR Code anatomy: https://www.method-b.uk/pyStrich/docs/qrcode.html"
    encoder = QRCodeEncoder(payload)
    barcode_inner = _strip_svg_wrapper(encoder.get_svg(cellsize=1), qz + sym + qz, "QR Code")

    def mod(rc: int) -> int:
        return qz + rc

    overlays: list[str] = []

    # Data + error correction: covers the symbol interior, overpainted below.
    overlays.append(f'<rect x="{qz}" y="{qz}" width="{sym}" height="{sym}" fill="{_GREEN}"/>')

    # Timing patterns: row 6 and column 6, between the three finders.
    overlays.append(
        f'<rect x="{mod(0)}" y="{mod(6)}" width="{sym}" height="1" fill="{_SKY_BLUE}"/>'
    )
    overlays.append(
        f'<rect x="{mod(6)}" y="{mod(0)}" width="1" height="{sym}" fill="{_SKY_BLUE}"/>'
    )

    # Alignment pattern (v5): 5x5 centred at module (30, 30).
    overlays.append(f'<rect x="{mod(28)}" y="{mod(28)}" width="5" height="5" fill="{_ORANGE}"/>')

    # Position detection patterns: 7x7 at three corners.
    finder_origins = [(0, 0), (sym - 7, 0), (0, sym - 7)]
    for c, r in finder_origins:
        overlays.append(
            f'<rect x="{mod(c)}" y="{mod(r)}" width="7" height="7" fill="{_VERMILLION}"/>'
        )

    # Separators: 1-module strip on the interior edges of each finder.
    # Top-left finder: row 7 cols 0-7 and col 7 rows 0-7.
    overlays += [
        f'<rect x="{mod(0)}" y="{mod(7)}" width="8" height="1" fill="{_PURPLE}"/>',
        f'<rect x="{mod(7)}" y="{mod(0)}" width="1" height="8" fill="{_PURPLE}"/>',
        # Top-right finder: row 7 cols sym-8..sym-1 and col sym-8 rows 0-7.
        f'<rect x="{mod(sym - 8)}" y="{mod(7)}" width="8" height="1" fill="{_PURPLE}"/>',
        f'<rect x="{mod(sym - 8)}" y="{mod(0)}" width="1" height="8" fill="{_PURPLE}"/>',
        # Bottom-left finder: row sym-8 cols 0-7 and col 7 rows sym-8..sym-1.
        f'<rect x="{mod(0)}" y="{mod(sym - 8)}" width="8" height="1" fill="{_PURPLE}"/>',
        f'<rect x="{mod(7)}" y="{mod(sym - 8)}" width="1" height="8" fill="{_PURPLE}"/>',
    ]

    key = [
        (
            "Position detection patterns",
            "Three corner squares; scanners use them to locate and align the symbol.",
            _VERMILLION,
        ),
        (
            "Separators",
            "One-module strip isolating each finder from the data area.",
            _PURPLE,
        ),
        (
            "Timing patterns",
            "Alternating cells running between the finders; fix the module grid.",
            _SKY_BLUE,
        ),
        (
            "Alignment pattern",
            "Smaller square in larger symbols; corrects for projective distortion.",
            _ORANGE,
        ),
        (
            "Data and error correction",
            "Masked codewords (payload + Reed-Solomon) and format-info bits.",
            _GREEN,
        ),
        (
            "Quiet zone",
            "White margin (4 modules per spec).",
            None,
        ),
    ]
    return _compose_anatomy_svg(barcode_inner, qz + sym + qz, overlays, key)
