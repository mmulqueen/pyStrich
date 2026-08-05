# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""QR Code holding a ``geo:`` location URI (RFC 5870), saved as SVG."""

from pystrich.qrcode import QRCodeEncoder

QRCodeEncoder("geo:37.335278,-94.302222").save_svg("qr_geo.svg")
