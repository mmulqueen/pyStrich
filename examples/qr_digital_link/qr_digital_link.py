# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""QR Code holding a GS1 Digital Link URL, saved as SVG.

A Digital Link is just a URL, so it goes straight to QRCodeEncoder.
"""

from pystrich.qrcode import QRCodeEncoder

url = "https://id.gs1.org/01/05050070007664/10/W126"
QRCodeEncoder(url).save_svg("qr_digital_link.svg")
