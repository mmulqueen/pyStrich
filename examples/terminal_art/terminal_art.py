# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""Print a Wi-Fi join QR to the terminal -- scan it to connect, no password typing."""

from pystrich.qrcode import QRCodeData, QRCodeEncoder

# QRCodeData.wifi_network builds the WIFI: payload phones understand.
wifi = QRCodeData.wifi_network(ssid="DoubleDeuceGuest", password="PainDontHurt")

# Pass ansi_bg=False for plain block characters without ANSI colour codes.
print(QRCodeEncoder(wifi).get_terminal_art())
