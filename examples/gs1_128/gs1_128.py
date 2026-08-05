# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""GS1-128 barcode: (01) GTIN + (17) expiry + (10) batch, saved as SVG."""

from pystrich.code128 import Code128Data, Code128Encoder
from pystrich.gs1 import GS1Fixed, GS1Variable

payload = Code128Data.gs1(
    GS1Fixed("01", "05050070007664"),
    GS1Fixed("17", "261231"),
    GS1Variable("10", "W126"),
)
Code128Encoder(payload).save_svg("gs1_128.svg")
