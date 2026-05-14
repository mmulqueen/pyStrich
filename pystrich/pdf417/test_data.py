"""Tests for :class:`PDF417Data` charset selection and validation."""

from __future__ import annotations

import pytest

from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption
from pystrich.pdf417 import PDF417Data, PDF417Encoder


@pytest.mark.parametrize(
    "text, expected_encoding",
    [
        pytest.param("PDF417", "ascii", id="ascii"),
        pytest.param("café", "iso-8859-1", id="latin1"),
        pytest.param("½", "iso-8859-1", id="latin1-edge"),
        pytest.param("中文", "utf-8", id="utf8-cjk"),
        pytest.param("☕", "utf-8", id="utf8-symbol"),
        pytest.param("", "ascii", id="empty"),
    ],
)
def test_pdf417data_auto_encoding_picks_narrowest(text, expected_encoding):
    """``auto_encoding=True`` walks ASCII → Latin-1 → UTF-8 and picks the first that fits."""
    assert PDF417Data(text, auto_encoding=True).encoding == expected_encoding


def test_pdf417data_explicit_ascii_rejects_non_ascii():
    """Pinning ``encoding='ascii'`` raises on non-ASCII input."""
    with pytest.raises(PyStrichInvalidInput, match="ASCII"):
        PDF417Data("café", encoding="ascii")


def test_pdf417data_explicit_latin1_rejects_codepoint_above_ff():
    """Pinning ``encoding='iso-8859-1'`` raises on codepoints > 0xFF."""
    with pytest.raises(PyStrichInvalidInput, match="ISO-8859-1"):
        PDF417Data("☕", encoding="iso-8859-1")


def test_pdf417data_requires_encoding_or_auto():
    """Constructing without ``encoding=`` or ``auto_encoding=True`` is a programmer error."""
    with pytest.raises(PyStrichInvalidOption, match="auto_encoding"):
        PDF417Data("hello")


def test_pdf417data_rejects_unknown_encoding():
    """Unknown encoding names surface a clear error listing the supported ones."""
    with pytest.raises(PyStrichInvalidOption, match="unknown"):
        PDF417Data("hello", encoding="latin1")  # type: ignore[arg-type]


def test_pdf417_encoder_accepts_pdf417data_directly():
    """Passing :class:`PDF417Data` lets the caller pin the encoding."""
    # Force ascii — would raise on non-ASCII input via PDF417Data construction.
    e = PDF417Encoder(PDF417Data("hello", encoding="ascii"))
    assert e.matrix  # smoke: matrix is non-empty


def test_pdf417_encoder_wraps_plain_str_with_auto_encoding():
    """``PDF417Encoder(str)`` is equivalent to ``PDF417Encoder(PDF417Data(str, auto_encoding=True))``."""
    plain = PDF417Encoder("café").matrix
    wrapped = PDF417Encoder(PDF417Data("café", auto_encoding=True)).matrix
    assert plain == wrapped


def test_pdf417data_concatenation_inherits_encoding():
    """``+`` preserves the pinned encoding across segments."""
    combined = PDF417Data("abc", encoding="utf-8") + "def"
    assert combined.encoding == "utf-8"
    assert combined.segments == ("abc", "def")
