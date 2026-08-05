# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""PDF417 stacked barcode, saved as SVG."""

from pystrich.pdf417 import PDF417Encoder

PDF417Encoder("WDBCA45D2HA327260").save_svg("pdf417.svg")
