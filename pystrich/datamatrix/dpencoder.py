"""DataMatrix high-level encoder — picks the shortest mode sequence.

Dynamic programming over ``(mode, position, phase)`` states across the
four implemented encodation modes (ASCII, C40, Text, X12). C40/Text/X12
pack three set-values into two codewords, so ``phase`` tracks the
in-flight position within a triplet (always 0 in ASCII). Costs are kept
in thirds of a codeword so the integer DP cleanly handles the 2/3-per-char
density of C40/Text/X12.

The output is a flat ``list[int]`` of codewords ready for the existing
padding and Reed-Solomon stages in :mod:`pystrich.datamatrix.textencoder`.
"""

from __future__ import annotations

from collections.abc import Callable
from itertools import groupby
from operator import itemgetter

from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidPayloadLength

from .modes import (
    ALL_MODES,
    ASCII,
    ASCII_COST,
    C40,
    C40_COUNT,
    C40_EMIT,
    CLOSE_COST,
    LATCH,
    TEXT,
    TEXT_COUNT,
    TEXT_EMIT,
    UNLATCH,
    X12,
    X12_VALUE,
)

_INF = 10**18

# Switching into a non-ASCII mode pays one codeword (3 thirds) for its latch.
# ASCII is the base mode and has no header.
_HEADER: tuple[int, ...] = (0, 3, 3, 3)


def encode_high_level(payload: bytes, *, eci: int | None = None) -> list[int]:
    """Encode ``payload`` to a codeword list, optionally with an ECI prologue.

    :param payload: input bytes.
    :param eci: ECI number to prepend, or ``None`` to omit the prologue.
    :returns: codeword list ready to hand to the padding stage.
    """
    return _HighLevelEncoder(payload, eci).encode()


def _eci_emission(eci: int) -> list[int]:
    """Build the ECI prologue: codeword 241 followed by the single-codeword designator."""
    if not 0 <= eci <= 126:
        raise PyStrichInvalidInput(f"ECI {eci} out of range 0..126")
    return [241, eci + 1]


def _pack_byte_by_byte(payload: bytes) -> list[int]:
    """ASCII-mode codewords: digit-pair packing and Upper Shift for high bytes."""
    out: list[int] = []
    i = 0
    n = len(payload)
    while i < n:
        b = payload[i]
        if i + 1 < n and 0x30 <= b <= 0x39 and 0x30 <= payload[i + 1] <= 0x39:
            # Digit pair: codewords 130..229 cover "00".."99" in one byte.
            out.append(130 + (b - 0x30) * 10 + (payload[i + 1] - 0x30))
            i += 2
        elif b > 127:
            # Upper Shift (235) escapes bytes 128..255 via (byte - 127).
            out.append(235)
            out.append(b - 127)
            i += 1
        else:
            # Plain ASCII: codeword = byte + 1 (so 0x00 -> 1, 0x7F -> 128).
            out.append(b + 1)
            i += 1
    return out


def _pack_triplets(set_values: list[int]) -> list[int]:
    """Pack 5-bit set-values into codeword pairs.

    Three values ``v1, v2, v3`` in ``0..39`` encode as the base-40 number
    ``v1*1600 + v2*40 + v3 + 1`` (range ``1..64000``, 16-bit), split
    MSB/LSB into two codewords. The ``+1`` keeps the packed value
    non-zero so an all-zero triplet doesn't collide with an unwritten
    codeword slot.
    """
    out: list[int] = []
    for i in range(0, len(set_values), 3):
        packed = 1600 * set_values[i] + 40 * set_values[i + 1] + set_values[i + 2] + 1
        out.append(packed >> 8)
        out.append(packed & 0xFF)
    return out


def _pack_emit_table(payload: bytes, emit_table: tuple[tuple[int, ...], ...]) -> list[int]:
    """Expand each byte via ``emit_table`` and pack the set-values into triplets."""
    set_values: list[int] = []
    for b in payload:
        set_values.extend(emit_table[b])
    return _pack_triplets(set_values)


def _pack_c40(payload: bytes) -> list[int]:
    return [LATCH[C40], *_pack_emit_table(payload, C40_EMIT), UNLATCH]


def _pack_text(payload: bytes) -> list[int]:
    return [LATCH[TEXT], *_pack_emit_table(payload, TEXT_EMIT), UNLATCH]


def _pack_x12(payload: bytes) -> list[int]:
    return [LATCH[X12], *_pack_triplets([X12_VALUE[b] for b in payload]), UNLATCH]


# Indexed by the mode constants from .modes — ASCII=0, C40=1, TEXT=2, X12=3.
_PACKERS: tuple[Callable[[bytes], list[int]], ...] = (
    _pack_byte_by_byte,
    _pack_c40,
    _pack_text,
    _pack_x12,
)


class _HighLevelEncoder:
    """Viterbi-style DP across ``(mode, position, phase)`` states.

    State indices: ``mode`` in ``{0:ASCII, 1:C40, 2:TEXT, 3:X12}``; ``pos``
    in ``[0, n]``; ``phase`` in ``{0, 1, 2}`` is the position within the
    current C40/Text/X12 triplet — 0 means "just closed a triplet, ready
    to emit", 1/2 means "one/two set-values buffered". Always 0 in ASCII.
    """

    def __init__(self, payload: bytes, eci: int | None) -> None:
        self.payload = payload
        self.n = len(payload)
        self.eci_emission: list[int] = _eci_emission(eci) if eci is not None else []
        eci_cost = 3 * len(self.eci_emission)
        # dp[mode][pos][phase] = minimum thirds to reach state.
        self.dp: list[list[list[int]]] = [
            [[_INF] * 3 for _ in range(self.n + 1)] for _ in ALL_MODES
        ]
        # prev[mode][pos][phase] = src_state | None. A 3D list parallel to dp
        # rather than a dict keyed by (mode, pos, phase): the DP relaxes each
        # state hundreds of thousands of times, and list indexing avoids
        # allocating and hashing a tuple key on every write and read.
        self.prev: list[list[list[tuple[int, int, int] | None]]] = [
            [[None] * 3 for _ in range(self.n + 1)] for _ in ALL_MODES
        ]
        # Seed every mode at pos 0: ASCII is free; non-ASCII pays its latch.
        for m in ALL_MODES:
            self.dp[m][0][0] = eci_cost + _HEADER[m]

    def encode(self) -> list[int]:
        for p in range(self.n + 1):
            self._relax_switches(p)
            if p < self.n:
                self._advance(p)
        return self._reconstruct()

    def _relax_switches(self, p: int) -> None:
        """Try every cross-mode switch at position ``p``.

        Closing the source phase + paying the destination's latch is a
        single relaxation per (src, dst) pair. Multi-hop chains at the same
        position are never cheaper than direct ones.
        """
        dp = self.dp
        prev = self.prev
        for m_src in ALL_MODES:
            close_src = CLOSE_COST[m_src]
            dp_src_p = dp[m_src][p]
            for phase in range(3):
                base = dp_src_p[phase] + close_src[phase]
                if base >= _INF:
                    continue
                src_state = (m_src, p, phase)
                for m_dst in ALL_MODES:
                    if m_dst == m_src:
                        continue
                    new_cost = base + _HEADER[m_dst]
                    if new_cost < dp[m_dst][p][0]:
                        dp[m_dst][p][0] = new_cost
                        prev[m_dst][p][0] = src_state

    def _advance(self, p: int) -> None:
        """Advance every reachable state at ``p`` by one (or two) byte(s)."""
        dp = self.dp
        prev = self.prev
        payload = self.payload
        byte = payload[p]

        # ASCII direct (and digit-pair when both this byte and the next are digits).
        cost = dp[ASCII][p][0]
        if cost < _INF:
            dp_ascii_next = dp[ASCII][p + 1]
            new_cost = cost + ASCII_COST[byte]
            if new_cost < dp_ascii_next[0]:
                dp_ascii_next[0] = new_cost
                prev[ASCII][p + 1][0] = (ASCII, p, 0)
            if p + 1 < self.n and 0x30 <= byte <= 0x39 and 0x30 <= payload[p + 1] <= 0x39:
                pair_cost = cost + 3
                if pair_cost < dp[ASCII][p + 2][0]:
                    dp[ASCII][p + 2][0] = pair_cost
                    prev[ASCII][p + 2][0] = (ASCII, p, 0)

        # C40 and TEXT share the same triplet-packing structure; only the
        # per-byte set-value count differs.
        for mode, count_table in ((C40, C40_COUNT), (TEXT, TEXT_COUNT)):
            set_values = count_table[byte]
            cost_per_byte = 2 * set_values
            phase_step = set_values % 3
            dp_mode_p = dp[mode][p]
            dp_mode_next = dp[mode][p + 1]
            prev_mode_next = prev[mode][p + 1]
            for phase in range(3):
                cost = dp_mode_p[phase]
                if cost >= _INF:
                    continue
                new_phase = (phase + phase_step) % 3
                new_cost = cost + cost_per_byte
                if new_cost < dp_mode_next[new_phase]:
                    dp_mode_next[new_phase] = new_cost
                    prev_mode_next[new_phase] = (mode, p, phase)

        # X12 (only for bytes in the X12 set).
        if X12_VALUE[byte] >= 0:
            dp_x12_p = dp[X12][p]
            dp_x12_next = dp[X12][p + 1]
            prev_x12_next = prev[X12][p + 1]
            for phase in range(3):
                cost = dp_x12_p[phase]
                if cost >= _INF:
                    continue
                new_phase = (phase + 1) % 3
                new_cost = cost + 2
                if new_cost < dp_x12_next[new_phase]:
                    dp_x12_next[new_phase] = new_cost
                    prev_x12_next[new_phase] = (X12, p, phase)

    def _reconstruct(self) -> list[int]:
        """Walk back-pointers from the cheapest end state and emit codewords."""
        best_cost = _INF
        best_state: tuple[int, int, int] | None = None
        for m in ALL_MODES:
            for phase in range(3):
                total = self.dp[m][self.n][phase] + CLOSE_COST[m][phase]
                if total < best_cost:
                    best_cost = total
                    best_state = (m, self.n, phase)
        if best_state is None:
            raise PyStrichInvalidPayloadLength("could not encode payload")

        chain: list[tuple[int, int, int]] = []
        cur: tuple[int, int, int] | None = best_state
        while cur is not None:
            chain.append(cur)
            m, pos, phase = cur
            cur = self.prev[m][pos][phase]
        chain.reverse()

        # Emit each maximal same-mode run as one segment. CLOSE_COST forbids
        # non-ASCII segments from ending at phase != 0, so every triplet-mode
        # segment is guaranteed to end on a triplet boundary.
        out: list[int] = list(self.eci_emission)
        for mode, group in groupby(chain, key=itemgetter(0)):
            positions = [pos for _, pos, _ in group]
            start, end = positions[0], positions[-1]
            out.extend(_PACKERS[mode](self.payload[start:end]))
        return out
