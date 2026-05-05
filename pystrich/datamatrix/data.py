"""DataMatrix-specific composition types and marker constants."""

import warnings

from pystrich.exceptions import (
    DataMatrixNonAsciiWarning,
    Fnc1WorkaroundCompatWarning,
    PyStrichInvalidInput,
    PyStrichInvalidOption,
)


_ENCODING_RULES = {
    "compat": ("ascii", "warn"),
    "ascii": ("ascii", "raise"),
    "iso-8859-1": ("iso-8859-1", "raise"),
    "utf-8": ("utf-8", "raise"),
}


class DataMatrixData:
    """Composable encoder input mixing text chunks with raw-codeword markers.

    Build values by concatenating marker constants (e.g. :data:`FNC1`) with
    plain strings on either side, then pass the result to
    :class:`DataMatrixEncoder` in place of a ``str``.

    Four encodings are supported: ``"compat"`` (default; warns on non-ASCII),
    ``"ascii"`` (raises on any byte > 127), ``"iso-8859-1"`` (Latin-1; emits the
    DataMatrix Upper Shift codeword for chars 128-255), and ``"utf-8"`` (declares
    ECI 26 once at the start of the symbol and byte-encodes the input).
    """

    __slots__ = ("segments", "encoding")

    def __init__(self, *segments, encoding: str = "compat"):
        if encoding not in _ENCODING_RULES:
            raise PyStrichInvalidOption(
                f"unknown DataMatrixData encoding {encoding!r}; "
                f"expected one of {sorted(_ENCODING_RULES)}"
            )

        charset, on_fail = _ENCODING_RULES[encoding]

        for segment in segments:
            if isinstance(segment, DataMatrixCodeword):
                continue
            if not isinstance(segment, str):
                raise TypeError(
                    f"DataMatrixData segments must be str or DataMatrixCodeword, "
                    f"got {type(segment).__name__}"
                )
            try:
                segment.encode(charset)
            except UnicodeEncodeError as exc:
                suggested = "utf-8" if any(ord(c) > 255 for c in segment) else "iso-8859-1"
                msg = (
                    f"DataMatrix encoding {encoding!r} expects {charset.upper()}; "
                    f"got {segment!r}."
                )
                if suggested != encoding:
                    seg_args = ", ".join(repr(s) for s in segments)
                    msg += f" Try {type(self).__name__}({seg_args}, encoding={suggested!r})."
                if on_fail == "raise":
                    raise PyStrichInvalidInput(msg) from exc
                warnings.warn(
                    msg + " Promote to error with "
                    "warnings.filterwarnings('error', category=PyStrichWarning).",
                    DataMatrixNonAsciiWarning,
                    stacklevel=2,
                )

        self.segments = segments
        self.encoding = encoding

    def __add__(self, other):
        cls = type(self)
        if isinstance(other, str):
            return cls(*self.segments, other, encoding=self.encoding)
        if isinstance(other, DataMatrixData):
            if other.encoding != self.encoding:
                raise PyStrichInvalidOption(
                    f"cannot concatenate DataMatrixData with different encodings "
                    f"({self.encoding!r} and {other.encoding!r})"
                )
            return cls(*self.segments, *other.segments, encoding=self.encoding)
        if isinstance(other, DataMatrixCodeword):
            return cls(*self.segments, other, encoding=self.encoding)
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            return type(self)(other, *self.segments, encoding=self.encoding)
        return NotImplemented

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.segments == other.segments and self.encoding == other.encoding

    def __hash__(self):
        return hash((type(self), self.segments, self.encoding))

    def __repr__(self):
        return f"{type(self).__name__}({list(self.segments)!r})"


class DataMatrixCodeword:
    """A literal DataMatrix codeword value to emit verbatim.

    Concatenation with a plain ``str`` or another codeword (e.g. ``FNC1 + "..."``)
    is the modern API path and produces a :class:`DataMatrixData` tagged with
    the strict ``"ascii"`` encoding. Concatenation with an existing
    :class:`DataMatrixData` preserves that object's encoding instead.
    """

    __slots__ = ("value",)

    def __init__(self, value: int):
        if not 0 <= value <= 255:
            raise ValueError(f"codeword must be 0-255, got {value}")
        self.value = value

    def __add__(self, other):
        if isinstance(other, DataMatrixData):
            return DataMatrixData(self, *other.segments, encoding=other.encoding)
        if isinstance(other, (str, DataMatrixCodeword)):
            return DataMatrixData(self, other, encoding="ascii")
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            return DataMatrixData(other, self, encoding="ascii")
        return NotImplemented

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.value == other.value

    def __hash__(self):
        return hash((type(self), self.value))

    def __repr__(self):
        return f"{type(self).__name__}({self.value})"


# Codeword 232 — see https://github.com/mmulqueen/pyStrich/issues/13
FNC1 = DataMatrixCodeword(232)


def fnc1_workaround_compat(text: str) -> DataMatrixData:
    """Translate a leading chr(231) into an explicit FNC1 marker.

    Predates the FNC1 constant: callers triggered codeword 232 via the +1 ASCII
    offset bug. Non-leading chr(231) is left alone and falls through to the
    compat-mode warning. New code should use the FNC1 constant directly.

    See https://github.com/mmulqueen/pyStrich/issues/13.
    """
    if not text.startswith("\xe7"):
        return DataMatrixData(text, encoding="compat")

    warnings.warn(
        "chr(231) is being interpreted as FNC1 (codeword 232) for backwards "
        "compatibility with issue #13. New code should use the FNC1 constant "
        "from pystrich.datamatrix instead.",
        Fnc1WorkaroundCompatWarning,
        stacklevel=2,
    )

    segments = []
    for i, chunk in enumerate(text.split("\xe7")):
        if i > 0:
            segments.append(FNC1)
        if chunk:
            segments.append(chunk)
    return DataMatrixData(*segments, encoding="compat")
