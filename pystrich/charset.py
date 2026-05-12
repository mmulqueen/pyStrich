"""Shared charset-selection helpers for the 2D ``*Data`` composition types."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Literal, Protocol, TypeVar

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
