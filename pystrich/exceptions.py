"""Public exception hierarchy for pyStrich."""


class PyStrichError(Exception):
    """Base class for all pyStrich-specific errors."""


class PyStrichInvalidInput(PyStrichError):
    """The text being encoded is not valid for the chosen barcode format.

    Typically raised in response to end-user-supplied input.
    """


class PyStrichInvalidOption(PyStrichError):
    """An encoder option (configuration argument) is invalid.

    Typically a programmer error: options are usually hardcoded by the caller
    rather than passed through from end-user input.
    """