"""Aztec Code renderer."""

from __future__ import annotations

from pystrich.matrix_renderer import Matrix2DRenderer

AZTEC_DEFAULT_QUIET_ZONE: int = 2
"""Default Aztec quiet zone width in modules.

Aztec Code does not require a quiet zone, but a small margin is conventional
for safe printing and matches the project's other 2D formats. Pass
``quiet_zone=`` to :class:`AztecEncoder` to override the default.
"""


class AztecRenderer(Matrix2DRenderer[int]):
    """Rendering class for a pre-populated Aztec Code matrix.

    Wraps the matrix in a quiet zone before delegating to
    :class:`Matrix2DRenderer` for PNG, SVG, EPS, ASCII, terminal and DXF
    output.

    :param matrix: The pre-populated Aztec module matrix.
    :param quiet_zone: Width of the surrounding white border in modules.
        Defaults to :data:`AZTEC_DEFAULT_QUIET_ZONE`.
    """

    quiet_zone: int

    def __init__(
        self,
        matrix: list[list[int]],
        *,
        quiet_zone: int = AZTEC_DEFAULT_QUIET_ZONE,
    ) -> None:
        self.width = self.height = len(matrix)
        self.matrix = matrix
        self.quiet_zone = quiet_zone
        if quiet_zone > 0:
            self.add_border(colour=0, width=quiet_zone)

    def add_border(self, colour: int = 0, width: int = 2) -> None:
        """Wrap the matrix in a border of the given width and colour."""
        self.width = self.height = self.width + width * 2
        self.matrix = (
            [[colour] * self.width] * width
            + [
                [colour] * width + self.matrix[i] + [colour] * width
                for i in range(self.width - width * 2)
            ]
            + [[colour] * self.width] * width
        )
