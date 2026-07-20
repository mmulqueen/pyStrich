"""Shared base class for 2D matrix barcode encoders.

Encoder subclasses (:class:`pystrich.qrcode.QRCodeEncoder`,
:class:`pystrich.datamatrix.DataMatrixEncoder`) lay their input out into
a matrix and supply :meth:`Matrix2DEncoder.init_renderer` that constructs
the matching :class:`pystrich.matrix_renderer.Matrix2DRenderer`. Render
entry points (PNG, SVG, EPS, DXF, ASCII) live on the base.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic

from pystrich._dataurl import png_to_data_url, svg_to_data_url
from pystrich.dxf import DxfUnit
from pystrich.marks import MarkShape, SymbolMarks
from pystrich.matrix_renderer import CellT, Matrix2DRenderer

if TYPE_CHECKING:
    from pystrich._pillow import PILImage
    from pystrich.colour import RGBA


class Matrix2DEncoder(ABC, Generic[CellT]):
    """Common encoder surface for 2D matrix barcode formats."""

    matrix: list[list[CellT]]
    width: int
    height: int

    @abstractmethod
    def init_renderer(self) -> Matrix2DRenderer[CellT]:
        """Construct a :class:`Matrix2DRenderer` for the encoded matrix.

        Implementations are expected to update :attr:`width` and
        :attr:`height` with the renderer's pixel dimensions before
        returning.
        """

    def save(
        self,
        filename: str | os.PathLike[str],
        cellsize: int = 5,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the symbol as a PNG. Pass a ``.png`` filename.

        :param filename: PNG output path.
        :param cellsize: Side length in pixels of one module.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        self.init_renderer().write_file(cellsize, filename, dark_hex=dark_hex, light_hex=light_hex)

    def get_imagedata(
        self,
        cellsize: int = 5,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> bytes:
        """Render the symbol and return PNG bytes.

        :param cellsize: Side length in pixels of one module.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :returns: PNG-encoded image data.
        :rtype: bytes

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return self.init_renderer().get_imagedata(cellsize, dark_hex=dark_hex, light_hex=light_hex)

    def png_dataurl(
        self,
        cellsize: int = 5,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the symbol and return a PNG ``data:`` URL string.

        :param cellsize: Side length in pixels of one module.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :rtype: str

        .. versionadded:: 0.15

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return png_to_data_url(self.get_imagedata(cellsize, dark_hex=dark_hex, light_hex=light_hex))

    def get_pilimage(
        self,
        cellsize: int = 5,
        *,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> PILImage:
        """Render the symbol and return a Pillow image.

        :param cellsize: Side length in pixels of one module.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :returns: The rendered symbol.
        :rtype: PIL.Image.Image

        .. versionadded:: 0.11

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return self.init_renderer().get_pilimage(cellsize, dark_hex=dark_hex, light_hex=light_hex)

    def get_svg(
        self,
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the symbol and return SVG markup.

        :param cellsize: Side length in user units of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :rtype: str

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return self.init_renderer().get_svg(
            cellsize,
            inverse=inverse,
            mark_shape=mark_shape,
            dark_hex=dark_hex,
            light_hex=light_hex,
        )

    def svg_dataurl(
        self,
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the symbol and return an SVG ``data:`` URL string.

        :param cellsize: Side length in user units of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.
        :rtype: str

        .. versionadded:: 0.15

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return svg_to_data_url(
            self.get_svg(
                cellsize,
                inverse=inverse,
                mark_shape=mark_shape,
                dark_hex=dark_hex,
                light_hex=light_hex,
            )
        )

    def save_svg(
        self,
        filename: str | os.PathLike[str],
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the symbol as an SVG file. Pass a ``.svg`` filename.

        :param filename: SVG output path.
        :param cellsize: Side length in user units of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to white.

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        self.init_renderer().write_svg_file(
            cellsize,
            filename,
            inverse=inverse,
            mark_shape=mark_shape,
            dark_hex=dark_hex,
            light_hex=light_hex,
        )

    def get_eps(
        self,
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> str:
        """Render the symbol and return EPS markup.

        :param cellsize: Side length in PostScript points of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``, opaque. Defaults to white.
        :rtype: str

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        return self.init_renderer().get_eps(
            cellsize,
            inverse=inverse,
            mark_shape=mark_shape,
            dark_hex=dark_hex,
            light_hex=light_hex,
        )

    def save_eps(
        self,
        filename: str | os.PathLike[str],
        cellsize: int = 5,
        *,
        inverse: bool = False,
        mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS,
        dark_hex: str | RGBA | None = None,
        light_hex: str | RGBA | None = None,
    ) -> None:
        """Save the symbol as an EPS file. Pass an ``.eps`` filename.

        :param filename: EPS output path.
        :param cellsize: Side length in PostScript points of one module.
        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :param dark_hex: Dark-module colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``. Defaults to black.
        :param light_hex: Background colour as a 3-, 6- or 8-digit hex string or an
            ``RGBA``, opaque. Defaults to white.

        .. versionadded:: 0.12

        .. versionchanged:: 0.16
            Added ``dark_hex`` and ``light_hex``.
        """
        self.init_renderer().write_eps_file(
            cellsize,
            filename,
            inverse=inverse,
            mark_shape=mark_shape,
            dark_hex=dark_hex,
            light_hex=light_hex,
        )

    def get_ascii(self) -> str:
        """Return an ASCII-art rendering of the symbol.

        :rtype: str
        """
        return self.init_renderer().get_ascii()

    def get_terminal_art(self, *, ansi_bg: bool = True) -> str:
        """Render the symbol using Unicode half-block characters for terminals.

        Each character represents two matrix rows and one column, producing
        approximately square cells in a typical fixed-width font and yielding
        a result that is scannable on screen.

        :param ansi_bg: If ``True`` (the default), wrap each line in ANSI
            escape codes that force a white background and black foreground,
            making the symbol scannable regardless of the terminal's colour
            scheme. Set to ``False`` for plain output (correct only on a
            light-themed terminal).
        :rtype: str

        .. versionadded:: 0.12
        """
        return self.init_renderer().get_terminal_art(ansi_bg=ansi_bg)

    def get_dxf(
        self,
        cellsize: float = 1.0,
        inverse: bool = True,
        units: DxfUnit | None = "mm",
        *,
        mark_shape: MarkShape = MarkShape.SQUARE_CELLS,
    ) -> str:
        """Return a DXF (CAD) representation of the symbol.

        :param cellsize: Side length of one module in ``units``.
        :param inverse: If ``True`` (the default), light modules are drawn as
            filled cells. If ``False``, dark modules are drawn, matching the
            normal appearance of the symbol.
        :param units: One of ``"in"``, ``"ft"``, ``"mi"``, ``"mm"``, ``"cm"``
            or ``"m"``, or ``None`` for Unspecified (``$INSUNITS=0``).
        :param mark_shape: How matched cells are grouped and drawn.
        :rtype: str

        .. versionadded:: 0.9

        .. versionchanged:: 0.12
            ``units`` now supports ``"in"``, ``"ft"``, ``"mi"``, ``"cm"``,
            ``"m"`` and ``None`` (Unspecified); previously any value other
            than ``"mm"`` was silently treated as unspecified.
        """
        return self.init_renderer().get_dxf(cellsize, inverse, units, mark_shape=mark_shape)

    def get_rect_marks(
        self, *, inverse: bool = False, mark_shape: MarkShape = MarkShape.HORIZONTAL_RUNS
    ) -> SymbolMarks:
        """Return the symbol's dark cells as rectangles in module units.

        :param inverse: If ``True``, mark the light cells instead of the dark ones.
        :param mark_shape: How matched cells are grouped and drawn.
        :rtype: pystrich.marks.SymbolMarks

        .. versionadded:: 0.18
        """
        return self.init_renderer().get_rect_marks(inverse=inverse, mark_shape=mark_shape)
