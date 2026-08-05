# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich[png]", "flask"]
# ///
"""Serve a product's barcode as PNG: look the product up by primary key, encode its GTIN."""

from flask import Flask, Response, abort

from pystrich.ean13 import EAN13Encoder

app = Flask(__name__)

# Stand-in for a real database: primary key -> product GTIN.
PRODUCTS = {
    1: "5050070007664",  # Road House (DVD)
    2: "0034100175054",  # Miller Genuine Draft, 6-pack
}


@app.route("/product/<int:product_id>/barcode.png")
def barcode(product_id: int) -> Response:
    gtin = PRODUCTS.get(product_id)
    if gtin is None:
        abort(404)
    return Response(EAN13Encoder(gtin).get_imagedata(), mimetype="image/png")


if __name__ == "__main__":
    app.run()
