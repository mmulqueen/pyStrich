"""User-friendly composition of GS1 Application Identifier payloads.

Pair :class:`GS1Fixed` and :class:`GS1Variable` instances with the matching
:meth:`gs1` classmethod on :class:`pystrich.code128.Code128Data` or
:class:`pystrich.datamatrix.DataMatrixData` to emit a GS1-128 or GS1 Data
Matrix payload without managing FNC1 separators by hand.

The library does not ship an Application Identifier registry: callers tell
us whether each field is fixed- or variable-length by choosing the wrapper
class. FNC1 separators are inserted after variable-length fields that are
not the final element of the payload, and once at the very start of the
message.

.. versionadded:: 0.15
"""

from __future__ import annotations

from pystrich.exceptions import PyStrichInvalidInput


def _validate_application_identifier(application_identifier: str) -> None:
    if not isinstance(application_identifier, str) or not (
        application_identifier.isascii()
        and application_identifier.isdigit()
        and 2 <= len(application_identifier) <= 4
    ):
        raise PyStrichInvalidInput(
            f"GS1 Application Identifier must be 2-4 ASCII digits, got {application_identifier!r}"
        )


def _validate_value(value: str) -> None:
    if not isinstance(value, str) or not value:
        raise PyStrichInvalidInput("GS1 field value must be a non-empty str")
    for ch in value:
        if not 0x20 <= ord(ch) <= 0x7E:
            raise PyStrichInvalidInput(
                f"GS1 field value must be printable ASCII (0x20-0x7E); "
                f"{ch!r} (U+{ord(ch):04X}) is not"
            )


class _GS1Field:
    """Shared base for the typed GS1 field wrappers; not part of the public API."""

    __slots__ = ("application_identifier", "value")

    application_identifier: str
    value: str

    def __init__(self, application_identifier: str, value: str) -> None:
        _validate_application_identifier(application_identifier)
        _validate_value(value)
        self.application_identifier = application_identifier
        self.value = value

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return (
            self.application_identifier == other.application_identifier
            and self.value == other.value
        )

    def __hash__(self):
        return hash((type(self), self.application_identifier, self.value))

    def __repr__(self):
        return f"{type(self).__name__}({self.application_identifier!r}, {self.value!r})"


class GS1Fixed(_GS1Field):
    """A fixed-length GS1 Application Identifier field.

    The reader knows the data length from the Application Identifier alone,
    so no FNC1 separator is needed after the field. Use for Application
    Identifiers such as ``(01)`` GTIN-14, ``(17)`` expiry date, or ``(11)``
    production date.

    :param application_identifier: The 2-4 digit Application Identifier.
    :param value: The data string. Must be non-empty printable ASCII.
    """

    __slots__ = ()


class GS1Variable(_GS1Field):
    """A variable-length GS1 Application Identifier field.

    The reader cannot determine where the data ends from the Application
    Identifier alone, so an FNC1 separator follows unless this is the last
    field of the payload. Use for Application Identifiers such as ``(10)``
    batch, ``(21)`` serial number, or ``(240)`` additional product
    identification.

    :param application_identifier: The 2-4 digit Application Identifier.
    :param value: The data string. Must be non-empty printable ASCII.
    """

    __slots__ = ()
