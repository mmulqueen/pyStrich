# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""QR Code, saved as SVG."""

from pystrich.qrcode import QRCodeEncoder

QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg("qrcode.svg")
