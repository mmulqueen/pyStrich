"""Tests for AztecData encoding specification."""

from __future__ import annotations

import pytest

from pystrich.aztec.data import AztecData
from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption

# Encoding selection


@pytest.mark.parametrize(
    "text, expected",
    [
        pytest.param("Hello", "ascii", id="ascii"),
        pytest.param("café", "iso-8859-1", id="latin1"),
        pytest.param("日本語", "utf-8", id="unicode"),
    ],
)
def test_auto_encoding_picks_narrowest_fitting(text, expected):
    assert AztecData(text, auto_encoding=True).encoding == expected


def test_empty_segments_auto_encoding_defaults_to_ascii():
    data = AztecData(auto_encoding=True)
    assert data.segments == ()
    assert data.encoding == "ascii"


# Validation


def test_requires_either_encoding_or_auto_encoding():
    with pytest.raises(PyStrichInvalidOption, match="auto_encoding"):
        AztecData("hello")


def test_rejects_unknown_encoding():
    with pytest.raises(PyStrichInvalidOption, match="unknown"):
        AztecData("hello", encoding="latin1")  # type: ignore[arg-type]


def test_explicit_encoding_rejects_out_of_range():
    with pytest.raises(PyStrichInvalidInput, match="ASCII"):
        AztecData("café", encoding="ascii")


# Equality and hashing


def test_equal_when_segments_and_encoding_match():
    a = AztecData("Hello", encoding="ascii")
    b = AztecData("Hello", encoding="ascii")
    assert a == b
    assert hash(a) == hash(b)


@pytest.mark.parametrize(
    "a, b",
    [
        pytest.param(
            AztecData("Hello", encoding="ascii"),
            AztecData("World", encoding="ascii"),
            id="segments-differ",
        ),
        pytest.param(
            AztecData("café", auto_encoding=True),
            AztecData("café", encoding="utf-8"),
            id="encoding-differs",
        ),
    ],
)
def test_not_equal_when_field_differs(a, b):
    assert a != b
    assert hash(a) != hash(b)

