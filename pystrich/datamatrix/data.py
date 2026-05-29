"""DataMatrix-specific composition types and marker constants."""

from __future__ import annotations

import warnings
from typing import Literal, NamedTuple

from pystrich.charset import (
    Charset,
    find_max_codepoint,
    get_suitable_encoding_for_codepoint,
    merge_str_segments,
)
from pystrich.exceptions import (
    DataMatrixNonAsciiWarning,
    Fnc1WorkaroundCompatWarning,
    PyStrichInvalidInput,
    PyStrichInvalidOption,
)

DataMatrixEncoding = Literal["compat", "ascii", "iso-8859-1", "utf-8"]


class DataMatrixEncodingRule(NamedTuple):
    """Concrete :class:`~pystrich.charset.EncodingRule` plus DataMatrix's on-fail policy."""

    charset: Charset
    max_codepoint: int
    on_fail: Literal["warn", "raise"]


_ENCODING_RULES: dict[DataMatrixEncoding, DataMatrixEncodingRule] = {
    "compat": DataMatrixEncodingRule("ascii", 0x7F, "warn"),
    "ascii": DataMatrixEncodingRule("ascii", 0x7F, "raise"),
    "iso-8859-1": DataMatrixEncodingRule("iso-8859-1", 0xFF, "raise"),
    "utf-8": DataMatrixEncodingRule("utf-8", 0x10FFFF, "raise"),
}

_AUTO_ENCODING_RULES: tuple[DataMatrixEncodingRule, ...] = (
    _ENCODING_RULES["ascii"],
    _ENCODING_RULES["iso-8859-1"],
    _ENCODING_RULES["utf-8"],
)


class _HasMarkers(Exception):
    """Raised by :meth:`DataMatrixData.as_plain_text` when the data contains
    :class:`DataMatrixCodeword` markers (which the DP optimiser can't represent).
    """


def _compat_transform(
    segments: tuple[str | DataMatrixCodeword, ...],
) -> tuple[str | DataMatrixCodeword, ...]:
    """Replace each char with ``ord >= 128`` by ``DataMatrixCodeword(ord + 1)``.

    Used only for the deprecated ``"compat"`` encoding. Codepoints whose
    ``ord + 1`` exceeds 255 (e.g. ``'€'``) can't be represented and will
    raise from ``DataMatrixCodeword``'s validation.
    """
    out: list[str | DataMatrixCodeword] = []
    for seg in segments:
        if isinstance(seg, str):
            chunk = ""
            for ch in seg:
                if ord(ch) >= 128:
                    if chunk:
                        out.append(chunk)
                        chunk = ""
                    out.append(DataMatrixCodeword(ord(ch) + 1))
                else:
                    chunk += ch
            if chunk:
                out.append(chunk)
        else:
            out.append(seg)
    return tuple(out)


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

    After construction :attr:`segments` is normalised: consecutive str
    segments are merged, empty strs are dropped, and (for ``"compat"``)
    every codepoint with the high bit set is replaced by a
    :class:`DataMatrixCodeword` carrying the legacy ``ord + 1`` value.
    The encoder therefore only ever sees pure-encodable strs interleaved with
    raw codeword markers.

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

        max_codepoint = find_max_codepoint(segments, ignore_types=(DataMatrixCodeword,))

        chosen: DataMatrixEncoding
        if auto_encoding:
            chosen = get_suitable_encoding_for_codepoint(max_codepoint, _AUTO_ENCODING_RULES)
        else:
            assert encoding is not None  # guaranteed by the early None+!auto check
            chosen = encoding
            charset, max_allowed, on_fail = _ENCODING_RULES[encoding]
            if max_codepoint > max_allowed:
                suggested = get_suitable_encoding_for_codepoint(max_codepoint, _AUTO_ENCODING_RULES)
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

        if chosen == "compat":
            segments = _compat_transform(segments)

        self.segments = merge_str_segments(segments)
        self.encoding = chosen
        self.auto_encoding = auto_encoding

    def as_plain_text(self) -> tuple[str, Charset]:
        """Return the concatenated text and the codec to encode it with.

        Raises :class:`_HasMarkers` if any segment is a
        :class:`DataMatrixCodeword`. ``"compat"`` maps to ``"ascii"`` —
        the normaliser has already replaced compat's high codepoints with
        markers, which trigger the raise instead.
        """
        parts: list[str] = []
        for seg in self.segments:
            if isinstance(seg, DataMatrixCodeword):
                raise _HasMarkers
            parts.append(seg)
        charset: Charset = "ascii" if self.encoding == "compat" else self.encoding
        return "".join(parts), charset

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
    offset bug. Without a leading chr(231) the text is handed off to
    ``auto_encoding=True`` to match the other symbologies. New code should use
    the FNC1 constant directly.

    See https://github.com/mmulqueen/pyStrich/issues/13.
    """
    if not text.startswith("\xe7"):
        return DataMatrixData(text, auto_encoding=True)

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
