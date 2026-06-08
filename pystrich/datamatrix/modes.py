"""DataMatrix encodation-mode tables for the high-level DP encoder.

Four of the six encodation schemes are modelled here: ASCII (the default),
C40, Text and X12. EDIFACT and Base 256 are not implemented. C40, Text and
X12 each pack three set-values into two codewords. C40 and Text have a
basic set plus Shift 1/2/3 subsets; X12 is a flat 40-character set with no
shifts (so most bytes are unencodable in X12).

Cost unit throughout: *thirds of a codeword* — one codeword is 3 units,
one C40/Text/X12 set-value is 2 units (three pack into two codewords).
The DP that consumes these tables works in the same unit.
"""

from __future__ import annotations

# Mode indices into the DP's dp / prev tables.
ASCII = 0
C40 = 1
TEXT = 2
X12 = 3
ALL_MODES: tuple[int, ...] = (ASCII, C40, TEXT, X12)

# Latch codewords (ASCII has no latch — it's the base mode).
LATCH: tuple[int, ...] = (
    -1,  # ASCII
    230,  # Latch to C40
    239,  # Latch to TEXT
    238,  # Latch to X12
)
UNLATCH = 254

# Phase-0 close: a non-ASCII segment emits one Unlatch codeword (3 units)
# to return to ASCII. ASCII closes for free.
#
# Phase-2 close: the spec also allows padding the unfilled set-value with
# Shift 1, avoiding the Unlatch. Under the always-Unlatch packers used
# below, that route ties with the hybrid "unlatch here + finish the last
# byte in ASCII" route at the same cost, and the DP can already reach the
# hybrid via the phase-0 close. Model phase-2 as forbidden so the packers
# stay single-pathed.
#
# Phase 1 has no legal close in any mode.
_INF = 10**18
# fmt: off
CLOSE_COST: tuple[tuple[int, ...], ...] = (
    # phase:   0     1     2
    (          0, _INF, _INF),  # ASCII
    (          3, _INF, _INF),  # C40
    (          3, _INF, _INF),  # TEXT
    (          3, _INF, _INF),  # X12
)
# fmt: on


# Set-value layout for C40 and Text (5-bit values, 0..39):
#   value 0          — Shift 1 escape (followed by a set-1 value: ASCII 0..31)
#   value 1          — Shift 2 escape (followed by a set-2 value: punctuation,
#                       plus value 30 = Upper Shift for bytes 128..255)
#   value 2          — Shift 3 escape (followed by a set-3 value: case-flipped
#                       letters + braces/tilde/DEL; C40 lowercases, Text upper)
#   value 3          — space (direct)
#   values 4..13     — digits '0'..'9' (direct)
#   values 14..39    — the 26 'main' letters (direct; case differs per mode)
#
# X12 has no shifts; its 40 values are: 0=CR, 1='*', 2='>', 3=space,
# 4..13=digits, 14..39=A-Z. Anything else is unencodable in X12.


def _shift2_pairs() -> list[tuple[int, int]]:
    """ASCII byte ↔ Shift 2 value mapping shared by C40 and Text."""
    pairs: list[tuple[int, int]] = []
    # 33..47 ('!'..'/') → set values 0..14
    pairs += [(33 + i, i) for i in range(15)]
    # 58..64 (':'..'@') → set values 15..21
    pairs += [(58 + i, 15 + i) for i in range(7)]
    # 91..95 ('['..'_') → set values 22..26
    pairs += [(91 + i, 22 + i) for i in range(5)]
    return pairs


def _build_c40_emit() -> tuple[tuple[int, ...], ...]:
    """For each byte 0..255, the tuple of C40 set-values to emit for it."""
    out: list[tuple[int, ...]] = [()] * 256

    # Basic set (single value, no shift).
    out[32] = (3,)
    for d in range(10):
        out[48 + d] = (4 + d,)
    for u in range(26):
        out[65 + u] = (14 + u,)

    # Shift 1 set: ASCII control characters 0..31.
    for c in range(32):
        out[c] = (0, c)

    # Shift 2 set: punctuation and brackets.
    for ascii_v, set_v in _shift2_pairs():
        out[ascii_v] = (1, set_v)

    # Shift 3 set: backtick, lowercase, braces, tilde, DEL.
    out[96] = (2, 0)
    for low in range(26):
        out[97 + low] = (2, 1 + low)
    for i, b in enumerate(range(123, 128)):
        out[b] = (2, 27 + i)

    # Extended ASCII: Shift 2 + Upper Shift, then the encoding of (byte - 128).
    # Snapshot first — the splat reads base[hi-128] and would self-reference if it read out.
    base = list(out)
    for hi in range(128, 256):
        out[hi] = (1, 30, *base[hi - 128])

    return tuple(out)


def _build_text_emit() -> tuple[tuple[int, ...], ...]:
    """For each byte 0..255, the tuple of Text set-values to emit for it."""
    out: list[tuple[int, ...]] = [()] * 256

    # Basic set: space, digits, lowercase.
    out[32] = (3,)
    for d in range(10):
        out[48 + d] = (4 + d,)
    for low in range(26):
        out[97 + low] = (14 + low,)

    # Shift 1 set: ASCII control characters.
    for c in range(32):
        out[c] = (0, c)

    # Shift 2 set: punctuation and brackets (same mapping as C40).
    for ascii_v, set_v in _shift2_pairs():
        out[ascii_v] = (1, set_v)

    # Shift 3 set: backtick, uppercase, braces, tilde, DEL.
    out[96] = (2, 0)
    for up in range(26):
        out[65 + up] = (2, 1 + up)
    for i, b in enumerate(range(123, 128)):
        out[b] = (2, 27 + i)

    # Extended ASCII: Shift 2 + Upper Shift, then the encoding of (byte - 128).
    # Snapshot first — the splat reads base[hi-128] and would self-reference if it read out.
    base = list(out)
    for hi in range(128, 256):
        out[hi] = (1, 30, *base[hi - 128])

    return tuple(out)


def _build_x12_value() -> tuple[int, ...]:
    """For each byte 0..255, its X12 value, or -1 if not encodable in X12."""
    out: list[int] = [-1] * 256
    out[13] = 0  # CR
    out[42] = 1  # *
    out[62] = 2  # >
    out[32] = 3  # space
    for d in range(10):
        out[48 + d] = 4 + d
    for u in range(26):
        out[65 + u] = 14 + u
    return tuple(out)


C40_EMIT: tuple[tuple[int, ...], ...] = _build_c40_emit()
TEXT_EMIT: tuple[tuple[int, ...], ...] = _build_text_emit()
X12_VALUE: tuple[int, ...] = _build_x12_value()

# Per-byte set-value count (= cost in halves of a codeword pair).
# Cost in thirds = 2 * count.
C40_COUNT: tuple[int, ...] = tuple(len(e) for e in C40_EMIT)
TEXT_COUNT: tuple[int, ...] = tuple(len(e) for e in TEXT_EMIT)

# ASCII per-byte cost in thirds: 3 for the normal range, 6 for high bytes
# (Upper Shift codeword + value codeword).
ASCII_COST: tuple[int, ...] = tuple(3 if b <= 127 else 6 for b in range(256))
