# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich", "flask"]
# ///
"""Flask template filters that inline barcodes as ``data:`` URLs."""

from flask import Flask, render_template_string

from pystrich.ean13 import EAN13Encoder
from pystrich.qrcode import QRCodeEncoder

app = Flask(__name__)


@app.template_filter("ean13_dataurl")
def ean13_dataurl(code: str) -> str:
    return EAN13Encoder(code).svg_dataurl()


@app.template_filter("qr_dataurl")
def qr_dataurl(text: str) -> str:
    return QRCodeEncoder(text).svg_dataurl(cellsize=4)


@app.route("/")
def index() -> str:
    return render_template_string(
        '<img src="{{ gtin | ean13_dataurl }}" alt="EAN-13 for the Road House DVD">'
        '<img src="{{ url | qr_dataurl }}" alt="QR code">',
        gtin="5050070007664",
        url="https://github.com/mmulqueen/pyStrich",
    )


if __name__ == "__main__":
    app.run()
