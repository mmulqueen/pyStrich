"""Private helpers for converting rendered output to ``data:`` URLs.

Shared by :class:`pystrich.bar_encoder.Bar1DEncoder` and
:class:`pystrich.matrix_encoder.Matrix2DEncoder`.
"""

from __future__ import annotations

from base64 import b64encode
from urllib.parse import quote


def svg_to_data_url(svg: str) -> str:
    return "data:image/svg+xml," + quote(svg)


def png_to_data_url(png: bytes) -> str:
    return "data:image/png;base64," + b64encode(png).decode("ascii")
