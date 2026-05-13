"""End-to-end roundtrip tests for the PDF417 encoder.

Encodes a string, renders it to a PNG, then decodes that PNG via the
shared ``decode_barcode`` fixture (zxing-cpp). The decoded payload must
match the input exactly. This exercises every part of the pipeline --
compaction, error correction, layout and rendering -- against a real
decoder, catching mistakes pure unit tests can miss (an off-by-one in
the row indicator formulas, for example).
"""

from __future__ import annotations

import pytest

from pystrich.pdf417 import PDF417Encoder


def _save(text: str, tmp_path, **kwargs) -> str:
    out = tmp_path / "p417.png"
    PDF417Encoder(text, **kwargs).save(str(out), cellsize=4)
    return str(out)


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("PDF417", id="text-mixed-submode"),
        pytest.param("Hello, World!", id="text-with-punctuation"),
        pytest.param("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz", id="alpha-and-lower"),
        pytest.param("1234567890" * 5, id="numeric-long-run"),
        pytest.param("abc\x80\x81\x82\x83\x84\x85def", id="byte-mult6"),
        pytest.param("abc\x80def", id="byte-single"),
        pytest.param("Mixed: ABC 123 def 4567890123456789012345 end.", id="mixed-mode-switching"),
    ],
)
def test_roundtrip_decodes_to_input(tmp_path, text, decode_barcode):
    """Every compaction mode roundtrips through encoder, renderer and scanner."""
    assert decode_barcode(_save(text, tmp_path)) == text


@pytest.mark.parametrize("ecl", [0, 1, 2, 3, 4, 5])
def test_roundtrip_at_every_ecl_decodes_correctly(tmp_path, ecl, decode_barcode):
    """All error correction levels produce decodable symbols on clean renders."""
    text = "the quick brown fox jumps over the lazy dog"
    assert decode_barcode(_save(text, tmp_path, ecl=ecl)) == text


@pytest.mark.parametrize("columns", [1, 3, 6, 10, 20, 30])
def test_roundtrip_at_various_column_counts(tmp_path, columns, decode_barcode):
    """Different column counts produce decodable symbols."""
    text = "abcdef0123456789"
    assert decode_barcode(_save(text, tmp_path, columns=columns)) == text


@pytest.mark.parametrize("row_height", [2, 3, 4, 6])
def test_roundtrip_at_various_row_heights(tmp_path, row_height, decode_barcode):
    """Above the spec minimum Y/X >= 2 the symbol decodes; row_height=3 is the default."""
    text = "PDF417 row-height test"
    assert decode_barcode(_save(text, tmp_path, row_height=row_height)) == text


@pytest.mark.parametrize(
    "text",
    [
        pytest.param("Ich dachte, Sie wären kräftiger", id="latin1"),
        pytest.param("€5 親切にしろ 🐻‍❄️", id="utf8-mixed"),
    ],
)
def test_roundtrip_non_ascii_decodes_via_eci(tmp_path, text, decode_barcode):
    """Non-ASCII payloads roundtrip via the appropriate character interpretation.

    Latin-1 input uses the PDF417 default (ECI 000003, no prefix needed);
    UTF-8 input emits codeword 927 + 26 (ECI 000026) once at the start of
    the symbol. zxing-cpp picks up both automatically.
    """
    assert decode_barcode(_save(text, tmp_path)) == text
