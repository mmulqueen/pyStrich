"""Shared charset-selection helpers for the 2D ``*Data`` composition types."""

from __future__ import annotations

from collections.abc import Iterable
from typing import ClassVar, Generic, Literal, TypeGuard, cast, get_args, get_origin

from typing_extensions import Never, TypeVar

from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption
from pystrich.limits import check_input_length

T = TypeVar("T")


def _payload_length(segments: Iterable[str | object]) -> int:
    """Character count of ``segments``; each non-str marker counts as one."""
    return sum(len(s) if isinstance(s, str) else 1 for s in segments)


Charset = Literal["ascii", "iso-8859-1", "utf-8"]

EncT = TypeVar("EncT", bound=str, default=Charset)
MarkerT = TypeVar("MarkerT", default=Never)


class _HasMarkers(Exception):
    """Raised by :meth:`EncodableData.as_plain_text` when the data contains
    raw markers that have no plain-text representation. Subclasses with
    ``_MARKER_TYPES == ()`` (the default) never trigger this.
    """


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


def pick_default_encoding(codepoint: int) -> Charset:
    """Narrowest of ASCII / ISO-8859-1 / UTF-8 that represents ``codepoint``."""
    if codepoint <= 0x7F:
        return "ascii"
    if codepoint <= 0xFF:
        return "iso-8859-1"
    return "utf-8"


def _all_str(segments: tuple[str | object, ...]) -> TypeGuard[tuple[str, ...]]:
    """Narrow ``segments`` to ``tuple[str, ...]`` when every element is a str."""
    return all(isinstance(s, str) for s in segments)


def _extract_marker_types(marker_type: object) -> tuple[type, ...]:
    """Resolve the ``MarkerT`` arm of ``EncodableData[EncT, MarkerT]`` to a
    concrete tuple of types for ``isinstance``. ``Never`` collapses to
    ``()``; a union expands to its arms; a single class wraps to a 1-tuple.
    """
    if marker_type is Never:
        return ()
    args = get_args(marker_type)
    if args:
        return args
    return (marker_type,)  # type: ignore[return-value]


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


class EncodableData(Generic[EncT, MarkerT]):
    """Shared base for the ``*Data`` composition types with a pinned charset.

    Generic over two parameters: ``EncT`` is the encoding-literal type
    (defaults to :data:`Charset`), and ``MarkerT`` is the raw-marker type
    that may appear alongside text segments (defaults to ``Never`` -- no
    markers). The Literal's arms become ``_SUPPORTED_ENCODINGS`` and the
    marker type becomes ``_MARKER_TYPES`` automatically via
    :meth:`__init_subclass__`. Override :meth:`_validate_explicit_encoding`
    only if you need to swap the default trial-encode policy.

    :ivar segments: Tuple of input segments after empty-merge.
    :ivar encoding: The chosen Python codec name.
    :ivar auto_encoding: ``True`` if the encoding was picked automatically.
    """

    __slots__ = ("auto_encoding", "encoding", "segments")

    # Populated from the parameterised generics by __init_subclass__.
    _SUPPORTED_ENCODINGS: ClassVar[tuple[str, ...]] = ()
    _MARKER_TYPES: ClassVar[tuple[type, ...]] = ()

    # Longest payload the format can ever encode, in characters; ``None`` falls
    # back to the global ceiling. Subclasses set their true single-symbol maximum.
    _MAX_PAYLOAD_LENGTH: ClassVar[int | None] = None

    segments: tuple[str | MarkerT, ...]
    encoding: EncT
    auto_encoding: bool

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        # __orig_bases__ holds the parameterised form when generic args
        # are explicit; __bases__ holds the bare class when subclasses
        # omit them (relying on the TypeVar defaults).
        type_params = EncodableData.__parameters__  # type: ignore[attr-defined]
        for base in (*getattr(cls, "__orig_bases__", ()), *cls.__bases__):
            if base is EncodableData or get_origin(base) is EncodableData:
                args = get_args(base)
                enc_type, marker_type = (
                    args[i] if i < len(args) else tp.__default__ for i, tp in enumerate(type_params)
                )
                cls._SUPPORTED_ENCODINGS = get_args(enc_type)
                cls._MARKER_TYPES = _extract_marker_types(marker_type)
                return
        raise TypeError(
            f"{cls.__name__} must subclass EncodableData, "
            "optionally parameterised (e.g. EncodableData[DataMatrixEncoding, DataMatrixCodeword])."
        )

    def __init__(
        self,
        *segments: str | MarkerT,
        encoding: EncT | None = None,
        auto_encoding: bool = False,
    ) -> None:
        # Enforced here, before the O(total-chars) charset scan below, so the
        # cap covers every ``*Data`` the way in -- direct construction, ``.gs1()``,
        # concatenation -- not just the encoder entry points.
        check_input_length(_payload_length(segments), self._MAX_PAYLOAD_LENGTH)
        if auto_encoding:
            max_cp = find_max_codepoint(segments, ignore_types=self._MARKER_TYPES)
            chosen = cast(EncT, pick_default_encoding(max_cp))
        elif encoding is None:
            raise PyStrichInvalidOption(
                f"{type(self).__name__} requires an explicit encoding= "
                f"(one of {', '.join(self._SUPPORTED_ENCODINGS)}) "
                "or auto_encoding=True for automatic selection."
            )
        else:
            self._validate_explicit_encoding(segments, encoding)
            chosen = encoding

        self.segments = merge_str_segments(segments)
        self.encoding = chosen
        self.auto_encoding = auto_encoding

    def _validate_explicit_encoding(
        self, segments: tuple[str | object, ...], encoding: str
    ) -> None:
        """Raise if ``encoding`` isn't supported or can't represent the segments.

        Trial-encodes each str segment with ``encoding``; the codec itself
        decides what it can cover, which keeps the base class
        codec-agnostic. Non-str segments (i.e. :attr:`_MARKER_TYPES`
        instances) are skipped.
        """
        cls_name = type(self).__name__
        if encoding not in self._SUPPORTED_ENCODINGS:
            raise PyStrichInvalidOption(
                f"unknown {cls_name} encoding {encoding!r}; "
                f"expected one of {sorted(self._SUPPORTED_ENCODINGS)}"
            )
        # Also serves as type validation: rejects non-str non-marker segments.
        max_cp = find_max_codepoint(segments, ignore_types=self._MARKER_TYPES)
        try:
            for seg in segments:
                if isinstance(seg, str):
                    seg.encode(encoding)
        except UnicodeEncodeError as e:
            suggested = pick_default_encoding(max_cp)
            seg_args = ", ".join(repr(s) for s in segments)
            raise PyStrichInvalidInput(
                f"{cls_name} encoding {encoding.upper()} cannot encode the input; "
                f"try {cls_name}({seg_args}, encoding={suggested!r}) "
                "or pass auto_encoding=True to select an encoding automatically."
            ) from e

    def as_plain_text(self) -> tuple[str, EncT]:
        """Return the concatenated text and the codec to encode it with.

        Raises :class:`_HasMarkers` if any segment is a raw marker rather
        than a string. For subclasses without markers (``MarkerT == Never``)
        the check is a no-op.
        """
        if not _all_str(self.segments):
            raise _HasMarkers
        return "".join(self.segments), self.encoding

    def __add__(self, other):
        new_segments: tuple[str | MarkerT, ...]
        if isinstance(other, (str, *self._MARKER_TYPES)):
            new_segments = (*self.segments, other)  # type: ignore[assignment]
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

    def __len__(self) -> int:
        """Payload length: text characters plus one per marker token."""
        return _payload_length(self.segments)

    def __eq__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        return self.segments == other.segments and self.encoding == other.encoding

    def __hash__(self):
        return hash((type(self), self.segments, self.encoding))

    def __repr__(self):
        return f"{type(self).__name__}({list(self.segments)!r})"
