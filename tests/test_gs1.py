"""Validation tests for the GS1 field wrappers."""

import pytest

from pystrich.exceptions import PyStrichInvalidInput
from pystrich.gs1 import GS1Fixed, GS1Variable


@pytest.mark.parametrize("cls", [GS1Fixed, GS1Variable])
def test_valid_field(cls):
    field = cls("01", "09501234543213")
    assert field.application_identifier == "01"
    assert field.value == "09501234543213"


@pytest.mark.parametrize("cls", [GS1Fixed, GS1Variable])
@pytest.mark.parametrize(
    "application_identifier",
    [
        pytest.param("", id="empty"),
        pytest.param("1", id="one-digit"),
        pytest.param("12345", id="five-digits"),
        pytest.param("0A", id="non-digit"),
        pytest.param("０１", id="non-ascii-digits"),  # noqa: RUF001 — testing rejection of fullwidth digits
        pytest.param("01 ", id="trailing-space"),
    ],
)
def test_invalid_application_identifier(cls, application_identifier):
    with pytest.raises(PyStrichInvalidInput, match="Application Identifier"):
        cls(application_identifier, "BF07")


@pytest.mark.parametrize("cls", [GS1Fixed, GS1Variable])
@pytest.mark.parametrize(
    "value",
    [
        pytest.param("", id="empty"),
        pytest.param("café", id="non-ascii"),
        pytest.param("BF\x1d07", id="embedded-gs"),
        pytest.param("BF\x07", id="control-char"),
        pytest.param("BF\x7f", id="del"),
    ],
)
def test_invalid_value(cls, value):
    with pytest.raises(PyStrichInvalidInput, match="value"):
        cls("10", value)


def test_field_equality_distinguishes_classes():
    """A fixed and variable field with the same payload are not equal --
    the class identity carries the FNC1-following semantics."""
    assert GS1Fixed("01", "x") == GS1Fixed("01", "x")
    assert GS1Fixed("01", "x") != GS1Variable("01", "x")


def test_field_repr():
    assert repr(GS1Fixed("01", "x")) == "GS1Fixed('01', 'x')"
    assert repr(GS1Variable("10", "y")) == "GS1Variable('10', 'y')"
