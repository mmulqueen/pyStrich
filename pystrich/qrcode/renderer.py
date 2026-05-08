"""QR Code renderer"""

from __future__ import annotations

from pystrich.matrix_renderer import Matrix2DRenderer


class QRCodeRenderer(Matrix2DRenderer[int]):
    """Rendering class - given a pre-populated QR Code matrix.
    it will add edge handles and render to either to an image
    (including quiet zone) or ascii printout"""

    def __init__(self, matrix: list[list[int]]) -> None:
        self.width = self.height = len(matrix)
        self.matrix = matrix
        self.add_border(colour=0, width=4)

    @property
    def mtx_size(self) -> int:
        """Backwards-compatible alias for :attr:`width` (= :attr:`height`).

        QR Code symbols are square, so this returns the same value as
        either dimension.

        .. deprecated:: 0.12
           Use :attr:`width` or :attr:`height` instead.
        """
        return self.width

    def add_border(self, colour: int = 1, width: int = 4) -> None:
        """Wrap the matrix in a border of given width
        and colour"""

        self.width = self.height = self.width + width * 2

        self.matrix = (
            [
                [
                    colour,
                ]
                * self.width,
            ]
            * width
            + [
                [
                    colour,
                ]
                * width
                + self.matrix[i]
                + [
                    colour,
                ]
                * width
                for i in range(0, self.width - (width * 2))
            ]
            + [
                [
                    colour,
                ]
                * self.width,
            ]
            * width
        )
