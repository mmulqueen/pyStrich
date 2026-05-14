"""Tests for the unified Reed-Solomon module.

Reed-Solomon error correction is built in two layers, and the tests below
mirror that split:

1. **A Galois field GF(256)** — arithmetic on bytes where addition is XOR and
   multiplication wraps via a "primitive" polynomial that fixes how values
   behave past 255. The field tests verify this arithmetic obeys the algebraic
   laws the encoder relies on (zero is absorbing, one is the identity, addition
   distributes over multiplication, the wraparound matches the chosen primitive,
   and the precomputed log/exp tables are consistent).

2. **The encoder** — produces error-correction bytes by polynomial long
   division over the field. ``test_codeword_is_zero_at_generator_roots``
   verifies the defining property of a Reed-Solomon codeword, so the encoder is
   checked against the spec definition rather than against its own output.
"""

import random

import pytest

from pystrich.reedsolomon import (
    GF929,
    BinaryExtensionGaloisField,
    GF256_0x11D,
    GF256_0x12D,
    PrimeGaloisField,
    reed_solomon_encode,
    reed_solomon_encode_pdf417,
)


@pytest.mark.parametrize("primitive", [0x11D, 0x12D])
def test_galois_field_log_exp_round_trip(primitive):
    """The exp and log lookup tables are inverses for every non-zero byte."""
    field = BinaryExtensionGaloisField(primitive)
    for x in range(1, field.size):
        assert field._exp[field._log[x]] == x


@pytest.mark.parametrize("field", [GF256_0x11D, GF256_0x12D])
@pytest.mark.parametrize("a", [0, 1, 2, 7, 128, 255])
def test_galois_field_mul_by_zero(field, a):
    """Anything multiplied by zero is zero."""
    assert field.mul(a, 0) == 0
    assert field.mul(0, a) == 0


@pytest.mark.parametrize("field", [GF256_0x11D, GF256_0x12D])
@pytest.mark.parametrize("a", [1, 2, 7, 128, 255])
def test_galois_field_mul_identity(field, a):
    """Anything multiplied by one is itself."""
    assert field.mul(a, 1) == a
    assert field.mul(1, a) == a


@pytest.mark.parametrize(
    "field, expected",
    [
        pytest.param(GF256_0x11D, 0x1D, id="GF256_0x11D"),
        pytest.param(GF256_0x12D, 0x2D, id="GF256_0x12D"),
    ],
)
def test_galois_field_wraps_via_primitive_polynomial(field, expected):
    """Multiplications that overflow a byte wrap using the primitive polynomial.

    ``2 * 128 = 256`` doesn't fit in 8 bits, so the field replaces the overflowed
    bit with the primitive polynomial's low byte (``0x1D`` or ``0x2D`` depending
    on which polynomial defines the field). This is the whole reason the
    primitive polynomial is a constructor parameter.
    """
    assert field.mul(2, 128) == expected
    assert field.mul(128, 2) == expected


@pytest.mark.parametrize("field", [GF256_0x11D, GF256_0x12D])
def test_galois_field_distributivity(field):
    """Multiplication distributes over addition: ``a * (b + c) == a*b + a*c``.

    Addition here is XOR, so the property reads
    ``mul(a, b ^ c) == mul(a, b) ^ mul(a, c)``. Sampled on random triples.
    """
    rng = random.Random(0)
    for _ in range(200):
        a, b, c = rng.randrange(256), rng.randrange(256), rng.randrange(256)
        assert field.mul(a, b ^ c) == field.mul(a, b) ^ field.mul(a, c)


def test_reed_solomon_encode_zero_data_returns_zero_ec():
    """Encoding all-zero data produces all-zero error-correction bytes."""
    assert reed_solomon_encode([0] * 10, GF256_0x11D, num_ec=5) == [0] * 5


def _eval_poly(coeffs, x, field):
    """Evaluate the polynomial with these coefficients at ``x`` (Horner's method).

    ``coeffs`` is highest-degree-first: ``[c_n, ..., c_1, c_0]`` represents
    ``c_n * x^n + ... + c_1 * x + c_0``. Returns the single value of the
    polynomial at ``x``, computed using field arithmetic.
    """
    result = 0
    for c in coeffs:
        result = field.mul(result, x) ^ c
    return result


@pytest.mark.parametrize(
    "field, first_root",
    [
        pytest.param(GF256_0x11D, 0, id="QR-GF256_0x11D"),
        pytest.param(GF256_0x12D, 1, id="DM-GF256_0x12D"),
    ],
)
@pytest.mark.parametrize("num_ec", [5, 10, 14, 28, 68])
def test_codeword_is_zero_at_generator_roots(field, first_root, num_ec):
    """Encoded codewords satisfy the defining equation of a Reed-Solomon code.

    A Reed-Solomon codeword is the polynomial
    ``c(x) = data(x) * x^num_ec + ec(x)``, and it is defined by the property
    that ``c`` evaluates to zero at every root of the generator polynomial.
    Those roots are ``a^first_root, a^(first_root+1), ...``, where ``a = 2`` is
    the field's primitive element.

    This check is non-circular: the encoder produces ``ec`` by polynomial long
    division, while this test evaluates the resulting codeword (a different
    computation) at the roots. The two agree only if the encoder is correct.
    """
    rng = random.Random(0)
    data = [rng.randrange(256) for _ in range(50)]
    codeword = data + reed_solomon_encode(data, field, num_ec, first_root=first_root)
    for k in range(num_ec):
        root = field._exp[(first_root + k) % (field.size - 1)]
        assert _eval_poly(codeword, root, field) == 0


# PDF417 -- Reed-Solomon over the prime field GF(929)


def test_prime_galois_field_basic_arithmetic():
    """Sanity check: GF(929) modular arithmetic and its primitive element."""
    f = PrimeGaloisField(929, primitive=3)
    assert f.prime == 929
    # 3 is a primitive root mod 929: powers 3^0..3^927 cover every non-zero
    # field element exactly once.
    seen = {pow(3, i, 929) for i in range(928)}
    assert len(seen) == 928
    assert 0 not in seen


# Generator polynomial coefficients pulled verbatim from the spec for
# error correction levels 0..4. The spec lists them lowest-power-first
# (constant term first); the encoder returns them highest-power-first,
# so the comparison reverses one of them.
# fmt: off
SPEC_LOW_LEVELS = {
    0: [27, 917],
    1: [522, 568, 723, 809],
    2: [237, 308, 436, 284, 646, 653, 428, 379],
    3: [274, 562, 232, 755, 599, 524, 801, 132, 295, 116, 442, 428, 295, 42, 176, 65],
    4: [361, 575, 922, 525, 176, 586, 640, 321, 536, 742, 677, 742, 687, 284, 193, 517,
        273, 494, 263, 147, 593, 800, 571, 320, 803, 133, 231, 390, 685, 330, 63, 410],
}
# fmt: on


@pytest.mark.parametrize(
    "ecl, expected_low_first",
    list(SPEC_LOW_LEVELS.items()),
    ids=lambda v: f"ECL{v}" if isinstance(v, int) else "spec",
)
def test_pdf417_generator_coefficients_match_spec(ecl, expected_low_first):
    """``generator_coefficients`` reproduces the spec's coefficient tables.

    The spec lists coefficients lowest-power-first; the encoder returns
    them highest-power-first, so the comparison reverses one of them.
    """
    num_ec = 2 ** (ecl + 1)
    coeffs = GF929.generator_coefficients(num_ec, first_root=1)
    assert list(coeffs) == list(reversed(expected_low_first))


def test_pdf417_reed_solomon_encode_matches_spec_worked_example():
    """Spec worked example: data [5, 453, 178, 121, 239] at ECL 1 produces [452, 327, 657, 619].

    This is the spec's only fully traced worked example. The encoder's
    output is the four EC codewords appended after the data; the codeword
    polynomial is then zero at every root of the generator polynomial
    (verified in the next test).
    """
    data = [5, 453, 178, 121, 239]
    ec = reed_solomon_encode_pdf417(data, num_ec=4)
    assert ec == [452, 327, 657, 619]


@pytest.mark.parametrize("ecl, num_ec", [(0, 2), (1, 4), (2, 8), (3, 16), (4, 32)])
def test_pdf417_codeword_is_zero_at_generator_roots(ecl, num_ec):
    """A PDF417 codeword is zero at every root of its generator polynomial.

    The defining property of a Reed-Solomon codeword is ``c(3^i) = 0``
    for ``i = 1..k``, independent of how the encoder produced the EC
    bytes. This evaluates the codeword polynomial via Horner's method
    and checks each root -- so the encoder is verified against the
    algebraic definition rather than its own output.
    """
    rng = random.Random(ecl)
    data = [rng.randrange(929) for _ in range(50)]
    ec = reed_solomon_encode_pdf417(data, num_ec=num_ec)
    codeword = data + ec
    for k in range(1, num_ec + 1):
        root = pow(3, k, 929)
        acc = 0
        for c in codeword:
            acc = (acc * root + c) % 929
        assert acc == 0, f"codeword non-zero at root 3^{k} = {root}"


@pytest.mark.parametrize(
    "data, num_ec, expected_ec",
    [
        pytest.param(
            [105, 106, 129],
            5,
            [74, 235, 130, 61, 159],
            id="datamatrix-hi-3data-5ec",
        ),
        pytest.param(
            [99, 98, 111, 98, 111, 98, 129, 56],
            10,
            [227, 236, 237, 109, 16, 221, 163, 60, 171, 76],
            id="datamatrix-banana-8data-10ec",
        ),
    ],
)
def test_reed_solomon_encode_datamatrix_vectors(data, num_ec, expected_ec):
    """Direct vector check of ECC200's GF(256)/0x12D + first_root=1 RS path."""
    assert reed_solomon_encode(data, GF256_0x12D, num_ec, first_root=1) == expected_ec
