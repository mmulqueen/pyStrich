"""QR Code-specific composition types for :class:`QRCodeEncoder` input."""

from __future__ import annotations

from typing import Literal
from urllib.parse import quote

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

    @classmethod
    def wifi_network(
        cls,
        ssid: str,
        password: str | None = None,
        *,
        hidden: bool = False,
        transition_disable: int | None = None,
        password_identifier: str | None = None,
        public_key: str | None = None,
    ) -> QRCodeData:
        """Build a ``WIFI:`` payload a phone can scan to join a network.

        Produces the WIFI URI defined by the Wi-Fi Alliance WPA3
        Specification v3.5.

        :param ssid: Network name.
        :param password: Network password; omit for an open network.
        :param hidden: ``True`` when the network does not broadcast its SSID.
        :param transition_disable: Transition Disable bitmap, rendered as
            hexadecimal.
        :param password_identifier: SAE password identifier.
        :param public_key: Base64-encoded SAE-PK public key, inserted verbatim.

        .. versionadded:: 0.15
        """
        payload = "WIFI:"
        if password:
            payload += "T:WPA;"
        if transition_disable is not None:
            payload += f"R:{transition_disable:x};"
        payload += f"S:{quote(ssid, safe='')};"
        if hidden:
            payload += "H:true;"
        if password_identifier is not None:
            payload += f"I:{quote(password_identifier, safe='')};"
        if password:
            payload += f"P:{quote(password, safe='')};"
        if public_key is not None:
            payload += f"K:{public_key};"
        payload += ";"
        return cls(payload, encoding="ascii")
