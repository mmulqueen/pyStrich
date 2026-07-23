"""DataMatrix-specific composition types and marker constants."""

from __future__ import annotations

import warnings
from typing import Literal

from pystrich.charset import Charset, EncodableData
from pystrich.exceptions import (
    DataMatrixNonAsciiWarning,
    Fnc1WorkaroundCompatWarning,
    PyStrichInvalidOption,
)
from pystrich.gs1 import GS1Fixed, GS1Variable

DataMatrixEncodingArg = Literal["compat", "ascii", "iso-8859-1", "utf-8"]
DataMatrixEncoding = Charset


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


def _compat_transform(
    segments: tuple[str | DataMatrixCodeword, ...],
) -> tuple[str | DataMatrixCodeword, ...]:
    """Run the legacy compat path: warn on non-ASCII and replace each char
    with ``ord >= 128`` by ``DataMatrixCodeword(ord + 1)``.

    Codepoints whose ``ord + 1`` exceeds 255 (e.g. ``'€'``) can't be
    represented and will raise from ``DataMatrixCodeword``'s validation.
    After this returns, str segments are guaranteed pure ASCII.
    """
    warned = False
    out: list[str | DataMatrixCodeword] = []
    for seg in segments:
        if isinstance(seg, str):
            chunk = ""
            for ch in seg:
                if ord(ch) >= 128:
                    if not warned:
                        warnings.warn(
                            "DataMatrix encoding 'compat' got non-ASCII input; the "
                            "legacy ASCII+1 transform will widen each high codepoint "
                            "to a raw codeword. Prefer encoding='iso-8859-1' (or "
                            "'utf-8') or auto_encoding=True. Promote to error with "
                            "warnings.filterwarnings('error', category=PyStrichWarning).",
                            DataMatrixNonAsciiWarning,
                            stacklevel=3,
                        )
                        warned = True
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


class DataMatrixData(EncodableData[DataMatrixEncoding, DataMatrixCodeword]):
    """Composable encoder input mixing text chunks with raw-codeword markers.

    Build values by concatenating marker constants (e.g. :data:`FNC1`) with
    plain strings on either side, then pass the result to
    :class:`DataMatrixEncoder` in place of a ``str``.

    Construction requires either an explicit ``encoding=`` (one of
    ``"ascii"``, ``"iso-8859-1"``, ``"utf-8"`` or the legacy ``"compat"``)
    or ``auto_encoding=True``. With ``auto_encoding=True`` the constructor
    picks the narrowest of ``ascii``, ``iso-8859-1``, ``utf-8`` that
    represents every segment; any ``encoding=`` argument passed alongside
    is ignored. ``"compat"`` is an init-time option only -- it triggers
    the legacy ASCII+1 codeword transform and is then stored as
    ``"ascii"``, so :attr:`encoding` is always one of the three concrete
    charsets after construction.

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

    __slots__ = ()

    # The largest symbol (144x144) holds at most 3116 numeric digits.
    _MAX_PAYLOAD_LENGTH = 3116

    encoding: DataMatrixEncoding

    def __init__(
        self,
        *segments: str | DataMatrixCodeword,
        encoding: DataMatrixEncodingArg | None = None,
        auto_encoding: bool = False,
    ) -> None:
        if encoding == "compat":
            segments = _compat_transform(segments)
            encoding = "ascii"
        super().__init__(*segments, encoding=encoding, auto_encoding=auto_encoding)

    @classmethod
    def gs1(cls, *fields: GS1Fixed | GS1Variable) -> DataMatrixData:
        """Build a GS1 Data Matrix payload from typed Application Identifier fields.

        Emits a leading :data:`FNC1` (which flags the symbol as GS1 Data
        Matrix to conformant scanners) followed by
        ``application_identifier + value`` for each field, inserting a
        further :data:`FNC1` separator after each
        :class:`~pystrich.gs1.GS1Variable` that is not the final element.
        ASCII is hardcoded -- the GS1 General Specifications restrict
        Application Identifier values to a 7-bit character set.

        :param fields: One or more :class:`~pystrich.gs1.GS1Fixed` /
            :class:`~pystrich.gs1.GS1Variable` instances. Plain strings are
            not accepted; wrap each Application Identifier / value pair in
            the appropriate field class so we know whether to follow it
            with FNC1.
        :raises pystrich.exceptions.PyStrichInvalidOption: if ``fields`` is
            empty or contains anything other than the field classes.

        .. versionadded:: 0.15
        """
        if not fields:
            raise PyStrichInvalidOption(
                "DataMatrixData.gs1 requires at least one GS1Fixed or GS1Variable field"
            )
        for field in fields:
            if not isinstance(field, (GS1Fixed, GS1Variable)):
                raise PyStrichInvalidOption(
                    "DataMatrixData.gs1 fields must be GS1Fixed or GS1Variable, "
                    f"got {type(field).__name__}"
                )
        segments: list[str | DataMatrixCodeword] = [FNC1]
        last = len(fields) - 1
        for i, field in enumerate(fields):
            segments.append(field.application_identifier + field.value)
            if isinstance(field, GS1Variable) and i != last:
                segments.append(FNC1)
        return cls(*segments, encoding="ascii")


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
