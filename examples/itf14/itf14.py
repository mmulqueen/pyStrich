# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""ITF-14 shipping-carton barcode, saved as SVG."""

from pystrich.itf import ITF14Encoder

ITF14Encoder("1505007000766").save_svg("itf14.svg")
