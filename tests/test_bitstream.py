"""Tests for ``pystrich.bitstream.BitStream``."""

import pytest

from pystrich.bitstream import BitStream
from pystrich.exceptions import PyStrichError


def test_append_emits_bits_msb_first():
    bs = BitStream()
    bs.append(0b10110, 5)
    assert bs.data == [1, 0, 1, 1, 0]


def test_append_truncates_to_low_bitsnum_bits():
    bs = BitStream()
    bs.append(0xFF, 4)
    assert bs.data == [1, 1, 1, 1]


def test_prepend_orders_msb_first_at_the_front():
    bs = BitStream()
    bs.append(0, 4)
    bs.prepend(0b101, 3)
    assert bs.data == [1, 0, 1, 0, 0, 0, 0]


def test_append_then_prepend_produces_expected_sequence():
    bs = BitStream()
    bs.append(0xA, 4)
    bs.append(0x5, 4)
    bs.prepend(0b11, 2)
    assert bs.data == [1, 1, 1, 0, 1, 0, 0, 1, 0, 1]


@pytest.mark.parametrize("op", ["append", "prepend"])
@pytest.mark.parametrize("bitsnum", [0, -1, -8])
def test_invalid_bitsnum_raises(op, bitsnum):
    bs = BitStream()
    with pytest.raises(PyStrichError):
        getattr(bs, op)(0, bitsnum)
