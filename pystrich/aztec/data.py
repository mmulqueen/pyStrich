"""Aztec-specific composition types for :class:`AztecEncoder` input."""

from __future__ import annotations

from typing import NamedTuple

from pystrich.charset import (
    Charset,
    find_max_codepoint,
    get_suitable_encoding_for_codepoint,
)
from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption

AztecEncoding = Charset


class AztecEncodingRule(NamedTuple):
    """Concrete :class:`~pystrich.charset.EncodingRule` for Aztec Code."""

    charset: Charset
    max_codepoint: int


_ENCODING_RULES: dict[AztecEncoding, AztecEncodingRule] = {
    "ascii": AztecEncodingRule("ascii", 0x7F),
    "iso-8859-1": AztecEncodingRule("iso-8859-1", 0xFF),
    "utf-8": AztecEncodingRule("utf-8", 0x10FFFF),
}

_AUTO_ENCODING_RULES: tuple[AztecEncodingRule, ...] = tuple(_ENCODING_RULES.values())


class AztecData:
    """Encoder input with an explicit character-set choice.

    :class:`AztecEncoder` accepts a plain ``str`` and selects the encoding
    automatically. Use :class:`AztecData` only to pin the encoding -- for
    example, force ``"ascii"`` to reject non-ASCII input.

    Pass either ``encoding=`` (one of ``"ascii"``, ``"iso-8859-1"``,
    ``"utf-8"``) or ``auto_encoding=True``. With ``auto_encoding=True``
    the constructor picks the narrowest fitting encoding; any
    ``encoding=`` argument is then ignored.

    :ivar segments: Tuple of input string segments.
    :ivar encoding: The chosen Python codec name.
    :ivar auto_encoding: ``True`` if the encoding was picked automatically.
    """

    __slots__ = ("auto_encoding", "encoding", "segments")

    segments: tuple[str, ...]
    encoding: AztecEncoding
    auto_encoding: bool

    def __init__(
        self,
        *segments: str,
        encoding: AztecEncoding | None = None,
        auto_encoding: bool = False,
    ) -> None:
        if encoding is None and not auto_encoding:
            raise PyStrichInvalidOption(
                "AztecData requires an explicit encoding= "
                "(one of 'ascii', 'iso-8859-1', 'utf-8') "
                "or auto_encoding=True for automatic selection."
            )
        if encoding is not None and encoding not in _ENCODING_RULES:
            raise PyStrichInvalidOption(
                f"unknown AztecData encoding {encoding!r}; "
                f"expected one of {sorted(_ENCODING_RULES)}"
            )

        max_codepoint = find_max_codepoint(segments)

        if auto_encoding:
            chosen = get_suitable_encoding_for_codepoint(max_codepoint, _AUTO_ENCODING_RULES)
        else:
            assert encoding is not None
            chosen = encoding
            rule = _ENCODING_RULES[encoding]
            if max_codepoint > rule.max_codepoint:
                suggested = get_suitable_encoding_for_codepoint(max_codepoint, _AUTO_ENCODING_RULES)
                seg_args = ", ".join(repr(s) for s in segments)
                raise PyStrichInvalidInput(
                    f"AztecData encoding {encoding!r} expects {rule.charset.upper()}; "
                    f"got {chr(max_codepoint)!r}. "
                    f"Try {type(self).__name__}({seg_args}, encoding={suggested!r})"
                    " or pass auto_encoding=True to select an encoding automatically."
                )

        self.segments = segments
        self.encoding = chosen
        self.auto_encoding = auto_encoding

    def __add__(self, other):
        if isinstance(other, str):
            new_segments = (*self.segments, other)
            other_auto = False
        elif isinstance(other, AztecData):
            if not (self.auto_encoding or other.auto_encoding) and other.encoding != self.encoding:
                raise PyStrichInvalidOption(
                    f"cannot concatenate AztecData with different encodings "
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
