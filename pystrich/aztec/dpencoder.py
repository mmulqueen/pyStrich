"""Aztec high-level encoder — picks the shortest encodation for a byte payload.

Dynamic programming over (mode, position) states. From each state, the
encoder tries: direct character encoding, Punct digraph compression, single-
character shifts, multi-character latches (composed one hop at a time so the
DP finds the cheapest path), and Byte mode runs of 1..2047 bytes.

Byte runs are relaxed as they *close* at a position rather than enumerated by
length from each start, keeping the whole encode linear in the payload: a run
of ``j`` bytes ending at ``pos`` costs ``dp[start] + byte-shift + prefix(j) +
8j``, so for each length-prefix regime (1..31 bytes uses a 5-bit prefix,
32..2047 a 16-bit one) the cheapest start is a sliding-window minimum of
``dp[start] - 8*start`` maintained by a monotonic deque.

The output is an MSB-first bit list ready for the codeword chunker.
"""

from __future__ import annotations

from collections import deque

from pystrich.aztec.modes import (
    ALL_MODES,
    BYTE_SHIFT_CODEWORDS,
    BYTE_SHIFT_FROM,
    CHAR_BITS,
    CHAR_TABLE_DIGIT,
    CHAR_TABLES,
    LATCH_BY_SRC,
    PUNCT_DIGRAPHS,
    SHIFT_BY_SRC,
    P,
    U,
)
from pystrich.bitstream import BitStream
from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidPayloadLength

_INF = 10**18
_MAX_BYTE_RUN = 2047

# Byte-run length regimes: (shortest run, longest run, length-prefix bits).
# 1..31 bytes carry a 5-bit length; 32.. carry a 5-bit escape plus 11-bit count.
_BYTE_REGIMES = ((1, 31, 5), (32, _MAX_BYTE_RUN, 16))

Emission = list[tuple[int, int]]

# DP state key: (mode, position). A plain tuple rather than a NamedTuple -- it is
# only ever a dict key, never attribute-accessed, and construction is on the hot
# path, so the tuple literal ``(mode, pos)`` avoids the NamedTuple ``__new__``.
State = tuple[str, int]


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
        start: State = (U, 0)
        # dp[state] = minimum bits to reach this state.
        # prev[state] = (source state, emission to get here).
        self.dp: dict[State, int] = {start: eci_cost}
        self.prev: dict[State, tuple[State | None, Emission]] = {start: (None, eci_em)}

        # Sliding-window state for closing Byte-mode runs. For each byte-capable
        # caller mode, ``_byte_start_term`` holds ``dp[(mode, start)] -
        # 8*start`` at every reachable start -- the part of a run's cost that
        # depends only on where it starts. ``_byte_windows`` keeps one monotonic
        # deque per length regime holding the in-window starts, cheapest at the
        # front, so each close is a sliding-window minimum of that term.
        self._byte_modes = tuple(m for m in ALL_MODES if m in BYTE_SHIFT_FROM)
        self._byte_start_term: dict[str, dict[int, int]] = {m: {} for m in self._byte_modes}
        self._byte_windows: dict[str, list[deque[int]]] = {
            m: [deque() for _ in _BYTE_REGIMES] for m in self._byte_modes
        }

    def encode(self) -> list[int]:
        for pos in range(self.n + 1):
            self._byte_mode_close(pos)
            self._close_latches(pos)
            self._record_byte_starts(pos)
            if pos == self.n:
                continue
            for mode in ALL_MODES:
                if (mode, pos) not in self.dp:
                    continue
                self._direct_encode(mode, pos)
                self._punct_digraph(mode, pos)
                self._shifts(mode, pos)
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
                src: State = (mode, pos)
                cost = self.dp.get(src)
                if cost is None:
                    continue
                for dst_mode, cw_val, cw_bits in LATCH_BY_SRC[mode]:
                    if self._relax((dst_mode, pos), cost + cw_bits, src, [(cw_val, cw_bits)]):
                        changed = True

    def _direct_encode(self, mode: str, pos: int) -> None:
        """Emit the current byte as a single codeword in ``mode``, if possible."""
        byte = self.payload[pos]
        if byte not in CHAR_TABLES[mode]:
            return
        cw = CHAR_TABLES[mode][byte]
        bits = CHAR_BITS[mode]
        src: State = (mode, pos)
        self._relax((mode, pos + 1), self.dp[src] + bits, src, [(cw, bits)])

    def _punct_digraph(self, mode: str, pos: int) -> None:
        """In Punct mode, try compressing the current byte pair into one codeword."""
        if mode != P or pos + 1 >= self.n:
            return
        pair = (self.payload[pos], self.payload[pos + 1])
        if pair not in PUNCT_DIGRAPHS:
            return
        cw = PUNCT_DIGRAPHS[pair]
        src: State = (P, pos)
        self._relax((P, pos + 2), self.dp[src] + 5, src, [(cw, 5)])

    def _shifts(self, mode: str, pos: int) -> None:
        """Try every shift edge out of ``mode``: shift + char (or shift + digraph)."""
        byte = self.payload[pos]
        src: State = (mode, pos)
        cost = self.dp[src]
        for dst_mode, shift_cw, shift_bits in SHIFT_BY_SRC[mode]:
            if byte in CHAR_TABLES[dst_mode]:
                char_cw = CHAR_TABLES[dst_mode][byte]
                char_bits = CHAR_BITS[dst_mode]
                self._relax(
                    (mode, pos + 1),
                    cost + shift_bits + char_bits,
                    src,
                    [(shift_cw, shift_bits), (char_cw, char_bits)],
                )
            if dst_mode == P and pos + 1 < self.n:
                pair = (byte, self.payload[pos + 1])
                if pair in PUNCT_DIGRAPHS:
                    cw = PUNCT_DIGRAPHS[pair]
                    self._relax(
                        (mode, pos + 2),
                        cost + shift_bits + 5,
                        src,
                        [(shift_cw, shift_bits), (cw, 5)],
                    )

    def _record_byte_starts(self, pos: int) -> None:
        """Note that a byte run may start at ``pos`` in each byte-capable mode.

        Stores the start-only part of a run's cost, ``dp[start] - 8*start``, so
        :meth:`_byte_mode_close` can pick the cheapest start with a plain
        sliding-window minimum -- the shared ``8*pos`` and prefix terms cancel.
        """
        for m in self._byte_modes:
            src: State = (m, pos)
            if src in self.dp:
                self._byte_start_term[m][pos] = self.dp[src] - 8 * pos

    def _byte_mode_close(self, pos: int) -> None:
        """Relax every Byte-mode run ending at ``pos``, for each caller mode.

        A run of ``j = pos - start`` bytes costs ``dp[start] + byte-shift +
        prefix(j) + 8j``. Within each length regime the cheapest start is the
        front of a monotonic deque of the starts currently in range: a start
        enters when its offset reaches the regime's shortest run and leaves once
        the offset passes the longest.
        """
        for m in self._byte_modes:
            term = self._byte_start_term[m]
            bs_cw, bs_bits = BYTE_SHIFT_CODEWORDS[m]
            best_cost, best_start = _INF, -1

            for window, (shortest, longest, prefix_bits) in zip(
                self._byte_windows[m], _BYTE_REGIMES, strict=True
            ):
                entering = pos - shortest
                if entering in term:
                    while window and term[window[-1]] >= term[entering]:
                        window.pop()
                    window.append(entering)
                while window and window[0] < pos - longest:
                    window.popleft()
                if window:
                    cost = bs_bits + prefix_bits + 8 * pos + term[window[0]]
                    if cost < best_cost:
                        best_cost, best_start = cost, window[0]

            if best_start < 0:
                continue

            j = pos - best_start
            if j <= 31:
                prefix: Emission = [(bs_cw, bs_bits), (j, 5)]
            else:
                prefix = [(bs_cw, bs_bits), (0, 5), (j - 31, 11)]
            emission = prefix + self.payload_emission[best_start:pos]
            self._relax((m, pos), best_cost, (m, best_start), emission)

    def _reconstruct(self) -> list[int]:
        """Walk back-pointers from the cheapest end state and concatenate emissions."""
        end_cost = _INF
        end_mode = U
        for mode in ALL_MODES:
            c = self.dp.get((mode, self.n), _INF)
            if c < end_cost:
                end_cost = c
                end_mode = mode
        if end_cost == _INF:
            raise PyStrichInvalidPayloadLength("could not encode payload")

        emissions: list[Emission] = []
        state: State | None = (end_mode, self.n)
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
