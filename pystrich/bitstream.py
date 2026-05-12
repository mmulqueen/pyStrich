"""MSB-first bit buffer used by 2D barcode encoders to assemble payloads
that span sub-byte boundaries before packing into codewords.
"""

from __future__ import annotations

from pystrich.exceptions import PyStrichError


class BitStream:
    """Mutable list of single bits with MSB-first append and prepend."""

    data: list[int]

    def __init__(self) -> None:
        self.data = []

    def append(self, value: int, bitsnum: int) -> None:
        """Append the low ``bitsnum`` bits of ``value``, highest bit first."""
        if bitsnum < 1:
            raise PyStrichError(f"Wrong value for number of bits ({bitsnum})")
        for i in range(bitsnum - 1, -1, -1):
            self.data.append((value >> i) & 0x01)

    def prepend(self, value: int, bitsnum: int) -> None:
        """Prepend the low ``bitsnum`` bits of ``value``, highest bit first."""
        if bitsnum < 1:
            raise PyStrichError(f"Wrong value for number of bits ({bitsnum})")
        self.data[:0] = [(value >> i) & 0x01 for i in range(bitsnum - 1, -1, -1)]
