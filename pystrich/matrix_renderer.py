"""Shared base class for 2D matrix barcode renderers.

The 2D formats (QR Code, Data Matrix) both produce a 2D module matrix and
render it identically once the matrix (with quiet zones and any
format-specific borders or handles) is in place. This module captures
that shared surface; format-specific subclasses populate :attr:`matrix`
in their ``__init__`` and override :attr:`_SYMBOL` if their ASCII
rendering needs different glyphs.
"""

from __future__ import annotations

import os
from abc import ABC
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar, Generic, TypeVar

from pystrich.colour import RGBA, Fill, resolve_pil_palette
from pystrich.dxf import DxfUnit, matrix_to_dxf
from pystrich.eps import matrix_to_eps
from pystrich.limits import check_cell_size, check_image_pixels
from pystrich.marks import MarkShape, SymbolMarks, iter_marks
from pystrich.svg import matrix_to_svg

if TYPE_CHECKING:
    from pystrich._pillow import PILImage


# Cell type. Most 2D formats use 0/1; Data Matrix additionally uses None
# during placement to mean "unset".
CellT = TypeVar("CellT", int, "int | None")


def _pixel_bytes(value: Fill) -> bytes:
    return bytes((value,) if isinstance(value, int) else value)


class Matrix2DRenderer(ABC, Generic[CellT]):
    """Common rendering surface for 2D matrix barcode formats."""

    matrix: list[list[CellT]]

    _SYMBOL: ClassVar[dict[int | None, str]] = {0: " ", 1: "X"}

    @property
    def width(self) -> int:
        """Symbol width in modules, derived from the matrix."""
        return len(self.matrix[0]) if self.matrix else 0

    @property
    def height(self) -> int:
        """Symbol height in modules, derived from the matrix."""
        return len(self.matrix)

    def _add_border(self, colour: CellT, width: int) -> None:
        """Wrap the matrix in a uniform ring, ``width`` modules thick."""
        side = [colour] * width
        blank_row = [colour] * (self.width + 2 * width)
        self.matrix = (
            [list(blank_row) for _ in range(width)]
            + [side + row + side for row in self.matrix]
            + [list(blank_row) for _ in range(width)]
        )

    def get_pilimage(
        self,
        cellsize: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> PILImage:
        """Return the matrix as a PIL image."""
        check_cell_size(cellsize, name="cell size")
        check_image_pixels(self.width * cellsize, self.height * cellsize, cellsize=cellsize)

        from pystrich._pillow import Image

        mode, dark_fill, light_fill = resolve_pil_palette(dark_hex, light_hex)
        buff = self._buffer(cellsize, dark_fill, light_fill)
        return Image.frombuffer(
            mode,
            (self.width * cellsize, self.height * cellsize),
            buff,
            "raw",
            mode,
            0,
            -1,
        )

    def write_file(
        self,
        cellsize: int,
        filename: str | os.PathLike[str],
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Write the matrix out to an image file."""
        self.get_pilimage(cellsize, dark_hex=dark_hex, light_hex=light_hex).save(filename)

    def get_imagedata(
        self,
        cellsize: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> bytes:
        """Write the matrix out as PNG to a bytestream."""
        buffer = BytesIO()
        self.get_pilimage(cellsize, dark_hex=dark_hex, light_hex=light_hex).save(buffer, "PNG")
        return buffer.getvalue()

    def _buffer(self, cellsize: int, dark_fill: Fill, light_fill: Fill) -> bytes:
        """Convert the matrix into the buffer format used by PIL."""
        pixel: dict[int | None, bytes] = {
            0: _pixel_bytes(light_fill),
            1: _pixel_bytes(dark_fill),
        }
        # PIL writes image buffers from the bottom up, so feed in rows in
        # reverse.
        return b"".join(
            b"".join([pixel[cell] * cellsize for cell in row]) * cellsize
            for row in self.matrix[::-1]
        )

    def get_ascii(self) -> str:
        """Return an ASCII-art rendering of the matrix."""
        return "\n".join("".join(self._SYMBOL[cell] for cell in row) for row in self.matrix) + "\n"

    def get_terminal_art(self, *, ansi_bg: bool = True) -> str:
        """Render the matrix using Unicode half-block characters.

        Each terminal character represents two matrix rows and one column,
        producing approximately square cells in a typical fixed-width
        font and yielding a result that is scannable on screen.

        :param ansi_bg: If ``True`` (the default), wrap each line in ANSI
            escape codes that force a white background and black
            foreground, making the symbol scannable regardless of the
            terminal's colour scheme. Set to ``False`` for plain output
            (correct only on a light-themed terminal).
        :rtype: str

        .. versionadded:: 0.12
        """
        # Top cell, bottom cell.
        blocks = {
            (True, True): "█",  # Full block
            (True, False): "▀",  # Upper half block
            (False, True): "▄",  # Lower half block
            (False, False): " ",
        }
        rows = self.matrix
        empty_row = [0] * self.width

        lines: list[str] = []
        for i in range(0, len(rows), 2):
            top = rows[i]
            bottom = rows[i + 1] if i + 1 < len(rows) else empty_row
            line = "".join(blocks[(bool(t), bool(b))] for t, b in zip(top, bottom, strict=False))
            if ansi_bg:
                # 107 = bright white background, 30 = black foreground, 0 = reset.
                line = f"\033[107;30m{line}\033[0m"
            lines.append(line)
        return "\n".join(lines) + "\n"

    def get_svg(
        self,
        cellsize: int,
        *,
        inverse: bool,
        mark_shape: MarkShape,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Return the matrix as an SVG string."""
        check_cell_size(cellsize, name="cell size")
        return matrix_to_svg(
            self.matrix,
            cellsize,
            inverse=inverse,
            mark_shape=mark_shape,
            dark_hex=dark_hex,
            light_hex=light_hex,
        )

    def write_svg_file(
        self,
        cellsize: int,
        filename: str | os.PathLike[str],
        *,
        inverse: bool,
        mark_shape: MarkShape,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Write the matrix out to an SVG file."""
        with open(filename, "w", encoding="utf-8") as f:
            f.write(
                self.get_svg(
                    cellsize,
                    inverse=inverse,
                    mark_shape=mark_shape,
                    dark_hex=dark_hex,
                    light_hex=light_hex,
                )
            )

    def get_eps(
        self,
        cellsize: int,
        *,
        inverse: bool,
        mark_shape: MarkShape,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Return the matrix as an EPS string."""
        check_cell_size(cellsize, name="cell size")
        return matrix_to_eps(
            self.matrix,
            cellsize,
            inverse=inverse,
            mark_shape=mark_shape,
            dark_hex=dark_hex,
            light_hex=light_hex,
        )

    def write_eps_file(
        self,
        cellsize: int,
        filename: str | os.PathLike[str],
        *,
        inverse: bool,
        mark_shape: MarkShape,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Write the matrix out to an EPS file."""
        with open(filename, "w", encoding="ascii") as f:
            f.write(
                self.get_eps(
                    cellsize,
                    inverse=inverse,
                    mark_shape=mark_shape,
                    dark_hex=dark_hex,
                    light_hex=light_hex,
                )
            )

    def get_dxf(
        self,
        cellsize: float,
        inverse: bool,
        units: DxfUnit | None,
        *,
        mark_shape: MarkShape,
    ) -> str:
        """Return the matrix as a DXF string."""
        check_cell_size(cellsize, name="cell size", allow_float=True)
        return matrix_to_dxf(
            self.matrix, cellsize, inverse=inverse, units=units, mark_shape=mark_shape
        )

    def get_rect_marks(
        self, *, inverse: bool = False, mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS
    ) -> SymbolMarks:
        """Return the symbol's dark cells as rectangles in module units.

        The matrix already includes the quiet zone and any finder pattern, so
        the returned :attr:`~pystrich.marks.SymbolMarks.width` and ``height``
        span the full symbol. External renderers scale the marks to their own
        coordinate system.

        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :rtype: pystrich.marks.SymbolMarks

        .. versionadded:: 0.18
        """
        marks = tuple(iter_marks(self.matrix, mark_values_when=not inverse, mark_shape=mark_shape))
        return SymbolMarks(marks, self.width, self.height)
