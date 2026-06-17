"""QR Code-specific composition types for :class:`QRCodeEncoder` input."""

from __future__ import annotations

from typing import Literal

from pystrich.charset import EncodableData

QRCodeEncoding = Literal["ascii", "iso-8859-1", "utf-8", "shift_jis"]


class QRCodeData(EncodableData[QRCodeEncoding]):
    """Encoder input with an explicit character-set choice.

    :class:`QRCodeEncoder` accepts a plain ``str`` and selects the encoding
    automatically. Use :class:`QRCodeData` only to pin the encoding -- for
    example, force ``"ascii"`` to reject non-ASCII input, or ``"shift_jis"``
    to unlock Kanji-mode compression for Japanese payloads.

    Pass either ``encoding=`` (one of ``"ascii"``, ``"iso-8859-1"``,
    ``"utf-8"``, ``"shift_jis"``) or ``auto_encoding=True``. With
    ``auto_encoding=True`` the constructor picks the narrowest fitting
    encoding from the first three; ``"shift_jis"`` is explicit-only.

    .. versionchanged:: 0.15
       Added ``"shift_jis"`` to unlock Kanji-mode compression.
    """

    __slots__ = ()
