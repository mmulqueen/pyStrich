"""Aztec-specific composition types for :class:`AztecEncoder` input."""

from __future__ import annotations

from pystrich.charset import Charset, EncodableData

AztecEncoding = Charset


class AztecData(EncodableData):
    """Encoder input with an explicit character-set choice.

    :class:`AztecEncoder` accepts a plain ``str`` and selects the encoding
    automatically. Use :class:`AztecData` only to pin the encoding -- for
    example, force ``"ascii"`` to reject non-ASCII input.

    Pass either ``encoding=`` (one of ``"ascii"``, ``"iso-8859-1"``,
    ``"utf-8"``) or ``auto_encoding=True``. With ``auto_encoding=True``
    the constructor picks the narrowest fitting encoding; any
    ``encoding=`` argument is then ignored.
    """

    __slots__ = ()

    # The full 32-layer symbol at minimum ECC holds at most 4729 numeric digits.
    _MAX_PAYLOAD_LENGTH = 4729
