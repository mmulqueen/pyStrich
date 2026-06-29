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


class PyStrichPillowNotInstalled(PyStrichError):
    """PNG output was requested but Pillow is not installed.

    Pillow is an optional dependency, required only for PNG output.

    .. versionadded:: 0.16
    """

    def __init__(
        self,
        message: str = (
            "PNG output requires Pillow, an optional dependency of pyStrich. "
            'Install it with: pip install "pyStrich[png]"'
        ),
    ) -> None:
        super().__init__(message)


class PyStrichWarning(UserWarning):
    """Base class for pyStrich-specific warnings.

    .. versionadded:: 0.11
    """


class Fnc1WorkaroundCompatWarning(PyStrichWarning):
    """The legacy chr(231) FNC1 trick triggered the compat shim; use the FNC1 constant instead.

    .. versionadded:: 0.11
    """


class Code128MarkerBytesCompatWarning(PyStrichWarning):
    """The legacy ``\\xf1``..``\\xf4`` FNC shortcut bytes in bare-str input
    triggered the compat shim; use :class:`~pystrich.code128.Code128Data`
    with the typed marker constants instead.
    """


class DataMatrixNonAsciiWarning(PyStrichWarning):
    """DataMatrix input contains non-ASCII characters; output will not decode correctly.

    .. versionadded:: 0.11
    """
