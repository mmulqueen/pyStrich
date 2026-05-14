"""PDF417 renderer.

PDF417 module rows are taller than they are wide -- the spec recommends
``Y >= 3X``. The module matrix is built with each codeword row already
replicated ``row_height`` times, so the underlying
:class:`Matrix2DRenderer` (which assumes square cells) produces the
right aspect ratio without further work.
"""

from __future__ import annotations

from pystrich.matrix_renderer import Matrix2DRenderer

PDF417_DEFAULT_QUIET_ZONE: int = 2
"""Minimum quiet zone width: two modules on every side."""


class PDF417Renderer(Matrix2DRenderer[int]):
    """Render a pre-populated PDF417 module matrix.

    The matrix is the 0/1 module grid produced by :func:`layout.build_module_matrix`,
    where ``1`` marks a bar module and ``0`` marks a space. The renderer wraps
    the matrix in a quiet zone and delegates to :class:`Matrix2DRenderer` for
    PNG, SVG, EPS, ASCII, terminal and DXF output.

    :param row_height: How many matrix rows the encoder packed per codeword
        row. The terminal-art override uses this to down-sample back to one
        line per codeword row.
    """

    row_height: int
    quiet_zone: int

    def __init__(
        self,
        matrix: list[list[int]],
        *,
        quiet_zone: int = PDF417_DEFAULT_QUIET_ZONE,
        row_height: int = 1,
    ) -> None:
        self.matrix = matrix
        self.height = len(matrix)
        self.width = len(matrix[0]) if matrix else 0
        self.row_height = row_height
        self.quiet_zone = quiet_zone
        if quiet_zone > 0:
            self._add_quiet_zone(quiet_zone)

    def _add_quiet_zone(self, width: int) -> None:
        """Wrap the matrix in a white border ``width`` modules thick on every side."""
        blank_row = [0] * (self.width + 2 * width)
        side = [0] * width
        self.matrix = (
            [list(blank_row) for _ in range(width)]
            + [side + row + side for row in self.matrix]
            + [list(blank_row) for _ in range(width)]
        )
        self.width += 2 * width
        self.height += 2 * width

    def get_terminal_art(self, *, ansi_bg: bool = True) -> str:
        """Render the symbol using horizontal half-block characters.

        Each character represents one codeword row and two modules,
        packed via ``LEFT HALF BLOCK`` and ``RIGHT HALF BLOCK``. That
        keeps codeword-row boundaries lined up with character boundaries
        and gives an on-screen aspect close to the recommended ``Y >= 3X``.
        The vertical half-block packing inherited from
        :class:`Matrix2DRenderer` straddles codeword boundaries when
        ``row_height`` is odd; this override avoids that for PDF417.

        :param ansi_bg: If ``True`` (the default), wrap each line in
            ANSI escape codes that force a white background and black
            foreground, making the symbol scannable regardless of the
            terminal's colour scheme. Set to ``False`` for plain output
            (correct only on a light-themed terminal).
        """
        glyphs = {
            (False, False): " ",
            (False, True): "▐",
            (True, False): "▌",
            (True, True): "█",
        }
        qz = self.quiet_zone
        # Skip the quiet zone, down-sample the codeword section, then add
        # a one-line vertical breather top and bottom. The side quiet zone
        # is already embedded in each matrix row.
        codeword_rows = self.matrix[qz : self.height - qz] if qz else self.matrix
        rows = codeword_rows[:: self.row_height]
        blank = [0] * self.width
        padded = [blank, *rows, blank]
        lines: list[str] = []
        for row in padded:
            chars = []
            for i in range(0, len(row), 2):
                left = bool(row[i])
                right = bool(row[i + 1]) if i + 1 < len(row) else False
                chars.append(glyphs[(left, right)])
            line = "".join(chars)
            if ansi_bg:
                line = f"\033[107;30m{line}\033[0m"
            lines.append(line)
        return "\n".join(lines) + "\n"
