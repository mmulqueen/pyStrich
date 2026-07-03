"""Encoding table and bar builder for Interleaved 2 of 5 / ITF-14."""

from __future__ import annotations

# Each digit is five elements wide, two of them wide -- hence "2 of 5". In an
# interleaved pair the first digit's pattern draws the bars and the second's
# draws the intervening spaces.
# fmt: off
WIDTHS: dict[int, str] = {
    0: "NNWWN",
    1: "WNNNW",
    2: "NWNNW",
    3: "WWNNN",
    4: "NNWNW",
    5: "WNWNN",
    6: "NWWNN",
    7: "NNNWW",
    8: "WNNWN",
    9: "NWNWN",
}
# fmt: on

# A narrow element is one module, a wide element two. Bars are "1", spaces "0".
START = "1010"
STOP = "11101"


def encode_digits(digits: str) -> str:
    """Return the ``"1"/"0"`` bar string for an even-length digit string."""
    bars = [START]
    for pair in range(0, len(digits), 2):
        bar_pattern = WIDTHS[int(digits[pair])]
        space_pattern = WIDTHS[int(digits[pair + 1])]
        for bar, space in zip(bar_pattern, space_pattern, strict=True):
            bars.append("1" if bar == "N" else "11")
            bars.append("0" if space == "N" else "00")
    bars.append(STOP)
    return "".join(bars)
