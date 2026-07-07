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
        order = size - 1
        # ``_exp`` is doubled to length ``2*order`` so multiply can index
        # ``_exp[log_a + log_b]`` directly -- the sum never exceeds 2*order - 2,
        # sparing a ``% order`` reduction on the hot path.
        self._exp = [0] * (2 * order)
        self._log = [0] * size
        x = 1
        for i in range(order):
            self._exp[i] = x
            self._log[x] = i
            x <<= 1
            if x >= size:
                x ^= primitive
        for i in range(order, 2 * order):
            self._exp[i] = self._exp[i - order]

    def mul(self, a: int, b: int) -> int:
        """Multiply two field symbols."""
        if a == 0 or b == 0:
            return 0
        return self._exp[self._log[a] + self._log[b]]

    # B019: the cache pins `self`, but instances are module-level
    # singletons that already live forever.
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


# Aztec Code mode message.
GF16_0x13 = BinaryExtensionGaloisField(0x13, size=16)  # x^4 + x + 1
# Aztec Code data (layers 1-2, 6-bit codewords).
GF64_0x43 = BinaryExtensionGaloisField(0x43, size=64)  # x^6 + x + 1
# QR Code data.
GF256_0x11D = BinaryExtensionGaloisField(0x11D)  # x^8 + x^4 + x^3 + x^2 + 1
# Data Matrix (ECC200) and Aztec Code (data layers 3-8, 8-bit codewords).
GF256_0x12D = BinaryExtensionGaloisField(0x12D)  # x^8 + x^5 + x^3 + x^2 + 1
# Aztec Code data (layers 9-22, 10-bit codewords).
GF1024_0x409 = BinaryExtensionGaloisField(0x409, size=1024)  # x^10 + x^3 + 1
# Aztec Code data (layers 23-32, 12-bit codewords).
GF4096_0x1069 = BinaryExtensionGaloisField(0x1069, size=4096)  # x^12 + x^6 + x^5 + x^3 + 1


class _ScaledGenerator:
    """Packed multiples of a Reed-Solomon generator, one big int per lead.

    For a fixed generator, :meth:`packed` returns ``[mul(lead, gen[j]) for j]``
    with each product in its own byte-aligned lane, highest power first. XORing
    that into the packed remainder is the encoder's whole inner loop done as one
    carry-free big-int operation. Lanes are byte-aligned (1 byte for fields up
    to 256 symbols, 2 bytes beyond) so the packed values build with
    :func:`int.from_bytes`; they are computed lazily per ``lead`` and cached.
    """

    def __init__(self, field: BinaryExtensionGaloisField, num_ec: int, first_root: int) -> None:
        self._exp = field._exp
        self._log = field._log
        self.lane_bytes = 1 if field.size <= 256 else 2
        gen = field.generator_coefficients(num_ec, first_root=first_root)
        # -1 marks a zero coefficient: its lane is always 0, and ``_log[0]`` is
        # not a real logarithm so it must not go through the exp table.
        self._log_gen = [self._log[g] if g else -1 for g in gen]
        self._packed: dict[int, int] = {}

    def packed(self, lead: int) -> int:
        """Scaled generator for ``lead`` as a packed big int (lead != 0)."""
        value = self._packed.get(lead)
        if value is None:
            exp = self._exp
            base = self._log[lead]
            if self.lane_bytes == 1:
                raw = bytes(exp[base + lg] if lg >= 0 else 0 for lg in self._log_gen)
            else:
                raw = b"".join(
                    (exp[base + lg] if lg >= 0 else 0).to_bytes(2, "big") for lg in self._log_gen
                )
            self._packed[lead] = value = int.from_bytes(raw, "big")
        return value


@functools.cache
def _scaled_generator(
    field: BinaryExtensionGaloisField, num_ec: int, first_root: int
) -> _ScaledGenerator:
    """One cached :class:`_ScaledGenerator` per (field, num_ec, first_root)."""
    return _ScaledGenerator(field, num_ec, first_root)


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

    The remainder is carried in a single big int -- one byte-aligned lane per
    symbol -- so each division step XORs a whole scaled generator in one
    operation instead of looping over ``num_ec`` field multiplies. Field
    addition is XOR, which never carries between lanes, so the packed form is
    exact. :func:`simple_reed_solomon_encode` is the plain equivalent this is
    checked against.

    :param data: Data symbols, highest power first.
    :param field: The field to do arithmetic in.
    :param num_ec: How many EC bytes to produce.
    :param first_root: Forwarded to :meth:`BinaryExtensionGaloisField.generator_coefficients`.
    :returns: EC bytes, length ``num_ec``, highest power first.
    """
    data_len = len(data)
    if data_len == 0:
        return [0] * num_ec
    scaled = _scaled_generator(field, num_ec, first_root)
    lb = scaled.lane_bytes
    lane_bits = 8 * lb
    mask = (1 << lane_bits) - 1

    if lb == 1:
        buffer = int.from_bytes(bytes(data), "big") << (lane_bits * num_ec)
    else:
        buffer = int.from_bytes(b"".join(d.to_bytes(lb, "big") for d in data), "big")
        buffer <<= lane_bits * num_ec

    packed = scaled.packed
    top = lane_bits * (data_len + num_ec - 1)  # shift of the leading (MSB) lane
    for i in range(data_len):
        lead = (buffer >> (top - lane_bits * i)) & mask
        if lead:
            buffer ^= packed(lead) << (lane_bits * (data_len - 1 - i))

    tail = (buffer & ((1 << (lane_bits * num_ec)) - 1)).to_bytes(lb * num_ec, "big")
    if lb == 1:
        return list(tail)
    return [int.from_bytes(tail[k : k + lb], "big") for k in range(0, lb * num_ec, lb)]


def simple_reed_solomon_encode(
    data: Sequence[int],
    field: BinaryExtensionGaloisField,
    num_ec: int,
    *,
    first_root: int = 0,
) -> list[int]:
    """Textbook Reed-Solomon EC bytes, kept as the reference for the fast path.

    Plain synthetic division using only :meth:`BinaryExtensionGaloisField.mul`,
    with no lane packing -- obviously correct and independent of the tricks in
    :func:`reed_solomon_encode`, which the tests hold equal to this. Not used at
    runtime. Arguments and return value match :func:`reed_solomon_encode`.
    """
    gen = field.generator_coefficients(num_ec, first_root=first_root)
    data_len = len(data)
    buffer = list(data) + [0] * num_ec
    for i in range(data_len):
        lead = buffer[i]
        if lead:
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
    # Reduce the leading coefficient on read and defer the per-cell modulo to
    # the return: the running entries stay congruent mod p, so the quotient
    # digits -- and hence the remainder -- are identical, at one modulo per row
    # instead of one per cell.
    for i in range(data_len):
        lead = buffer[i] % p
        if lead:
            offset = i + 1
            for j in range(num_ec):
                buffer[offset + j] -= lead * gen[j]
    return [(p - r) % p for r in buffer[data_len:]]
