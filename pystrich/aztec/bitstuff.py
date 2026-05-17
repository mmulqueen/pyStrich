"""Aztec bit-stuffing — chunk a bit stream into codewords avoiding all-0 / all-1 values.

Aztec treats all-0 and all-1 codewords as erasures, so the encoder rewrites
any codeword that would land on either value. The rule operates as the bit
stream is being chunked: if the first ``width - 1`` bits of a candidate
codeword are all 0, the codeword takes a dummy 1 at the LSB and the next
input bit starts the next codeword; if they're all 1, the dummy is 0. The
displaced bit pushes back into the stream rather than being lost.

The final partial codeword is right-padded with 1s; if that produces the
all-1 value, the LSB flips to 0.
"""

from __future__ import annotations

from collections.abc import Sequence


def _bits_to_int(bits: Sequence[int]) -> int:
    value = 0
    for b in bits:
        value = (value << 1) | b
    return value


def to_codewords(bits: Sequence[int], width: int) -> list[int]:
    """Chunk a bit sequence into ``width``-bit codewords with stuffing applied.

    :param bits: input bit sequence, MSB-first.
    :param width: codeword bit-width (6, 8, 10 or 12).
    :returns: codeword integer values, MSB-first within each codeword.
    """
    out: list[int] = []
    n = len(bits)
    i = 0
    forbidden_all_one = (1 << width) - 1

    while i < n:
        if i + width <= n:
            prefix = bits[i : i + width - 1]
            if all(b == 0 for b in prefix):
                out.append(_bits_to_int(prefix) << 1 | 1)
                i += width - 1
            elif all(b == 1 for b in prefix):
                out.append(_bits_to_int(prefix) << 1)
                i += width - 1
            else:
                out.append(_bits_to_int(bits[i : i + width]))
                i += width
        else:
            remaining = list(bits[i:])
            pad_count = width - len(remaining)
            cw = _bits_to_int(remaining + [1] * pad_count)
            if cw == forbidden_all_one:
                cw -= 1
            out.append(cw)
            i = n

    return out
