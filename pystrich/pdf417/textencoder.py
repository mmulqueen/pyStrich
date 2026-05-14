"""High-level PDF417 encoder.

The pipeline runs four steps:

1. **Compaction**. Splits the input into Text, Byte and Numeric runs
   and emits codewords using the appropriate mode. Mode switching is
   greedy: digit runs of 13 or more switch to Numeric, anything Text
   Compaction cannot represent switches to Byte, everything else stays
   in Text mode.

2. **Sizing and Symbol Length Descriptor**. The matrix is sized from
   the chosen ``columns`` and the source codeword count, and
   ``n = c*r - k`` is prepended as the SLD.

3. **Padding**. 900 codewords fill the remaining data slots.

4. **Error correction**. ``2 ** (ecl + 1)`` Reed-Solomon codewords are
   appended via :func:`pystrich.reedsolomon.reed_solomon_encode_pdf417`.

Matrix layout and rendering are not part of this module; the output is
the linear codeword stream that a later stage lays out on the bar grid.
"""

from __future__ import annotations

import math

from pystrich.exceptions import PyStrichInvalidInput
from pystrich.reedsolomon import reed_solomon_encode_pdf417

from .data import PDF417Data, PDF417Encoding
from .tables import (
    CHAR_TO_SUBMODE_VALUE,
    ECI_SMALL,
    LATCH_BYTE,
    LATCH_BYTE_MULT6,
    LATCH_NUMERIC,
    LATCH_TEXT,
    SUB_ALPHA,
    ec_codeword_count,
)

# ISO-8859-1 is the PDF417 default, so ASCII and Latin-1 inputs need no
# prefix. UTF-8 (ECI 26) is signalled by codeword 927 followed by 26.
_ECI_DESIGNATOR: dict[PDF417Encoding, int | None] = {
    "ascii": None,
    "iso-8859-1": None,
    "utf-8": 26,
}

PAD_CODEWORD = 900
"""Pad codeword. Fills unused data slots."""

NUMERIC_RUN_THRESHOLD = 13
"""Shortest digit run that justifies a switch to Numeric Compaction.

Below this length, encoding the digits in Text Compaction's Mixed
sub-mode at 2 characters per codeword beats Numeric mode, which costs
roughly 3 digits per codeword plus a latch.
"""

# Sub-mode transitions inside Text Compaction. A latch changes the
# active sub-mode for the rest of the symbol; a shift only applies to
# the next base-30 value. When the spec provides no direct latch (for
# example Lower to Alpha), the encoder chains two single-step latches
# through an intermediate sub-mode. The chains are short enough -- two
# steps at most -- to enumerate explicitly.

_LATCH_PATH: dict[tuple[str, str], tuple[int, ...]] = {
    ("alpha", "lower"): (27,),
    ("alpha", "mixed"): (28,),
    ("alpha", "punct"): (28, 25),
    ("lower", "alpha"): (28, 28),
    ("lower", "mixed"): (28,),
    ("lower", "punct"): (28, 25),
    ("mixed", "alpha"): (28,),
    ("mixed", "lower"): (27,),
    ("mixed", "punct"): (25,),
    ("punct", "alpha"): (29,),
    ("punct", "lower"): (29, 27),
    ("punct", "mixed"): (29, 28),
}

_SHIFT_PATH: dict[tuple[str, str], int] = {
    ("alpha", "punct"): 29,
    ("lower", "alpha"): 27,
    ("lower", "punct"): 29,
    ("mixed", "punct"): 29,
}

_PAD_BASE30 = 29
"""Base-30 value used to pad an odd-length Text Compaction stream.

Slot 29 is a shift or latch in every sub-mode, and the spec lets any
latch or shift serve as a terminal pad.
"""


def _numeric_compact(digits: str) -> list[int]:
    """Compact a run of decimal digits using Numeric Compaction mode."""
    cws: list[int] = []
    for start in range(0, len(digits), 44):
        group = digits[start : start + 44]
        t = int("1" + group)
        out: list[int] = []
        while t:
            out.append(t % 900)
            t //= 900
        cws.extend(reversed(out))
    return cws


def _byte_compact(data: bytes) -> list[int]:
    """Compact a bytes sequence using Byte Compaction mode.

    Groups of 6 bytes become 5 codewords via a base-256 to base-900
    conversion. Trailing bytes (when the total is not a multiple of 6)
    are emitted one byte per codeword.
    """
    cws: list[int] = []
    n = len(data)
    full = (n // 6) * 6
    for start in range(0, full, 6):
        t = 0
        for b in data[start : start + 6]:
            t = t * 256 + b
        out: list[int] = []
        for _ in range(5):
            out.append(t % 900)
            t //= 900
        cws.extend(reversed(out))
    cws.extend(data[full:])
    return cws


def _text_compact(text: str, start_submode: str = SUB_ALPHA) -> tuple[list[int], str]:
    """Encode ``text`` in Text Compaction mode.

    Greedy: stay in the current sub-mode when the next character is in
    it, use a shift when the destination sub-mode holds exactly one
    character here, otherwise latch. An odd-length base-30 stream is
    padded with ``ps``. Returns the codewords and the ending sub-mode,
    so a caller spanning several Text-mode segments can resume cleanly.
    """
    base30: list[int] = []
    current = start_submode
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        positions = CHAR_TO_SUBMODE_VALUE[ch]
        sub_to_value = dict(positions)

        if current in sub_to_value:
            base30.append(sub_to_value[current])
            i += 1
            continue

        target = positions[0][0]
        next_in_target = i + 1 < n and target in dict(CHAR_TO_SUBMODE_VALUE.get(text[i + 1], ()))
        shift = _SHIFT_PATH.get((current, target))
        if shift is not None and not next_in_target:
            base30.append(shift)
            base30.append(sub_to_value[target])
        else:
            base30.extend(_LATCH_PATH[(current, target)])
            base30.append(sub_to_value[target])
            current = target
        i += 1

    if len(base30) % 2:
        base30.append(_PAD_BASE30)
    cws = [base30[k] * 30 + base30[k + 1] for k in range(0, len(base30), 2)]
    return cws, current


def _is_digit(ch: str) -> bool:
    return "0" <= ch <= "9"


def _digit_run_length(text: str, start: int) -> int:
    end = start
    while end < len(text) and _is_digit(text[end]):
        end += 1
    return end - start


def _coerce(text: PDF417Data | str) -> PDF417Data:
    """Wrap a bare ``str`` in :class:`PDF417Data` with ``auto_encoding=True``."""
    return text if isinstance(text, PDF417Data) else PDF417Data(text, auto_encoding=True)


def _compact(text: PDF417Data | str) -> list[int]:
    """High-level greedy compaction into PDF417 codewords.

    Starts in Text Compaction / Alpha sub-mode. The encoder only switches
    when the next run is long enough to justify the latch overhead:
    Numeric for digit runs of :data:`NUMERIC_RUN_THRESHOLD` or more, Byte
    for any character Text Compaction cannot represent. When the chosen
    encoding is ``"utf-8"`` an ECI prefix is emitted once at the start
    of the symbol so the decoder interprets non-ASCII bytes as UTF-8
    rather than the Latin-1 default.
    """
    data = _coerce(text)
    joined = "".join(data.segments)
    if not joined:
        return []

    cws: list[int] = []
    eci = _ECI_DESIGNATOR[data.encoding]
    if eci is not None:
        cws.extend([ECI_SMALL, eci])

    current_mode = "text"
    text_submode = SUB_ALPHA
    i = 0
    n = len(joined)

    while i < n:
        if _digit_run_length(joined, i) >= NUMERIC_RUN_THRESHOLD:
            run = _digit_run_length(joined, i)
            if current_mode != "numeric":
                cws.append(LATCH_NUMERIC)
                current_mode = "numeric"
            cws.extend(_numeric_compact(joined[i : i + run]))
            i += run
            continue

        ch = joined[i]
        if ch in CHAR_TO_SUBMODE_VALUE:
            end = i + 1
            while end < n:
                if _digit_run_length(joined, end) >= NUMERIC_RUN_THRESHOLD:
                    break
                if joined[end] not in CHAR_TO_SUBMODE_VALUE:
                    break
                end += 1
            if current_mode != "text":
                cws.append(LATCH_TEXT)
                current_mode = "text"
                text_submode = SUB_ALPHA
            sub_cws, text_submode = _text_compact(joined[i:end], text_submode)
            cws.extend(sub_cws)
            i = end
            continue

        end = i + 1
        while end < n and joined[end] not in CHAR_TO_SUBMODE_VALUE and not _is_digit(joined[end]):
            end += 1
        try:
            byte_data = joined[i:end].encode(data.encoding)
        except UnicodeEncodeError as exc:
            # PDF417Data validates encoding fit at construction, so reaching
            # here means a private caller bypassed the wrapper. Surface it
            # as an input error so the message names the offending character.
            raise PyStrichInvalidInput(
                f"Character {joined[exc.start]!r} cannot be encoded as {data.encoding}"
            ) from exc
        cws.append(LATCH_BYTE_MULT6 if len(byte_data) % 6 == 0 else LATCH_BYTE)
        cws.extend(_byte_compact(byte_data))
        current_mode = "byte"
        i = end

    return cws


def _pick_rows(source_count: int, ecl: int, columns: int) -> int:
    """Choose the smallest number of rows that fits the data at the given columns.

    Spec constraints: ``3 <= rows <= 90``, ``1 <= columns <= 30``, and
    ``columns * rows - ec`` must be at least ``source_count + 1`` (data
    plus the Symbol Length Descriptor).
    """
    if not 1 <= columns <= 30:
        raise PyStrichInvalidInput(f"PDF417 columns must be 1..30, got {columns}")
    k = ec_codeword_count(ecl)
    required = source_count + 1 + k
    rows = max(3, -(-required // columns))
    if rows > 90:
        raise PyStrichInvalidInput(
            f"PDF417 data does not fit at columns={columns}: needs {rows} rows (max 90)"
        )
    return rows


def _auto_columns(total_codewords: int) -> int:
    """Pick a column count that yields a roughly-square symbol.

    With the default Y/X = 3 row-height ratio the rendered symbol is
    square when the row width in modules (``17 * c + 69``) equals
    three times the row count (``3 * T / c``). Setting those equal gives
    ``17 c^2 + 69 c - 3 T = 0``; the positive root is the estimate
    below, clamped to the valid 1..30 column range.
    """
    raw = (-69 + math.sqrt(69**2 + 4 * 17 * 3 * total_codewords)) / (2 * 17)
    return max(1, min(30, round(raw)))


def pick_dimensions(source_count: int, ecl: int, columns: int | None = None) -> tuple[int, int]:
    """Choose ``(rows, columns)`` for ``source_count`` source codewords at ``ecl``.

    When ``columns`` is given, only ``rows`` is computed; otherwise both are
    chosen to make the rendered symbol roughly square.
    """
    if columns is None:
        columns = _auto_columns(source_count + 1 + ec_codeword_count(ecl))
    rows = _pick_rows(source_count, ecl, columns)
    return rows, columns


def assemble(source: list[int], rows: int, columns: int, ecl: int) -> list[int]:
    """Prepend the SLD, pad with 900 and append Reed-Solomon EC codewords.

    The output has length exactly ``rows * columns`` -- the full codeword
    stream ready for low-level layout.
    """
    k = ec_codeword_count(ecl)
    n = columns * rows - k
    pad_count = n - len(source) - 1
    data = [n, *source, *([PAD_CODEWORD] * pad_count)]
    ec = reed_solomon_encode_pdf417(data, k)
    return data + ec


def encode(text: PDF417Data | str, ecl: int, *, columns: int | None = None) -> list[int]:
    """Encode ``text`` as a complete PDF417 codeword stream.

    The pipeline runs compaction, picks ``(rows, columns)``, prepends the
    Symbol Length Descriptor, pads with 900, then appends Reed-Solomon
    error correction codewords.

    :param text: Source text. A plain ``str`` is auto-encoded; wrap in
        :class:`PDF417Data` to pin the encoding to ``"ascii"``,
        ``"iso-8859-1"`` or ``"utf-8"``.
    :param ecl: Error correction level 0..8.
    :param columns: Number of data columns (1..30). When omitted, a
        roughly-square layout is chosen.
    :returns: The full codeword stream. Length equals ``columns * rows``.
    :raises pystrich.exceptions.PyStrichInvalidInput: when the data does not
        fit at the chosen ``columns``/``ecl``.
    """
    source = _compact(text)
    rows, columns = pick_dimensions(len(source), ecl, columns)
    return assemble(source, rows, columns, ecl)
