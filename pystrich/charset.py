"""Shared charset-selection helpers for the 2D ``*Data`` composition types."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import ClassVar, Literal, NamedTuple, Protocol, TypeVar

from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption

T = TypeVar("T")
C = TypeVar("C", bound=str, covariant=True)

Charset = Literal["ascii", "iso-8859-1", "utf-8"]


class EncodingRule(Protocol[C]):
    """An encoding entry: a Python codec name and its widest codepoint.

    Generic over the ``charset`` type so format-specific concretes can
    narrow it to a ``Literal`` (e.g. :data:`Charset`); the
    :func:`get_suitable_encoding_for_codepoint` return type then carries
    that narrower type back without a cast.
    """

    @property
    def charset(self) -> C: ...
    @property
    def max_codepoint(self) -> int: ...


def find_max_codepoint(
    segments: Iterable[str | T],
    *,
    ignore_types: tuple[type[T], ...] = (),
) -> int:
    """Highest Unicode codepoint across all ``str`` segments.

    :param segments: Segments to scan.
    :param ignore_types: Types to skip (e.g. raw codeword markers). Anything
        else that is not a ``str`` raises :class:`TypeError`.
    """
    result = 0
    for segment in segments:
        if isinstance(segment, ignore_types):
            continue
        if not isinstance(segment, str):
            raise TypeError(f"segment must be str, got {type(segment).__name__}")
        result = max(result, max((ord(c) for c in segment), default=0))
    return result


def get_suitable_encoding_for_codepoint(
    codepoint: int,
    rules: Sequence[EncodingRule[C]],
) -> C:
    """Return the ``charset`` of the first rule that covers ``codepoint``.

    ``rules`` is walked in order, so put the narrowest first. The return
    type matches the rules' ``charset`` type, so passing a sequence of
    rules whose ``charset`` is a ``Literal`` returns that ``Literal``.
    """
    return next(rule.charset for rule in rules if codepoint <= rule.max_codepoint)


def merge_str_segments(segments: tuple[str | T, ...]) -> tuple[str | T, ...]:
    """Merge consecutive str segments into one; drop empty strs."""
    out: list[str | T] = []
    for seg in segments:
        if isinstance(seg, str) and not seg:
            continue
        if out and isinstance(seg, str) and isinstance(out[-1], str):
            out[-1] += seg
        else:
            out.append(seg)
    return tuple(out)


class StandardEncodingRule(NamedTuple):
    """Default rule shape: ``charset`` plus its widest representable codepoint."""

    charset: Charset
    max_codepoint: int


_STANDARD_RULES: dict[Charset, StandardEncodingRule] = {
    "ascii": StandardEncodingRule("ascii", 0x7F),
    "iso-8859-1": StandardEncodingRule("iso-8859-1", 0xFF),
    "utf-8": StandardEncodingRule("utf-8", 0x10FFFF),
}


class EncodableData:
    """Shared base for the ``*Data`` composition types with a pinned charset.

    Subclasses typically only carry a docstring referencing the matching
    encoder. The default rule table covers ASCII, ISO-8859-1, and UTF-8;
    override ``_ENCODING_RULES`` / ``_AUTO_ENCODING_RULES`` to extend or
    narrow it.

    :ivar segments: Tuple of input string segments after empty-merge.
    :ivar encoding: The chosen Python codec name.
    :ivar auto_encoding: ``True`` if the encoding was picked automatically.
    """

    __slots__ = ("auto_encoding", "encoding", "segments")

    _ENCODING_RULES: ClassVar[dict[Charset, StandardEncodingRule]] = _STANDARD_RULES
    _AUTO_ENCODING_RULES: ClassVar[tuple[StandardEncodingRule, ...]] = tuple(
        _STANDARD_RULES.values()
    )

    segments: tuple[str, ...]
    encoding: Charset
    auto_encoding: bool

    def __init__(
        self,
        *segments: str,
        encoding: Charset | None = None,
        auto_encoding: bool = False,
    ) -> None:
        cls_name = type(self).__name__
        rules = self._ENCODING_RULES
        auto_rules = self._AUTO_ENCODING_RULES

        if auto_encoding:
            chosen = get_suitable_encoding_for_codepoint(find_max_codepoint(segments), auto_rules)
        elif encoding is None:
            raise PyStrichInvalidOption(
                f"{cls_name} requires an explicit encoding= "
                f"(one of {', '.join(repr(c) for c in rules)}) "
                "or auto_encoding=True for automatic selection."
            )
        elif encoding not in rules:
            raise PyStrichInvalidOption(
                f"unknown {cls_name} encoding {encoding!r}; expected one of {sorted(rules)}"
            )
        else:
            max_codepoint = find_max_codepoint(segments)
            chosen = encoding
            rule = rules[encoding]
            if max_codepoint > rule.max_codepoint:
                suggested = get_suitable_encoding_for_codepoint(max_codepoint, auto_rules)
                seg_args = ", ".join(repr(s) for s in segments)
                raise PyStrichInvalidInput(
                    f"{cls_name} encoding {encoding!r} expects {rule.charset.upper()}; "
                    f"got {chr(max_codepoint)!r}. "
                    f"Try {cls_name}({seg_args}, encoding={suggested!r})"
                    " or pass auto_encoding=True to select an encoding automatically."
                )

        self.segments = merge_str_segments(segments)
        self.encoding = chosen
        self.auto_encoding = auto_encoding

    def as_plain_text(self) -> tuple[str, Charset]:
        """Return the concatenated text and the codec to encode it with."""
        return "".join(self.segments), self.encoding

    def __add__(self, other):
        if isinstance(other, str):
            new_segments = (*self.segments, other)
            other_auto = False
        elif isinstance(other, type(self)):
            if not (self.auto_encoding or other.auto_encoding) and other.encoding != self.encoding:
                raise PyStrichInvalidOption(
                    f"cannot concatenate {type(self).__name__} with different encodings "
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
