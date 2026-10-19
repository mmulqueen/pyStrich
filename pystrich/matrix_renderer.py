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
from typing import TYPE_CHECKING, ClassVar, Generic, Literal, TypeVar, get_args

from pystrich.colour import RGBA, pil_mode, resolve_colours
from pystrich.dxf import DxfUnit, matrix_to_dxf
from pystrich.eps import matrix_to_eps
from pystrich.exceptions import PyStrichInvalidOption
from pystrich.limits import check_cell_size, check_image_pixels
from pystrich.marks import MarkShape, SymbolMarks, iter_marks
from pystrich.svg import matrix_to_svg

if TYPE_CHECKING:
    from pystrich._pillow import PILImage


# Cell type. Most 2D formats use 0/1; Data Matrix additionally uses None
# during placement to mean "unset".
CellT = TypeVar("CellT", int, "int | None")

ImageDepth = Literal["full", "bilevel"]


def _grey_image(modules: bytes, size: tuple[int, int], dark: int, light: int) -> PILImage:
    """Return 0/1 ``modules`` as an ``"L"`` image, one pixel per module."""
    from pystrich._pillow import Image

    return Image.frombytes("L", size, modules.translate(bytes((light, dark)) + bytes(254)))


def _palette_image(
    modules: bytes, size: tuple[int, int], dark: RGBA, light: RGBA, *, alpha: bool
) -> PILImage:
    """Return 0/1 ``modules`` as a ``"P"`` image on a light/dark palette, one pixel per module."""
    from pystrich._pillow import Image

    def entry(colour: RGBA) -> tuple[int, ...]:
        rgb = (colour.r, colour.g, colour.b)
        return (*rgb, colour.a) if alpha else rgb

    image = Image.frombytes("P", size, modules)
    image.putpalette(bytes(entry(light) + entry(dark)), "RGBA" if alpha else "RGB")
    return image


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
        depth: ImageDepth = "full",
    ) -> PILImage:
        """Return the matrix as a PIL image."""
        if depth not in get_args(ImageDepth):
            raise PyStrichInvalidOption(
                f"depth must be one of {get_args(ImageDepth)}, got {depth!r}"
            )
        check_cell_size(cellsize, name="cell size")
        check_image_pixels(self.width * cellsize, self.height * cellsize, cellsize=cellsize)

        dark, light = resolve_colours(dark_hex, light_hex)
        return self._scaled_image(cellsize, dark, light, depth=depth)

    def _scaled_image(
        self, cellsize: int, dark: RGBA, light: RGBA, *, depth: ImageDepth
    ) -> PILImage:
        """Render the matrix at ``cellsize`` pixels per module.

        One pixel per module, upscaled by nearest-neighbour: Pillow does the
        per-pixel work, so the Python-side cost scales with modules, not pixels.

        With ``depth="bilevel"`` the image has one bit per pixel: ``"1"`` for
        black and white, otherwise a two-entry ``"P"`` palette. Pillow writes
        either as a bit-depth-1 PNG.
        """
        from pystrich._pillow import Image

        modules = b"".join(bytes(row) for row in self.matrix)  # type: ignore[arg-type]
        size = (self.width, self.height)
        scaled = (self.width * cellsize, self.height * cellsize)
        mode = pil_mode(dark, light)
        alpha = mode == "RGBA"
        if depth == "bilevel" and mode == "L" and {dark.r, light.r} <= {0, 255}:
            image = _grey_image(modules, size, dark.r, light.r).convert(
                "1", dither=Image.Dither.NONE
            )
        elif depth == "bilevel":
            image = _palette_image(modules, size, dark, light, alpha=alpha)
        elif mode == "L":
            image = _grey_image(modules, size, dark.r, light.r)
        else:
            # Converting before upscaling touches modules rather than pixels.
            image = _palette_image(modules, size, dark, light, alpha=alpha).convert(mode)
        return image.resize(scaled, Image.Resampling.NEAREST)

    def write_file(
        self,
        cellsize: int,
        filename: str | os.PathLike[str],
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
        depth: ImageDepth = "bilevel",
    ) -> None:
        """Write the matrix out as a PNG file, as :meth:`get_imagedata` produces it."""
        image = self.get_pilimage(cellsize, dark_hex=dark_hex, light_hex=light_hex, depth=depth)
        image.save(filename, "PNG")

    def get_imagedata(
        self,
        cellsize: int,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
        depth: ImageDepth = "bilevel",
    ) -> bytes:
        """Write the matrix out as PNG to a bytestream."""
        buffer = BytesIO()
        image = self.get_pilimage(cellsize, dark_hex=dark_hex, light_hex=light_hex, depth=depth)
        image.save(buffer, "PNG")
        return buffer.getvalue()

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
