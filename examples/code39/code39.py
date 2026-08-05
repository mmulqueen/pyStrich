# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""Code 39 barcode, saved as SVG."""

from pystrich.code39 import Code39Encoder

Code39Encoder("64755").save_svg("code39.svg")
