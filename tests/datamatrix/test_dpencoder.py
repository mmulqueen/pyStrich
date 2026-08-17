"""DP high-level encoder tests for DataMatrix."""

from __future__ import annotations

import pytest

from pystrich.datamatrix.dpencoder import encode_high_level


@pytest.mark.parametrize(
    "payload, expected",
    [
        pytest.param(b"", [], id="empty"),
        # Single ASCII byte: latch+unlatch overhead loses to 1 codeword ASCII.
        pytest.param(b"A", [66], id="single-uppercase-ascii"),
        # Digit pair packs into one codeword 130+N.
        pytest.param(b"12", [142], id="digit-pair"),
        # Trailing single digit: pair + single.
        pytest.param(b"123", [142, 52], id="digit-pair-plus-single"),
        # Five digits: pair + pair + single (greedy left-to-right pairing).
        pytest.param(b"12345", [142, 164, 54], id="five-digits"),
        # High byte triggers Upper Shift; C40/Text framing costs more.
        pytest.param(b"\xe9", [235, 106], id="single-high-byte-upper-shift"),
        # Carriage return: ASCII (15) beats C40 Shift1 (4 thirds + framing).
        pytest.param(b"\r", [14], id="carriage-return"),
        # Three uppercase: ASCII (9 thirds) beats C40 (3+6+3=12 thirds).
        pytest.param(b"ABC", [66, 67, 68], id="short-uppercase-stays-ascii"),
        # Four uppercase: C40 would land at partial=1 (forbidden); ASCII wins.
        pytest.param(b"ABCD", [66, 67, 68, 69], id="four-uppercase-avoids-c40-partial1"),
        # Nine uppercase: C40 8 codewords beats ASCII 9.
        pytest.param(
            b"AAAAAAAAA",
            [230, 89, 191, 89, 191, 89, 191, 254],
            id="nine-uppercase-c40-wins",
        ),
        # Twelve uppercase: full C40 triplets land at partial=0.
        pytest.param(
            b"ABCDEFGHIJKL",
            [230, 89, 233, 109, 36, 128, 95, 147, 154, 254],
            id="twelve-uppercase-pure-c40",
        ),
        # Eleven lowercase: pure TEXT and hybrid TEXT9+ASCII2 both 10 cw; iteration
        # picks the ASCII end-state, giving the hybrid output.
        pytest.param(
            b"abcdefghijk",
            [239, 89, 233, 109, 36, 128, 95, 254, 107, 108],
            id="eleven-lowercase-text-hybrid",
        ),
        # Twelve lowercase: pure TEXT wins outright (10 cw vs 12 ASCII).
        pytest.param(
            b"abcdefghijkl",
            [239, 89, 233, 109, 36, 128, 95, 147, 154, 254],
            id="twelve-lowercase-pure-text",
        ),
        # Nine X12-encodable chars (CR + 8 letters): X12 8 codewords beats ASCII 9.
        pytest.param(
            b"\rABCDEFGH",
            [238, 2, 64, 102, 187, 121, 246, 254],
            id="nine-x12-chars-x12-wins",
        ),
        # Fourteen lowercase: pure TEXT (Shift1 pad) ties with hybrid TEXT12+ASCII2;
        # iteration picks the ASCII end-state.
        pytest.param(
            b"abcdefghijklmn",
            [239, 89, 233, 109, 36, 128, 95, 147, 154, 254, 110, 111],
            id="fourteen-lowercase-text-hybrid",
        ),
        # High byte mid-Text run: DP keeps the segment in TEXT and uses
        # Shift2 + Upper Shift for the high byte rather than switching to
        # ASCII and back (the round-trip would cost a relatch).
        pytest.param(
            b"aaaaaaaaaa\xe9aaaaaaaaaa",
            [239, 89, 191, 89, 191, 89, 191, 87, 199, 139, 191, 89, 191, 89, 191, 254, 98, 98],
            id="high-byte-stays-in-text",
        ),
        # Same shape under C40 (uppercase context).
        pytest.param(
            b"AAAAAA\xe9AAAAAA",
            [230, 89, 191, 89, 191, 10, 243, 58, 127, 89, 191, 254, 66],
            id="high-byte-stays-in-c40",
        ),
    ],
)
def test_optimal_encoding(payload: bytes, expected: list[int]) -> None:
    assert encode_high_level(payload) == expected


@pytest.mark.parametrize(
    "eci, expected_prologue",
    [
        pytest.param(26, [241, 27], id="utf-8"),
        pytest.param(0, [241, 1], id="eci-zero"),
        pytest.param(126, [241, 127], id="eci-max"),
    ],
)
def test_eci_prologue_precedes_payload(eci: int, expected_prologue: list[int]) -> None:
    assert encode_high_level(b"A", eci=eci) == [*expected_prologue, 66]


def test_no_eci_emits_no_prologue() -> None:
    assert encode_high_level(b"A") == [66]


def test_empty_payload_with_eci_emits_only_prologue() -> None:
    assert encode_high_level(b"", eci=26) == [241, 27]
