"""Pillow is optional: PNG output needs it, every other output format does not.

The whole suite runs with Pillow hidden from production code (the autouse
``simulate_missing_pillow`` fixture in ``conftest.py``); only tests marked
``png`` get the real module. That relies on production code reaching Pillow
solely through :mod:`pystrich._pillow`, which the ``TID251`` ruff rule enforces.
"""

from __future__ import annotations

import pytest

from pystrich.code128 import Code128Encoder
from pystrich.exceptions import PyStrichPillowNotInstalled


def test_png_requires_pillow() -> None:
    with pytest.raises(PyStrichPillowNotInstalled, match=r'pip install "pyStrich\[png\]"'):
        Code128Encoder("HELLO").get_imagedata()


@pytest.mark.png
def test_png_output_with_pillow() -> None:
    assert Code128Encoder("HELLO").get_imagedata().startswith(b"\x89PNG\r\n")
