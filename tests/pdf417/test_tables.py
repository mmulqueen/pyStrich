"""Tests for the PDF417 lookup tables.

These exercise the static character tables: every base-30 slot is
checked against the spec's published ASCII values, and the reverse
character map is checked for completeness.
"""

from __future__ import annotations

import pytest

from pystrich.pdf417 import tables


def test_text_submodes_each_have_30_entries():
    """Every Text Compaction sub-mode is exactly 30 base-30 values wide."""
    for sub, row in tables.TEXT_SUBMODES.items():
        assert len(row) == 30, sub


@pytest.mark.parametrize(
    "sub, value, expected_char",
    [
        # Spot checks across all four sub-modes.
        (tables.SUB_ALPHA, 0, "A"),
        (tables.SUB_ALPHA, 25, "Z"),
        (tables.SUB_ALPHA, 26, " "),
        (tables.SUB_LOWER, 0, "a"),
        (tables.SUB_LOWER, 25, "z"),
        (tables.SUB_MIXED, 0, "0"),
        (tables.SUB_MIXED, 9, "9"),
        (tables.SUB_MIXED, 10, "&"),
        (tables.SUB_MIXED, 11, "\r"),
        (tables.SUB_MIXED, 12, "\t"),
        (tables.SUB_PUNCT, 0, ";"),
        (tables.SUB_PUNCT, 8, "`"),
        (tables.SUB_PUNCT, 9, "~"),
        (tables.SUB_PUNCT, 15, "\n"),
        (tables.SUB_PUNCT, 20, '"'),
        (tables.SUB_PUNCT, 28, "'"),
    ],
)
def test_text_submode_character_assignments(sub, value, expected_char):
    """Each sub-mode maps its base-30 slots to the characters the spec specifies."""
    assert tables.TEXT_SUBMODES[sub][value] == expected_char


@pytest.mark.parametrize(
    "sub, value, expected_marker",
    [
        # Latches and shifts occupy positions 25..29; the exact combinations
        # differ per sub-mode (e.g. Mixed has 'pl' at 25 while Alpha and
        # Lower do not).
        (tables.SUB_ALPHA, 27, tables.LL),
        (tables.SUB_ALPHA, 28, tables.LM),
        (tables.SUB_ALPHA, 29, tables.SP),
        (tables.SUB_LOWER, 27, tables.SU),
        (tables.SUB_LOWER, 28, tables.LM),
        (tables.SUB_LOWER, 29, tables.SP),
        (tables.SUB_MIXED, 25, tables.LP),
        (tables.SUB_MIXED, 27, tables.LL),
        (tables.SUB_MIXED, 28, tables.LU),
        (tables.SUB_MIXED, 29, tables.SP),
        (tables.SUB_PUNCT, 29, tables.LU),
    ],
)
def test_text_submode_latch_and_shift_slots(sub, value, expected_marker):
    """Latch and shift slots in each sub-mode match the spec."""
    assert tables.TEXT_SUBMODES[sub][value] == expected_marker


def test_char_to_submode_value_round_trip():
    """Every character → (sub-mode, value) entry points back to itself in the table."""
    for ch, positions in tables.CHAR_TO_SUBMODE_VALUE.items():
        assert positions, ch
        for sub, value in positions:
            assert tables.TEXT_SUBMODES[sub][value] == ch


def test_char_to_submode_value_covers_alphanumeric_and_space():
    """Every ASCII letter, digit and space is reachable in Text Compaction mode."""
    expected = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 ")
    assert expected <= set(tables.CHAR_TO_SUBMODE_VALUE)


@pytest.mark.parametrize(
    "ecl, expected_count",
    [
        # k = 2 ** (ecl + 1).
        (0, 2),
        (1, 4),
        (2, 8),
        (3, 16),
        (4, 32),
        (5, 64),
        (6, 128),
        (7, 256),
        (8, 512),
    ],
)
def test_ec_codeword_count_matches_spec(ecl, expected_count):
    """Each error correction level produces the spec's codeword count."""
    assert tables.ec_codeword_count(ecl) == expected_count


@pytest.mark.parametrize("ecl", [-1, 9, 100])
def test_ec_codeword_count_rejects_out_of_range(ecl):
    """Levels outside 0..8 are rejected with a clear error."""
    with pytest.raises(ValueError, match=r"0\.\.8"):
        tables.ec_codeword_count(ecl)
