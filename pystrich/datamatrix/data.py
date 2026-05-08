"""DataMatrix-specific composition types and marker constants."""

from __future__ import annotations

import warnings
from typing import Literal

from pystrich.exceptions import (
    DataMatrixNonAsciiWarning,
    Fnc1WorkaroundCompatWarning,
    PyStrichInvalidInput,
    PyStrichInvalidOption,
)

DataMatrixEncoding = Literal["compat", "ascii", "iso-8859-1", "utf-8"]

_ENCODING_RULES: dict[DataMatrixEncoding, tuple[str, int, Literal["warn", "raise"]]] = {
    # encoding name -> (Python codec name, max representable codepoint, on-fail policy)
    "compat": ("ascii", 0x7F, "warn"),
    "ascii": ("ascii", 0x7F, "raise"),
    "iso-8859-1": ("iso-8859-1", 0xFF, "raise"),
    "utf-8": ("utf-8", 0x10FFFF, "raise"),
}

_AUTO_ENCODING_ORDER: tuple[DataMatrixEncoding, ...] = ("ascii", "iso-8859-1", "utf-8")


def get_suitable_encoding_for_codepoint(codepoint: int) -> DataMatrixEncoding:
    """Return the narrowest encoding from the auto-selection order that fits ``codepoint``."""
    return next(c for c in _AUTO_ENCODING_ORDER if codepoint <= _ENCODING_RULES[c][1])


class DataMatrixData:
    """Composable encoder input mixing text chunks with raw-codeword markers.

    Build values by concatenating marker constants (e.g. :data:`FNC1`) with
    plain strings on either side, then pass the result to
    :class:`DataMatrixEncoder` in place of a ``str``.

    Construction requires either an explicit ``encoding=`` (one of
    ``"ascii"``, ``"iso-8859-1"``, ``"utf-8"`` or the legacy ``"compat"``)
    or ``auto_encoding=True``. With ``auto_encoding=True`` the constructor
    picks the narrowest encoding from ``ascii``, ``iso-8859-1``, ``utf-8``
    that represents every segment; any ``encoding=`` argument passed
    alongside is ignored. After construction, :attr:`encoding` is always
    one of the four concrete charsets.

    .. versionadded:: 0.11

    .. versionchanged:: 0.12
       Callers must now pass either an explicit ``encoding=`` or
       ``auto_encoding=True``. Added the ``auto_encoding`` flag.

    .. deprecated:: 0.11
       The ``"compat"`` encoding is retained only for backwards
       compatibility and will be removed in a future release. New code
       should pick ``"ascii"``, ``"iso-8859-1"`` or ``"utf-8"`` explicitly,
       or use ``auto_encoding=True``.
    """

    __slots__ = ("auto_encoding", "encoding", "segments")

    segments: tuple[str | DataMatrixCodeword, ...]
    encoding: DataMatrixEncoding
    auto_encoding: bool

    def __init__(
        self,
        *segments: str | DataMatrixCodeword,
        encoding: DataMatrixEncoding | None = None,
        auto_encoding: bool = False,
    ) -> None:
        if encoding is None and not auto_encoding:
            raise PyStrichInvalidOption(
                "DataMatrixData requires an explicit encoding= "
                "(one of 'ascii', 'iso-8859-1', 'utf-8', 'compat') "
                "or auto_encoding=True for automatic selection."
            )
        if encoding is not None and encoding not in _ENCODING_RULES:
            raise PyStrichInvalidOption(
                f"unknown DataMatrixData encoding {encoding!r}; "
                f"expected one of {sorted(_ENCODING_RULES)}"
            )

        # Type-check segments and find the highest codepoint in one pass.
        max_codepoint = 0
        for segment in segments:
            if isinstance(segment, DataMatrixCodeword):
                continue
            if not isinstance(segment, str):
                raise TypeError(
                    f"DataMatrixData segments must be str or DataMatrixCodeword, "
                    f"got {type(segment).__name__}"
                )
            max_codepoint = max(max_codepoint, max((ord(c) for c in segment), default=0))

        if auto_encoding:
            chosen = get_suitable_encoding_for_codepoint(max_codepoint)
        else:
            assert encoding is not None  # guaranteed by the early None+!auto check
            chosen = encoding
            charset, max_allowed, on_fail = _ENCODING_RULES[encoding]
            if max_codepoint > max_allowed:
                suggested = get_suitable_encoding_for_codepoint(max_codepoint)
                seg_args = ", ".join(repr(s) for s in segments)
                msg = (
                    f"DataMatrix encoding {encoding!r} expects {charset.upper()}; "
                    f"got {chr(max_codepoint)!r}. "
                    f"Try {type(self).__name__}({seg_args}, encoding={suggested!r})"
                    " or pass auto_encoding=True to select an encoding automatically."
                )
                if on_fail == "raise":
                    raise PyStrichInvalidInput(msg)
                warnings.warn(
                    msg + " Promote to error with "
                    "warnings.filterwarnings('error', category=PyStrichWarning).",
                    DataMatrixNonAsciiWarning,
                    stacklevel=2,
                )

        self.segments = segments
        self.encoding = chosen
        self.auto_encoding = auto_encoding

    def __add__(self, other):
        if isinstance(other, (str, DataMatrixCodeword)):
            new_segments = (*self.segments, other)
            other_auto = False
        elif isinstance(other, DataMatrixData):
            if not (self.auto_encoding or other.auto_encoding) and other.encoding != self.encoding:
                raise PyStrichInvalidOption(
                    f"cannot concatenate DataMatrixData with different encodings "
                    f"({self.encoding!r} and {other.encoding!r})"
                )
            new_segments = (*self.segments, *other.segments)
            other_auto = other.auto_encoding
        else:
            return NotImplemented
        return type(self)(
            *new_segments,
            encoding=self.encoding,
            auto_encoding=self.auto_encoding or other_auto,
        )

    def __radd__(self, other):
        if not isinstance(other, str):
            return NotImplemented
        return type(self)(
            other,
            *self.segments,
            encoding=self.encoding,
            auto_encoding=self.auto_encoding,
        )

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

    .. versionadded:: 0.11
    """

    __slots__ = ("value",)

    value: int

    def __init__(self, value: int) -> None:
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


def fnc1_workaround_compat(text: str, /) -> DataMatrixData:
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

    segments: list[str | DataMatrixCodeword] = []
    for i, chunk in enumerate(text.split("\xe7")):
        if i > 0:
            segments.append(FNC1)
        if chunk:
            segments.append(chunk)
    return DataMatrixData(*segments, encoding="compat")
