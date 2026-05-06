"""Public exception hierarchy for pyStrich.

.. versionadded:: 0.11
   Unified exception hierarchy. All pyStrich-raised errors now inherit from
   :class:`PyStrichError`; all pyStrich-emitted warnings inherit from
   :class:`PyStrichWarning`.
"""


class PyStrichError(Exception):
    """Base class for all pyStrich-specific errors.

    .. versionadded:: 0.11
    """


class PyStrichInvalidInput(PyStrichError):
    """The text being encoded is not valid for the chosen barcode format.

    Typically raised in response to end-user-supplied input.

    .. versionadded:: 0.11
    """


class PyStrichInvalidOption(PyStrichError):
    """An encoder option (configuration argument) is invalid.

    Typically a programmer error: options are usually hardcoded by the caller
    rather than passed through from end-user input.

    .. versionadded:: 0.11
    """


class PyStrichWarning(UserWarning):
    """Base class for pyStrich-specific warnings.

    .. versionadded:: 0.11
    """


class Fnc1WorkaroundCompatWarning(PyStrichWarning):
    """The legacy chr(231) FNC1 trick triggered the compat shim; use the FNC1 constant instead.

    .. versionadded:: 0.11
    """


class DataMatrixNonAsciiWarning(PyStrichWarning):
    """DataMatrix input contains non-ASCII characters; output will not decode correctly.

    .. versionadded:: 0.11
    """
