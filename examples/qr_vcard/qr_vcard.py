# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""QR Code holding a vCard contact, saved as SVG.

vCard is plain text with CRLF line endings; a phone offers to save the contact.
"""

from pystrich.qrcode import QRCodeEncoder

vcard = "BEGIN:VCARD\r\nVERSION:3.0\r\nFN:Red\r\nTEL:+14175550142\r\nEND:VCARD\r\n"
QRCodeEncoder(vcard).save_svg("qr_vcard.svg")
