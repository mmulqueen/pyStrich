# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""EAN-13 barcode saved as SVG."""

from pystrich.ean13 import EAN13Encoder

EAN13Encoder("5050070007664").save_svg("ean13.svg")
