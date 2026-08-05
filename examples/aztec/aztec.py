# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""Aztec Code, saved as SVG."""

from pystrich.aztec import AztecEncoder

AztecEncoder("https://github.com/mmulqueen/pyStrich").save_svg("aztec.svg")
