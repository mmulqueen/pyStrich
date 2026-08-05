# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""Generate many barcodes in a loop, one SVG per identifier.

Each encoder builds a fresh symbol, so there is no shared state to reset
between calls.
"""

from pathlib import Path

from pystrich.code128 import Code128Encoder

out = Path("labels")
out.mkdir(exist_ok=True)

for part_number in ["A1266470501", "A1268206342", "A0001513255"]:
    Code128Encoder(part_number).save_svg(out / f"{part_number}.svg")
