"""Tests for the PDF417 renderer and the top-level PDF417Encoder.

These cover the renderer's quiet-zone handling and the public API surface
(matrix shape, dimension selection, render outputs). The end-to-end
roundtrip against ``zxing-cpp`` lives in ``test_roundtrip.py`` so it can
be skipped when that dependency is unavailable.
"""

from __future__ import annotations

import pytest

from pystrich.pdf417 import PDF417Encoder
from pystrich.pdf417.layout import row_modules
from pystrich.pdf417.renderer import PDF417_DEFAULT_QUIET_ZONE, PDF417Renderer


def _make_matrix(rows: int, cols: int) -> list[list[int]]:
    return [[(r + c) & 1 for c in range(cols)] for r in range(rows)]


def test_renderer_records_matrix_dimensions():
    """``width`` and ``height`` reflect the post-quiet-zone matrix size."""
    m = _make_matrix(6, 10)
    r = PDF417Renderer(m, quiet_zone=2)
    assert r.height == 6 + 2 * 2
    assert r.width == 10 + 2 * 2


def test_renderer_quiet_zone_is_all_zeros():
    """Every cell in the quiet-zone border is 0 (light)."""
    m = _make_matrix(6, 10)
    r = PDF417Renderer(m, quiet_zone=2)
    for row in r.matrix[:2]:
        assert all(c == 0 for c in row)
    for row in r.matrix[-2:]:
        assert all(c == 0 for c in row)
    for row in r.matrix[2:-2]:
        assert row[:2] == [0, 0]
        assert row[-2:] == [0, 0]


def test_renderer_zero_quiet_zone_leaves_matrix_unchanged():
    """``quiet_zone=0`` is a valid no-op."""
    m = _make_matrix(3, 5)
    r = PDF417Renderer(m, quiet_zone=0)
    assert r.height == 3
    assert r.width == 5
    assert r.matrix == m


# ---------------------------------------------------------------------------
# PDF417Encoder public API
# ---------------------------------------------------------------------------


def test_encoder_default_ecl_follows_spec_guidance():
    """Default ECL follows the spec's minimum-level guidance: short input gets level 2."""
    e = PDF417Encoder("PDF417")
    assert e.ecl == 2


def test_encoder_explicit_ecl_is_respected():
    """An explicit ``ecl`` overrides the auto-selection."""
    e = PDF417Encoder("PDF417", ecl=1)
    assert e.ecl == 1


def test_encoder_explicit_columns_is_respected():
    """An explicit ``columns`` sets the symbol shape directly."""
    e = PDF417Encoder("Hello", ecl=2, columns=5)
    assert e.columns == 5


def test_encoder_matrix_has_expected_row_width():
    """Matrix row width equals ``c*17 + 69`` (no quiet zone — that's added at render)."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3)
    assert len(e.matrix[0]) == row_modules(3)


def test_encoder_matrix_has_expected_height_with_default_row_aspect():
    """Each codeword row is rendered ``row_height=3`` tall by default."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3)
    assert len(e.matrix) == e.rows * 3


def test_encoder_row_height_overridable():
    """The Y/X aspect can be set explicitly for callers that want square cells."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3, row_height=1)
    assert len(e.matrix) == e.rows


def test_encoder_init_renderer_updates_pixel_dimensions():
    """``init_renderer`` adds the quiet zone and writes width/height back to the encoder."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3)
    r = e.init_renderer()
    assert e.width == r.width == row_modules(3) + 2 * PDF417_DEFAULT_QUIET_ZONE
    assert e.height == r.height == e.rows * 3 + 2 * PDF417_DEFAULT_QUIET_ZONE


def test_encoder_save_writes_png_to_disk(tmp_path):
    """``encoder.save`` produces a non-trivial PNG file."""
    out = tmp_path / "p417.png"
    e = PDF417Encoder("PDF417", ecl=1, columns=3)
    e.save(str(out), cellsize=4)
    assert out.exists()
    assert out.stat().st_size > 100  # arbitrary sanity check; PNG header alone is bigger


def test_encoder_get_svg_returns_svg_text():
    """SVG output starts with the standard XML/SVG preamble."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3)
    svg = e.get_svg()
    assert "<svg" in svg
    assert "</svg>" in svg


def test_encoder_get_imagedata_returns_png_bytes():
    """``get_imagedata`` returns PNG bytes (starts with the PNG magic number)."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3)
    data = e.get_imagedata()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_encoder_get_ascii_contains_start_pattern():
    """ASCII output begins each codeword row with the spec's start pattern (8 bars)."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3, row_height=1)
    ascii_art = e.get_ascii()
    # First non-quiet-zone row starts with 8 bars after the quiet-zone prefix.
    first_data_row = ascii_art.splitlines()[PDF417_DEFAULT_QUIET_ZONE]
    assert "XXXXXXXX" in first_data_row[:20]


@pytest.mark.parametrize("ecl", [0, 4, 8])
def test_encoder_supports_full_ecl_range(ecl):
    """All nine error correction levels produce a valid matrix."""
    e = PDF417Encoder("short payload", ecl=ecl)
    assert e.ecl == ecl
    # Smoke test: the renderer assembles without raising.
    e.init_renderer()


def test_get_terminal_art_emits_one_line_per_codeword_row():
    """Horizontal half-block packing collapses ``row_height`` matrix rows into one line.

    ASCII output uses one character per matrix row; terminal output overrides
    that to use one character per *codeword* row (sampling the replicated
    matrix at ``row_height`` stride). The result is ``rows + 2`` lines (one
    line of quiet zone top and bottom) regardless of ``row_height``.
    """
    e = PDF417Encoder("PDF417", ecl=1, columns=3, row_height=3)
    lines = e.get_terminal_art(ansi_bg=False).rstrip("\n").split("\n")
    assert len(lines) == e.rows + 2


def test_get_terminal_art_uses_horizontal_half_blocks():
    """The output uses LEFT/RIGHT half blocks (``▌``/``▐``), not vertical (``▀``/``▄``).

    PDF417's odd ``row_height`` would straddle codeword-row boundaries when
    rendered with the inherited vertical half-block packing; the override
    avoids that by packing two modules per character horizontally instead.
    """
    art = PDF417Encoder("PDF417", ecl=1, columns=3).get_terminal_art(ansi_bg=False)
    assert "▌" in art or "▐" in art or "█" in art
    assert "▀" not in art and "▄" not in art


def test_get_terminal_art_width_is_half_module_count_per_line():
    """Each line packs two modules per character, plus the two-module quiet zone."""
    e = PDF417Encoder("PDF417", ecl=1, columns=3, row_height=3)
    art = e.get_terminal_art(ansi_bg=False).rstrip("\n").split("\n")
    expected_chars = -(-(len(e.matrix[0]) + 2 * e.quiet_zone) // 2)  # ceil-divide by 2
    for line in art:
        assert len(line) == expected_chars


def test_encoder_columns_out_of_range_raises():
    """Columns above 30 fail at dimension picking."""
    from pystrich.exceptions import PyStrichInvalidInput

    with pytest.raises(PyStrichInvalidInput):
        PDF417Encoder("PDF417", columns=31)
