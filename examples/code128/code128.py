# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""Code 128 barcode, saved as SVG."""

from pystrich.code128 import Code128Encoder

Code128Encoder("WDBCA45D2HA327260").save_svg("code128.svg")
