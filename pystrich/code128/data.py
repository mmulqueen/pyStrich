"""Code 128 composition types: typed FNC markers plus a :class:`Code128Data`
container that interleaves them with text segments.

Mirrors :mod:`pystrich.datamatrix.data` for API symmetry. Latin-1 input is
accepted via ``encoding="iso-8859-1"`` (or ``auto_encoding=True``); the
underlying FNC4 charset-shift wire format is handled by the text encoder.
"""

from __future__ import annotations

import warnings
from typing import Literal

from pystrich.charset import EncodableData
from pystrich.exceptions import (
    Code128MarkerBytesCompatWarning,
    PyStrichInvalidInput,
    PyStrichInvalidOption,
)
from pystrich.gs1 import GS1Fixed, GS1Variable

Code128EncodingArg = Literal["ascii", "iso-8859-1"]
Code128Encoding = Literal["ascii", "iso-8859-1"]


# Symbolic marker name → (codeword in charset A, charset B, charset C);
# ``None`` means the marker isn't representable in that charset.
_MARKER_CODEWORDS: dict[str, tuple[int, int, int | None]] = {
    "FNC1": (102, 102, 102),
    "FNC2": (97, 97, None),
    "FNC3": (96, 96, None),
    "FNC4": (101, 100, None),
}


class Code128Marker:
    """A typed FNC marker for inclusion in a :class:`Code128Data` value.

    Use the module-level constants (:data:`FNC1`, :data:`FNC2`,
    :data:`FNC3`); concatenation with a plain ``str`` or another
    :class:`Code128Marker` (e.g. ``FNC1 + "10ABC"``) builds a
    :class:`Code128Data`. FNC4 isn't exposed as a public marker — Latin-1
    input is reached via ``encoding="iso-8859-1"`` on
    :class:`Code128Data` instead.
    """

    __slots__ = ("name",)

    name: str

    def __init__(self, name: str) -> None:
        if name not in _MARKER_CODEWORDS:
            raise ValueError(
                f"unknown Code128 marker name {name!r}; expected one of {sorted(_MARKER_CODEWORDS)}"
            )
        self.name = name

    def codeword_for_charset(self, charset: Literal["A", "B", "C"]) -> int:
        """Return the codeword for this marker in ``charset``, or raise if the
        marker isn't representable there."""
        a, b, c = _MARKER_CODEWORDS[self.name]
        value = {"A": a, "B": b, "C": c}[charset]
        if value is None:
            raise PyStrichInvalidInput(
                f"{self.name} is not representable in Code 128 charset {charset}"
            )
        return value

    def representable_in(self, charset: Literal["A", "B", "C"]) -> bool:
        """Whether this marker can be emitted from ``charset`` directly."""
        a, b, c = _MARKER_CODEWORDS[self.name]
        return {"A": a, "B": b, "C": c}[charset] is not None

    def representable_charsets(self) -> tuple[Literal["A", "B", "C"], ...]:
        """Charsets that can emit this marker, preference order B → A → C."""
        a, b, c = _MARKER_CODEWORDS[self.name]
        out: list[Literal["A", "B", "C"]] = []
        if b is not None:
            out.append("B")
        if a is not None:
            out.append("A")
        if c is not None:
            out.append("C")
        return tuple(out)

    def __add__(self, other):
        if isinstance(other, Code128Data):
            return Code128Data(self, *other.segments, encoding=other.encoding)
        if isinstance(other, (str, Code128Marker)):
            return Code128Data(self, other, encoding="ascii")
        return NotImplemented

    def __radd__(self, other):
        if isinstance(other, str):
            return Code128Data(other, self, encoding="ascii")
        return NotImplemented

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.name == other.name

    def __hash__(self):
        return hash((type(self), self.name))

    def __repr__(self):
        return self.name


FNC1 = Code128Marker("FNC1")
FNC2 = Code128Marker("FNC2")
FNC3 = Code128Marker("FNC3")
# FNC4 is the charset shift into the Latin-1 supplement. It's wire-format,
# not a semantic marker — callers should pass encoding="iso-8859-1" instead,
# and the text encoder will emit FNC4 internally. Kept here for use by the
# legacy bare-str compat shim.
_FNC4 = Code128Marker("FNC4")


# Maps the legacy magic byte to the marker the bare-str compat path
# promotes it to. The same byte values are also rejected from
# Code128Data ascii-mode str segments, with a message pointing at the
# typed constants.
_LEGACY_MARKER_BYTES: dict[str, Code128Marker] = {
    "\xf1": FNC1,
    "\xf2": FNC2,
    "\xf3": FNC3,
    "\xf4": _FNC4,
}


class Code128Data(EncodableData[Code128Encoding, Code128Marker]):
    """Composable encoder input mixing text chunks with FNC marker tokens.

    Build values by concatenating marker constants with plain strings on
    either side, then pass the result to :class:`Code128Encoder` in place
    of a ``str``::

        from pystrich.code128 import Code128Encoder, FNC1
        encoder = Code128Encoder(FNC1 + "10ABC" + FNC1 + "21XYZ")

    Pass ``encoding="iso-8859-1"`` (or ``auto_encoding=True``) to embed
    Latin-1 supplement characters; the encoder transparently emits the
    Code 128 FNC4 shifts. With ``encoding="ascii"`` the legacy magic-byte
    codepoints (``\\xf1``..``\\xf4``) are rejected with a message
    pointing at the typed marker constants.
    """

    __slots__ = ()

    encoding: Code128Encoding

    def __init__(
        self,
        *segments: str | Code128Marker,
        encoding: Code128EncodingArg | None = None,
        auto_encoding: bool = False,
    ) -> None:
        if encoding == "ascii":
            _reject_legacy_marker_bytes(segments)
        super().__init__(*segments, encoding=encoding, auto_encoding=auto_encoding)

    @classmethod
    def gs1(cls, *fields: GS1Fixed | GS1Variable) -> Code128Data:
        """Build a GS1-128 payload from typed Application Identifier fields.

        Emits a leading :data:`FNC1` (which flags the symbol as GS1-128 to
        conformant scanners) followed by
        ``application_identifier + value`` for each field, inserting a
        further :data:`FNC1` separator after each
        :class:`~pystrich.gs1.GS1Variable` that is not the final element.
        ASCII is hardcoded -- GS1 Application Identifier values are
        restricted to a 7-bit character set.

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
                "Code128Data.gs1 requires at least one GS1Fixed or GS1Variable field"
            )
        for field in fields:
            if not isinstance(field, (GS1Fixed, GS1Variable)):
                raise PyStrichInvalidOption(
                    "Code128Data.gs1 fields must be GS1Fixed or GS1Variable, "
                    f"got {type(field).__name__}"
                )
        segments: list[str | Code128Marker] = [FNC1]
        last = len(fields) - 1
        for i, field in enumerate(fields):
            segments.append(field.application_identifier + field.value)
            if isinstance(field, GS1Variable) and i != last:
                segments.append(FNC1)
        return cls(*segments, encoding="ascii")


def _reject_legacy_marker_bytes(
    segments: tuple[str | Code128Marker, ...],
) -> None:
    """Reject ``\\xf1``..``\\xf4`` from ASCII-mode str segments with a
    message pointing at the typed marker constants (or, for ``\\xf4``,
    the Latin-1 encoding path). The base class trial-encode would
    otherwise reject them with the generic "can't encode" message.
    """
    for seg in segments:
        if not isinstance(seg, str):
            continue
        for ch in seg:
            marker = _LEGACY_MARKER_BYTES.get(ch)
            if marker is None:
                continue
            if marker is _FNC4:
                hint = (
                    "use encoding='iso-8859-1' on Code128Data and pass the "
                    "Latin-1 character directly"
                )
            else:
                hint = (
                    f"use the {marker.name} marker constant instead: "
                    f"from pystrich.code128 import {marker.name}"
                )
            raise PyStrichInvalidInput(
                f"Character {ch!r} (U+{ord(ch):04X}) is the legacy "
                f"magic-byte form of {marker.name} and cannot appear "
                f"inside a Code128Data ASCII string segment; {hint}."
            )


def fnc_marker_bytes_compat(text: str) -> Code128Data | str:
    """Promote legacy FNC shortcut bytes (``\\xf1``..``\\xf4``) in a bare
    ``str`` to typed marker tokens on a :class:`Code128Data`, emitting a
    deprecation warning.

    Strings without any shortcut bytes pass through unchanged so callers
    that aren't using the convention see no behaviour change. The
    bare-``str`` shortcut is intended for removal once callers migrate
    to passing :class:`Code128Data` directly.
    """
    if not any(b in text for b in _LEGACY_MARKER_BYTES):
        return text

    warnings.warn(
        "Code128Encoder str input contains legacy FNC marker shortcut "
        "bytes (\\xf1..\\xf4). These are promoted to typed Code128Marker "
        "tokens for backward compatibility, but the bare-str shortcut is "
        "deprecated. Replace with Code128Data + the typed marker constants: "
        "from pystrich.code128 import Code128Encoder, FNC1; "
        "Code128Encoder(FNC1 + '10ABC' + FNC1 + '21XYZ').",
        Code128MarkerBytesCompatWarning,
        stacklevel=3,
    )

    segments: list[str | Code128Marker] = []
    buf = ""
    for ch in text:
        marker = _LEGACY_MARKER_BYTES.get(ch)
        if marker is None:
            buf += ch
            continue
        if buf:
            segments.append(buf)
            buf = ""
        segments.append(marker)
    if buf:
        segments.append(buf)
    return Code128Data(*segments, encoding="ascii")
