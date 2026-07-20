"""QR Code renderer"""

from __future__ import annotations

from pystrich.matrix_renderer import Matrix2DRenderer


class QRCodeRenderer(Matrix2DRenderer[int]):
    """Rendering class - given a pre-populated QR Code matrix.
    it will add the quiet zone and render to either an image
    or ascii printout"""

    def __init__(self, matrix: list[list[int]]) -> None:
        self.matrix = matrix
        self._add_border(colour=0, width=4)

    @property
    def mtx_size(self) -> int:
        """Backwards-compatible alias for :attr:`width` (= :attr:`height`).

        QR Code symbols are square, so this returns the same value as
        either dimension.

        .. deprecated:: 0.12
           Use :attr:`width` or :attr:`height` instead.
        """
        return self.width
