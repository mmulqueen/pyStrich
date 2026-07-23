"""Tests for the resource-exhaustion guards in :mod:`pystrich.limits`."""

from __future__ import annotations

import time

import pytest

from pystrich import limits
from pystrich.aztec import AztecEncoder
from pystrich.code39 import Code39Encoder
from pystrich.code128 import Code128Data, Code128Encoder
from pystrich.datamatrix import DataMatrixEncoder
from pystrich.ean13 import EAN13Encoder
from pystrich.exceptions import (
    PyStrichError,
    PyStrichInvalidOption,
    PyStrichInvalidPayloadLength,
)
from pystrich.itf import ITFEncoder
from pystrich.matrix_renderer import Matrix2DRenderer
from pystrich.pdf417 import PDF417Encoder
from pystrich.qrcode import QRCodeEncoder


def test_matrix_guard_precedes_buffer_allocation(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("buffer allocated despite oversized request")

    monkeypatch.setattr(Matrix2DRenderer, "_buffer", _boom)
    with pytest.raises(PyStrichInvalidOption):
        QRCodeEncoder("hi").get_pilimage(10**6)


def test_bar_guard_precedes_allocation():
    # Without the guard this would reach the (stubbed) Pillow import and raise
    # PyStrichPillowNotInstalled instead.
    with pytest.raises(PyStrichInvalidOption):
        Code128Encoder("hi").get_pilimage(10**6)


def test_matrix_cellsize_non_positive():
    with pytest.raises(PyStrichInvalidOption):
        QRCodeEncoder("hi").get_pilimage(0)


def test_bar_width_non_positive():
    with pytest.raises(PyStrichInvalidOption):
        Code128Encoder("hi").get_pilimage(0)


def test_matrix_pixel_cap_message_names_largest_cell_size():
    with pytest.raises(
        PyStrichInvalidOption, match=r"largest cell size for this \d+x\d+ symbol is \d+"
    ):
        QRCodeEncoder("hi").get_pilimage(10**6)


def test_bar_pixel_cap_message_names_bar_width():
    with pytest.raises(PyStrichInvalidOption, match="reduce the bar width"):
        Code128Encoder("hi").get_pilimage(10**6)


def test_max_image_pixels_read_at_call_time(monkeypatch):
    encoder = QRCodeEncoder("hi")
    monkeypatch.setattr(limits, "MAX_IMAGE_PIXELS", 1)
    with pytest.raises(PyStrichInvalidOption):
        encoder.get_pilimage(1)


_ENCODERS = [
    Code39Encoder,
    Code128Encoder,
    EAN13Encoder,
    ITFEncoder,
    QRCodeEncoder,
    DataMatrixEncoder,
    AztecEncoder,
    PDF417Encoder,
]


@pytest.mark.parametrize("encoder", _ENCODERS)
def test_input_length_cap_every_format(encoder):
    with pytest.raises(PyStrichInvalidPayloadLength):
        encoder("A" * (limits.MAX_INPUT_LENGTH + 1))


def test_input_length_cap_counts_data_segments():
    # A *Data is capped at construction, counting text characters plus markers.
    with pytest.raises(PyStrichInvalidPayloadLength):
        Code128Data("A" * (limits.MAX_INPUT_LENGTH + 1), encoding="ascii")


@pytest.mark.parametrize("encoder", _ENCODERS)
@pytest.mark.parametrize("text", ["", " ", "\x00", "\n", "€", "A" * limits.MAX_INPUT_LENGTH])
def test_edge_input_never_raises_untyped(encoder, text):
    """Every encoder either accepts an edge input or rejects it within the
    PyStrichError hierarchy -- never a bare crash (IndexError, RecursionError...)."""
    try:
        encoder(text)
    except PyStrichError:
        pass


def test_encodable_data_enforces_length_on_construction():
    # The 2D formats and Code 128 delegate the cap to EncodableData, so building
    # a *Data directly (or via .gs1()/concatenation) is capped too.
    from pystrich.qrcode import QRCodeData

    with pytest.raises(PyStrichInvalidPayloadLength):
        QRCodeData("A" * (limits.MAX_INPUT_LENGTH + 1), auto_encoding=True)


@pytest.mark.parametrize(
    "data_path, cap",
    [
        ("pystrich.qrcode.QRCodeData", 7089),
        ("pystrich.datamatrix.DataMatrixData", 3116),
        ("pystrich.aztec.AztecData", 4729),
        ("pystrich.pdf417.PDF417Data", 2710),
    ],
)
def test_format_specific_payload_cap(data_path, cap):
    import importlib

    module, name = data_path.rsplit(".", 1)
    data_cls = getattr(importlib.import_module(module), name)
    data_cls("9" * cap, auto_encoding=True)  # at the cap: constructs
    with pytest.raises(PyStrichInvalidPayloadLength):
        data_cls("9" * (cap + 1), auto_encoding=True)


def test_format_cap_tighter_than_global():
    from pystrich.qrcode import QRCodeData

    # QR's cap (7089) is below the global ceiling, so a 7090-char payload a
    # capless 1D format accepts is rejected at QRCodeData construction.
    Code39Encoder("9" * 7090)
    with pytest.raises(PyStrichInvalidPayloadLength):
        QRCodeData("9" * 7090, auto_encoding=True)


def test_encodable_data_length_check_precedes_charset_scan(monkeypatch):
    from pystrich.qrcode import QRCodeData

    def _boom(*args, **kwargs):
        raise AssertionError("charset scan ran despite over-length input")

    monkeypatch.setattr("pystrich.charset.find_max_codepoint", _boom)
    with pytest.raises(PyStrichInvalidPayloadLength):
        QRCodeData("A" * (limits.MAX_INPUT_LENGTH + 1), auto_encoding=True)


# Formats whose length check lives in the encoder rather than EncodableData,
# paired with the downstream call it must precede. Code 39 has no *Data type;
# Code 128 guards the legacy marker scan run before Code128Data is built. The
# EncodableData-backed 2D formats are covered by the two tests above.
_ENCODER_LEVEL_CHECKS = [
    (Code39Encoder, "pystrich.code39.TextEncoder.encode"),
    (Code128Encoder, "pystrich.code128.fnc_marker_bytes_compat"),
]


@pytest.mark.parametrize("encoder, downstream", _ENCODER_LEVEL_CHECKS)
def test_input_length_cap_precedes_encoding(encoder, downstream, monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("encoding ran despite over-length input")

    monkeypatch.setattr(downstream, _boom)
    with pytest.raises(PyStrichInvalidPayloadLength):
        encoder("A" * (limits.MAX_INPUT_LENGTH + 1))


def test_over_capacity_2d_raises_payload_length():
    # Under the input-length ceiling but over QR's own byte capacity (~2953),
    # so the format's capacity check fires rather than check_input_length.
    with pytest.raises(PyStrichInvalidPayloadLength):
        QRCodeEncoder("x" * 4000)


@pytest.mark.parametrize("get_vector", [QRCodeEncoder("hi").get_svg, Code128Encoder("hi").get_svg])
def test_vector_output_ignores_pixel_cap(get_vector):
    assert get_vector(10**6).startswith("<svg")


def test_near_limit_encoders_are_fast():
    start = time.monotonic()
    Code128Encoder("A" * 4000)
    DataMatrixEncoder("A" * 1000)
    QRCodeEncoder("A" * 1000)
    elapsed = time.monotonic() - start
    assert elapsed < 10, f"encoding took {elapsed:.1f}s"
