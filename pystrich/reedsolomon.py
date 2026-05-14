"""Reed-Solomon error correction.

Computes the error-correction (EC) bytes that 2D barcodes append to their data
so that scanners can recover from damaged symbols. Splitting data into blocks
(needed by QR but not DataMatrix) is left to the caller.
"""

from __future__ import annotations

import functools
from collections.abc import Sequence


class BinaryExtensionGaloisField:
    """Arithmetic over a finite field of ``size`` symbols.

    Reed-Solomon needs add and multiply on bytes (or wider symbols) where every
    non-zero value has an inverse. Plain integer arithmetic doesn't give that;
    a Galois field does. The ``primitive`` polynomial picks which field — QR
    and DataMatrix happen to pick different ones.

    Add is just XOR, so this class only exposes :meth:`mul` and
    :meth:`generator_coefficients`. Tables built at construction make both fast.

    :param primitive: Polynomial that defines the field, as an integer. Bit
        ``i`` is the coefficient of ``x^i``.
    :param size: Number of symbols in the field. Must be a power of 2.
    """

    def __init__(self, primitive: int, *, size: int = 256) -> None:
        self.size = size
        self.primitive = primitive
        self._exp = [0] * size
        self._log = [0] * size
        x = 1
        for i in range(size - 1):
            self._exp[i] = x
            self._log[x] = i
            x <<= 1
            if x >= size:
                x ^= primitive
        self._exp[size - 1] = 1

    def mul(self, a: int, b: int) -> int:
        """Multiply two field symbols."""
        if a == 0 or b == 0:
            return 0
        return self._exp[(self._log[a] + self._log[b]) % (self.size - 1)]

    # B019: the cache pins `self`, but the only callers pass module-level
    # singletons (GF256_0x11D / GF256_0x12D) that already live forever.
    @functools.cache  # noqa: B019
    def generator_coefficients(self, num_ec: int, *, first_root: int = 0) -> tuple[int, ...]:
        """Reed-Solomon generator polynomial of degree ``num_ec``.

        Builds ``g(x) = (x - a^k)(x - a^(k+1)) ... (x - a^(k + num_ec - 1))``
        and returns its ``num_ec`` coefficients, highest power first. The
        leading 1 is dropped because :func:`reed_solomon_encode` doesn't need
        it.

        :param first_root: The ``k`` in the formula above.
        """
        poly = [1]
        order = self.size - 1
        for i in range(num_ec):
            alpha_i = self._exp[(first_root + i) % order]
            new_poly = [*poly, 0]
            for j, c in enumerate(poly):
                new_poly[j + 1] ^= self.mul(c, alpha_i)
            poly = new_poly
        return tuple(poly[1:])


GF256_0x11D = BinaryExtensionGaloisField(0x11D)
GF256_0x12D = BinaryExtensionGaloisField(0x12D)


def reed_solomon_encode(
    data: Sequence[int],
    field: BinaryExtensionGaloisField,
    num_ec: int,
    *,
    first_root: int = 0,
) -> list[int]:
    """Return ``num_ec`` Reed-Solomon EC bytes for ``data``.

    QR Code uses ``first_root=0``; DataMatrix uses ``first_root=1``. The two
    specs differ on which root the generator polynomial starts at.

    :param data: Data symbols, highest power first.
    :param field: The field to do arithmetic in.
    :param num_ec: How many EC bytes to produce.
    :param first_root: Forwarded to :meth:`BinaryExtensionGaloisField.generator_coefficients`.
    :returns: EC bytes, length ``num_ec``, highest power first.
    """
    gen = field.generator_coefficients(num_ec, first_root=first_root)
    data_len = len(data)
    buffer = list(data) + [0] * num_ec
    for i in range(data_len):
        lead = buffer[i]
        if lead != 0:
            for j in range(num_ec):
                buffer[i + 1 + j] ^= field.mul(lead, gen[j])
    return buffer[data_len:]


class PrimeGaloisField:
    """Arithmetic over a prime field GF(p), used by PDF417's Reed-Solomon.

    Unlike QR Code and DataMatrix, PDF417's RS works over GF(929) -- a
    prime field, not a binary extension. Addition and multiplication
    are integer arithmetic taken modulo ``prime``; subtraction is its
    own operation (in a binary field, addition and subtraction are both
    XOR, but that doesn't hold here).

    :param prime: The field's prime modulus. Must be prime.
    :param primitive: A primitive root mod ``prime``. PDF417 uses 3.
    """

    def __init__(self, prime: int, *, primitive: int) -> None:
        self.prime = prime
        self.primitive = primitive

    @functools.cache  # noqa: B019
    def generator_coefficients(self, num_ec: int, *, first_root: int = 1) -> tuple[int, ...]:
        """Reed-Solomon generator polynomial of degree ``num_ec``.

        Builds ``g(x) = (x - a^k)(x - a^(k+1)) ... (x - a^(k + num_ec - 1))``
        where ``a`` is the field's primitive element, and returns the
        ``num_ec`` non-leading coefficients, highest power first. PDF417
        uses ``first_root=1``.

        :param first_root: The ``k`` in the formula above.
        """
        poly = [1]
        for i in range(num_ec):
            root = pow(self.primitive, first_root + i, self.prime)
            new_poly = [*poly, 0]
            for j, c in enumerate(poly):
                new_poly[j + 1] = (new_poly[j + 1] - root * c) % self.prime
            poly = new_poly
        return tuple(poly[1:])


GF929 = PrimeGaloisField(929, primitive=3)


def reed_solomon_encode_pdf417(data: Sequence[int], num_ec: int) -> list[int]:
    """Return ``num_ec`` Reed-Solomon EC codewords for PDF417 ``data``.

    Divides ``data * x^num_ec`` by the generator polynomial over GF(929),
    then negates each remainder coefficient. The negation step is what
    makes the full codeword satisfy ``c(3^i) = 0`` at every generator
    root.

    :param data: Data codewords, highest power first. The first element
        is the Symbol Length Descriptor.
    :param num_ec: Number of EC codewords. PDF417 uses ``2 ** (ecl + 1)``
        for ECL ``0..8``: 2, 4, 8, 16, 32, 64, 128, 256, 512.
    :returns: EC codewords, length ``num_ec``, highest power first.
    """
    p = GF929.prime
    gen = GF929.generator_coefficients(num_ec, first_root=1)
    data_len = len(data)
    buffer = list(data) + [0] * num_ec
    for i in range(data_len):
        lead = buffer[i]
        if lead != 0:
            for j in range(num_ec):
                buffer[i + 1 + j] = (buffer[i + 1 + j] - lead * gen[j]) % p
    return [(p - r) % p for r in buffer[data_len:]]
