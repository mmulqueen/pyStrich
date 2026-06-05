"""QR Code high-level encoder — picks the shortest segmentation.

Dynamic programming over ``(mode, position, phase)`` states. Each
position either continues the current segment or switches into a new
segment (paying the close cost of the leaving phase and the header of
the entering mode). The output is an MSB-first bit list ready for the
codeword packer.

The encoder is parametrised on the symbol's version bracket because the
character-count indicator width depends on bracket. ``encode_text``
re-runs the encoder once per bracket and picks the version that fits
into the smallest symbol.
"""

from __future__ import annotations

from itertools import groupby
from operator import itemgetter

from pystrich.bitstream import BitStream
from pystrich.exceptions import PyStrichInvalidInput

from .modes import (
    ALL_MODES,
    ALPHA,
    ALPHA_VALUE,
    BYTE,
    CHAR_COUNT_BITS,
    CLOSE_COST,
    KANJI,
    MODE_INDICATOR,
    NUM,
    kanji_value,
)

_INF = 10**18
_SHIFT_JIS_ECI = 20


def encode_high_level(
    payload: bytes,
    *,
    version_bracket: int,
    eci: int | None = None,
) -> list[int]:
    """Encode ``payload`` to an MSB-first bit list using QR's data modes.

    Kanji mode is offered to the DP only when ``eci`` is the Shift_JIS
    designator (20); under any other ECI, byte pairs that happen to fall
    in the kanji range go through byte mode instead.

    :param payload: input bytes.
    :param version_bracket: 0 for QR versions 1-9, 1 for 10-26, 2 for 27-40.
    :param eci: ECI number to prepend, or ``None`` for the default ECI.
    :returns: MSB-first bit list (no terminator; the caller appends one
        once the symbol size is chosen).
    """
    return _HighLevelEncoder(payload, version_bracket, eci).encode()


def _eci_emission(eci: int) -> list[tuple[int, int]]:
    """Build the ECI prologue: 4-bit mode indicator + 8/16/24-bit designator.

    The first one, two or three codewords following the indicator encode
    the ECI value; the number of leading ``1`` bits before the first ``0``
    selects the length.
    """
    if not 0 <= eci <= 999999:
        raise PyStrichInvalidInput(f"ECI {eci} out of range 0..999999")
    out: list[tuple[int, int]] = [(0b0111, 4)]
    if eci <= 127:
        out.append((eci, 8))
    elif eci <= 16383:
        out.append((0b10 << 14 | eci, 16))
    else:
        out.append((0b110 << 21 | eci, 24))
    return out


def _pack_numeric(data: bytes) -> list[tuple[int, int]]:
    """Pack ASCII digits: 3 → 10 bits, trailing 2 → 7 bits, trailing 1 → 4 bits."""
    out: list[tuple[int, int]] = []
    i = 0
    n = len(data)
    while i + 3 <= n:
        v = (data[i] - 0x30) * 100 + (data[i + 1] - 0x30) * 10 + (data[i + 2] - 0x30)
        out.append((v, 10))
        i += 3
    remaining = n - i
    if remaining == 2:
        out.append(((data[i] - 0x30) * 10 + (data[i + 1] - 0x30), 7))
    elif remaining == 1:
        out.append((data[i] - 0x30, 4))
    return out


def _pack_alpha(data: bytes) -> list[tuple[int, int]]:
    """Pack Alphanumeric: 2 chars → 11 bits, trailing 1 → 6 bits."""
    out: list[tuple[int, int]] = []
    i = 0
    n = len(data)
    while i + 2 <= n:
        out.append((ALPHA_VALUE[data[i]] * 45 + ALPHA_VALUE[data[i + 1]], 11))
        i += 2
    if n - i == 1:
        out.append((ALPHA_VALUE[data[i]], 6))
    return out


def _pack_byte(data: bytes) -> list[tuple[int, int]]:
    """Pack Byte mode: 8 bits per byte."""
    return [(b, 8) for b in data]


def _pack_kanji(data: bytes) -> list[tuple[int, int]]:
    """Pack Kanji mode: each Shift_JIS pair → 13 bits."""
    return [(kanji_value(data[i], data[i + 1]), 13) for i in range(0, len(data), 2)]  # type: ignore[misc]


# Indexed by the mode constants from .modes — NUM=0, ALPHA=1, BYTE=2, KANJI=3.
_PACKERS = (_pack_numeric, _pack_alpha, _pack_byte, _pack_kanji)


class _HighLevelEncoder:
    """Viterbi-style DP across ``(mode, position, phase)`` states.

    State indices: ``mode`` in ``{0:NUM, 1:ALPHA, 2:BYTE, 3:KANJI}``;
    ``pos`` in ``[0, n]``; ``phase`` is the number of chars buffered
    toward the in-flight Numeric triplet or Alphanumeric pair (0 for
    BYTE/KANJI and at segment boundaries).

    Under Shift_JIS (ECI 20), ``kanji[p]`` carries the 13-bit codeword
    for a kanji pair starting at ``p`` (or ``None``). Byte ``p + 1`` of
    such a pair is a "trail" — mode switches and non-BYTE advances are
    forbidden there so a kanji pair can't end up split across segments
    (which would leave an invalid stray lead byte in a BYTE segment).
    """

    def __init__(self, payload: bytes, version_bracket: int, eci: int | None) -> None:
        self.payload = payload
        self.n = len(payload)
        self.bracket = version_bracket
        kanji_enabled = eci == _SHIFT_JIS_ECI
        self.kanji: list[int | None] = (
            self._scan_kanji_pairs() if kanji_enabled else [None] * self.n
        )
        # Active mode set: KANJI is excluded outside Shift_JIS so its
        # states are neither seeded, relaxed, nor considered as end states.
        self.modes: tuple[int, ...] = ALL_MODES if kanji_enabled else (NUM, ALPHA, BYTE)
        self.eci_emission: list[tuple[int, int]] = _eci_emission(eci) if eci is not None else []
        eci_cost = sum(w for _, w in self.eci_emission)
        # Per-mode segment-header cost at this bracket: 4-bit mode indicator
        # + char-count indicator.
        self.header: tuple[int, ...] = tuple(
            4 + CHAR_COUNT_BITS[m][version_bracket] for m in ALL_MODES
        )
        # dp[mode][pos][phase] = minimum bits to reach state. Always sized
        # for ALL_MODES so indexing by mode value stays valid; unused mode
        # slots simply remain at _INF.
        self.dp: list[list[list[int]]] = [
            [[_INF] * 3 for _ in range(self.n + 1)] for _ in ALL_MODES
        ]
        # prev[(mode, pos, phase)] = src_state | None
        self.prev: dict[tuple[int, int, int], tuple[int, int, int] | None] = {}
        # Seed: open a fresh segment in each active mode at pos 0.
        for m in self.modes:
            self.dp[m][0][0] = eci_cost + self.header[m]
            self.prev[(m, 0, 0)] = None

    def _scan_kanji_pairs(self) -> list[int | None]:
        """Mark each byte position with its Kanji codeword if it leads a pair.

        Left-to-right so we skip a trailer after consuming its lead —
        otherwise a trailer byte numerically in lead range (e.g. 0x86
        after 中 = 0x9286) would be misread as starting its own pair.
        """
        out: list[int | None] = [None] * self.n
        p = 0
        while p < self.n - 1:
            v = kanji_value(self.payload[p], self.payload[p + 1])
            if v is not None:
                out[p] = v
                p += 2
            else:
                p += 1
        return out

    def _is_kanji_trail(self, p: int) -> bool:
        return 0 < p <= self.n and self.kanji[p - 1] is not None

    def encode(self) -> list[int]:
        for p in range(self.n + 1):
            self._relax_switches(p)
            if p < self.n:
                self._advance(p)
        return self._reconstruct()

    def _relax_switches(self, p: int) -> None:
        """Try every cross-mode switch at position ``p``.

        Switching from ``(m_src, p, phase)`` to ``(m_dst, p, 0)`` pays
        the close cost of the leaving phase plus the header of the
        entering mode. Multi-hop switches at the same position are never
        cheaper than direct switches, so a single pass suffices.
        Skipped at kanji-pair trail positions to keep a pair within one
        segment.
        """
        if self._is_kanji_trail(p):
            return
        for m_src in self.modes:
            for phase in range(3):
                base = self.dp[m_src][p][phase] + CLOSE_COST[m_src][phase]
                if base >= _INF:
                    continue
                src_state = (m_src, p, phase)
                for m_dst in self.modes:
                    if m_dst == m_src:
                        continue
                    new_cost = base + self.header[m_dst]
                    if new_cost < self.dp[m_dst][p][0]:
                        self.dp[m_dst][p][0] = new_cost
                        self.prev[(m_dst, p, 0)] = src_state

    def _advance(self, p: int) -> None:
        """Advance every reachable state at ``p`` by one byte in its mode.

        At a kanji-pair trail position only BYTE-mode continuation is
        permitted, keeping the two bytes of the pair in the same segment.
        """
        byte = self.payload[p]
        trail = self._is_kanji_trail(p)
        numeric = not trail and 0x30 <= byte <= 0x39
        alpha = not trail and ALPHA_VALUE[byte] >= 0

        # NUM continue: 3 digits pack into 10 bits, charged on the wrap to phase 0.
        # Intermediate digits look free because they're buffered into the current group.
        if numeric:
            for phase in range(3):
                cost = self.dp[NUM][p][phase]
                if cost >= _INF:
                    continue
                new_phase = (phase + 1) % 3
                new_cost = cost + (10 if new_phase == 0 else 0)
                if new_cost < self.dp[NUM][p + 1][new_phase]:
                    self.dp[NUM][p + 1][new_phase] = new_cost
                    self.prev[(NUM, p + 1, new_phase)] = (NUM, p, phase)

        # ALPHA continue: 2 chars pack into 11 bits, charged on the wrap to phase 0.
        if alpha:
            for phase in (0, 1):
                cost = self.dp[ALPHA][p][phase]
                if cost >= _INF:
                    continue
                new_phase = 1 - phase
                new_cost = cost + (11 if new_phase == 0 else 0)
                if new_cost < self.dp[ALPHA][p + 1][new_phase]:
                    self.dp[ALPHA][p + 1][new_phase] = new_cost
                    self.prev[(ALPHA, p + 1, new_phase)] = (ALPHA, p, phase)

        # BYTE continue: 8 bits per byte. Always available, even at trail positions.
        cost = self.dp[BYTE][p][0]
        if cost < _INF:
            new_cost = cost + 8
            if new_cost < self.dp[BYTE][p + 1][0]:
                self.dp[BYTE][p + 1][0] = new_cost
                self.prev[(BYTE, p + 1, 0)] = (BYTE, p, 0)

        # KANJI advance: skip over the trail byte; 13 bits per pair.
        if not trail and self.kanji[p] is not None:
            cost = self.dp[KANJI][p][0]
            if cost < _INF:
                new_cost = cost + 13
                if new_cost < self.dp[KANJI][p + 2][0]:
                    self.dp[KANJI][p + 2][0] = new_cost
                    self.prev[(KANJI, p + 2, 0)] = (KANJI, p, 0)

    def _reconstruct(self) -> list[int]:
        """Walk back-pointers, segment the chain, then emit bits."""
        # Pick the cheapest end state, accounting for trailing close cost.
        best_cost = _INF
        best_state: tuple[int, int, int] | None = None
        for m in self.modes:
            for phase in range(3):
                total = self.dp[m][self.n][phase] + CLOSE_COST[m][phase]
                if total < best_cost:
                    best_cost = total
                    best_state = (m, self.n, phase)
        assert best_state is not None, "BYTE mode always reaches the end state"

        # Walk back-pointers to recover the state chain.
        chain: list[tuple[int, int, int]] = []
        cur: tuple[int, int, int] | None = best_state
        while cur is not None:
            chain.append(cur)
            cur = self.prev[cur]
        chain.reverse()

        # Emit each maximal same-mode run as one segment: 4-bit mode indicator,
        # char-count indicator, then the packed payload. Kanji char-count is
        # byte-count / 2 (one count per pair); other modes count bytes.
        emission: list[tuple[int, int]] = list(self.eci_emission)
        for mode, group in groupby(chain, key=itemgetter(0)):
            positions = [pos for _, pos, _ in group]
            start, end = positions[0], positions[-1]
            char_count = (end - start) // 2 if mode == KANJI else end - start
            emission.append((MODE_INDICATOR[mode], 4))
            emission.append((char_count, CHAR_COUNT_BITS[mode][self.bracket]))
            emission.extend(_PACKERS[mode](self.payload[start:end]))

        stream = BitStream()
        for value, width in emission:
            stream.append(value, width)
        return stream.data
