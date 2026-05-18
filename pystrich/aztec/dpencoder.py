"""Aztec high-level encoder — picks the shortest encodation for a byte payload.

Dynamic programming over (mode, position) states. From each state, the
encoder tries: direct character encoding, Punct digraph compression, single-
character shifts, multi-character latches (composed one hop at a time so the
DP finds the cheapest path), and Byte mode runs of 1..2047 bytes.

The output is an MSB-first bit list ready for the codeword chunker.
"""

from __future__ import annotations

from typing import NamedTuple

from pystrich.aztec.modes import (
    ALL_MODES,
    BYTE_SHIFT_CODEWORDS,
    BYTE_SHIFT_FROM,
    CHAR_BITS,
    CHAR_TABLE_DIGIT,
    CHAR_TABLES,
    LATCH_CODEWORDS,
    PUNCT_DIGRAPHS,
    SHIFT_CODEWORDS,
    P,
    U,
)
from pystrich.bitstream import BitStream
from pystrich.exceptions import PyStrichInvalidInput

_INF = 10**18
_MAX_BYTE_RUN = 2047

Emission = list[tuple[int, int]]


class State(NamedTuple):
    mode: str
    pos: int


def _eci_emission(eci: int) -> Emission:
    """Build the FLG(n) ECI prologue for the given ECI number.

    Sequence (assuming we are in Upper): P/S (5 bits) + FLG (5 bits) +
    n (3 bits) + n Digit codewords (4 bits each).
    Encoding auto-returns to Upper afterwards.
    """
    digits = str(eci)
    n = len(digits)
    if not 1 <= n <= 6:
        raise PyStrichInvalidInput(f"ECI {eci} requires 1..6 digits; got {n}")
    emission: Emission = [(0, 5), (0, 5), (n, 3)]
    for d in digits:
        emission.append((CHAR_TABLE_DIGIT[ord(d)], 4))
    return emission


def encode_high_level(payload: bytes, *, eci: int | None = None) -> list[int]:
    """Encode the byte payload to an MSB-first bit list using Aztec's modes.

    :param payload: input bytes.
    :param eci: ECI number to prepend as an FLG(n) prologue, or ``None``.
    :returns: bit list, MSB-first.
    """
    return _HighLevelEncoder(payload, eci).encode()


class _HighLevelEncoder:
    """Viterbi-style DP across ``(mode, position)`` states.

    Each transition method considers one kind of edge out of the current
    state and calls :meth:`_relax` to record it if it improves the cost.
    """

    def __init__(self, payload: bytes, eci: int | None) -> None:
        self.payload = payload
        self.payload_emission: Emission = [(b, 8) for b in payload]
        self.n = len(payload)
        eci_em: Emission = _eci_emission(eci) if eci is not None else []
        eci_cost = sum(w for _, w in eci_em)
        start = State(U, 0)
        # dp[state] = minimum bits to reach this state.
        # prev[state] = (source state, emission to get here).
        self.dp: dict[State, int] = {start: eci_cost}
        self.prev: dict[State, tuple[State | None, Emission]] = {start: (None, eci_em)}

    def encode(self) -> list[int]:
        for pos in range(self.n + 1):
            self._close_latches(pos)
            if pos == self.n:
                continue
            for mode in ALL_MODES:
                if State(mode, pos) not in self.dp:
                    continue
                self._direct_encode(mode, pos)
                self._punct_digraph(mode, pos)
                self._shifts(mode, pos)
                self._byte_mode(mode, pos)
        return self._reconstruct()

    def _relax(self, state: State, new_cost: int, src_state: State, emission: Emission) -> bool:
        """Record ``state`` as reachable from ``src_state`` if this path is cheaper."""
        if new_cost < self.dp.get(state, _INF):
            self.dp[state] = new_cost
            self.prev[state] = (src_state, emission)
            return True
        return False

    def _close_latches(self, pos: int) -> None:
        """Relax every latch edge at ``pos`` until no costs change.

        Composes multi-hop paths (e.g. U->M->P) since each pass picks up
        latches whose source state was lowered by the previous pass.
        """
        changed = True
        while changed:
            changed = False
            for mode in ALL_MODES:
                src = State(mode, pos)
                if src not in self.dp:
                    continue
                cost = self.dp[src]
                for (src_mode, dst_mode), (cw_val, cw_bits) in LATCH_CODEWORDS.items():
                    if src_mode != mode:
                        continue
                    if self._relax(State(dst_mode, pos), cost + cw_bits, src, [(cw_val, cw_bits)]):
                        changed = True

    def _direct_encode(self, mode: str, pos: int) -> None:
        """Emit the current byte as a single codeword in ``mode``, if possible."""
        byte = self.payload[pos]
        if byte not in CHAR_TABLES[mode]:
            return
        cw = CHAR_TABLES[mode][byte]
        bits = CHAR_BITS[mode]
        src = State(mode, pos)
        self._relax(State(mode, pos + 1), self.dp[src] + bits, src, [(cw, bits)])

    def _punct_digraph(self, mode: str, pos: int) -> None:
        """In Punct mode, try compressing the current byte pair into one codeword."""
        if mode != P or pos + 1 >= self.n:
            return
        pair = (self.payload[pos], self.payload[pos + 1])
        if pair not in PUNCT_DIGRAPHS:
            return
        cw = PUNCT_DIGRAPHS[pair]
        src = State(P, pos)
        self._relax(State(P, pos + 2), self.dp[src] + 5, src, [(cw, 5)])

    def _shifts(self, mode: str, pos: int) -> None:
        """Try every shift edge out of ``mode``: shift + char (or shift + digraph)."""
        byte = self.payload[pos]
        src = State(mode, pos)
        cost = self.dp[src]
        for (src_mode, dst_mode), (shift_cw, shift_bits) in SHIFT_CODEWORDS.items():
            if src_mode != mode:
                continue
            if byte in CHAR_TABLES[dst_mode]:
                char_cw = CHAR_TABLES[dst_mode][byte]
                char_bits = CHAR_BITS[dst_mode]
                self._relax(
                    State(mode, pos + 1),
                    cost + shift_bits + char_bits,
                    src,
                    [(shift_cw, shift_bits), (char_cw, char_bits)],
                )
            if dst_mode == P and pos + 1 < self.n:
                pair = (byte, self.payload[pos + 1])
                if pair in PUNCT_DIGRAPHS:
                    cw = PUNCT_DIGRAPHS[pair]
                    self._relax(
                        State(mode, pos + 2),
                        cost + shift_bits + 5,
                        src,
                        [(shift_cw, shift_bits), (cw, 5)],
                    )

    def _byte_mode(self, mode: str, pos: int) -> None:
        """Try Byte mode runs of 1..2047 bytes starting at ``pos``.

        Runs of 1..31 use a 5-bit length prefix; longer runs use a 5+11 prefix.
        Inlines the relax check so the per-k emission is only built when accepted.
        """
        if mode not in BYTE_SHIFT_FROM:
            return
        bs_cw, bs_bits = BYTE_SHIFT_CODEWORDS[mode]
        src = State(mode, pos)
        cost_here = self.dp[src]
        max_k = min(_MAX_BYTE_RUN, self.n - pos)
        for k in range(1, max_k + 1):
            length_bits = 5 if k <= 31 else 16
            new_cost = cost_here + bs_bits + length_bits + 8 * k
            dst = State(mode, pos + k)
            if new_cost >= self.dp.get(dst, _INF):
                continue
            if k <= 31:
                prefix: Emission = [(bs_cw, bs_bits), (k, 5)]
            else:
                prefix = [(bs_cw, bs_bits), (0, 5), (k - 31, 11)]
            self.dp[dst] = new_cost
            self.prev[dst] = (src, prefix + self.payload_emission[pos : pos + k])

    def _reconstruct(self) -> list[int]:
        """Walk back-pointers from the cheapest end state and concatenate emissions."""
        end_cost = _INF
        end_mode = U
        for mode in ALL_MODES:
            c = self.dp.get(State(mode, self.n), _INF)
            if c < end_cost:
                end_cost = c
                end_mode = mode
        if end_cost == _INF:
            raise PyStrichInvalidInput("could not encode payload")

        emissions: list[Emission] = []
        state: State | None = State(end_mode, self.n)
        while state is not None:
            src_state, emission = self.prev[state]
            emissions.append(emission)
            state = src_state
        emissions.reverse()

        stream = BitStream()
        for emission in emissions:
            for value, width in emission:
                stream.append(value, width)
        return stream.data
