"""PDF417-specific composition types for :class:`PDF417Encoder` input."""

from __future__ import annotations

from pystrich.charset import Charset, EncodableData

PDF417Encoding = Charset


class PDF417Data(EncodableData):
    """Encoder input with an explicit character-set choice.

    :class:`PDF417Encoder` accepts a plain ``str`` and selects the encoding
    automatically. Use :class:`PDF417Data` only to pin the encoding -- for
    example, force ``"ascii"`` to reject non-ASCII input.

    Pass either ``encoding=`` (one of ``"ascii"``, ``"iso-8859-1"``,
    ``"utf-8"``) or ``auto_encoding=True``. With ``auto_encoding=True``
    the constructor picks the narrowest fitting encoding; any
    ``encoding=`` argument is then ignored.
    """

    __slots__ = ()
