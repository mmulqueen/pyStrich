# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich[png]", "django"]
# ///
"""Serve a product's barcode as PNG: look the product up by primary key, encode its GTIN.

Run it and open http://127.0.0.1:8000/product/1/barcode.png.
"""

import sys

from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import Http404, HttpRequest, HttpResponse
from django.urls import path

from pystrich.ean13 import EAN13Encoder

# runserver binds 127.0.0.1 by default; DEBUG=True auto-allows localhost hosts.
settings.configure(DEBUG=True, SECRET_KEY="django-insecure-example-only", ROOT_URLCONF=__name__)

# Stand-in for a real database: primary key -> product GTIN.
PRODUCTS = {
    1: "5050070007664",  # Road House (DVD)
    2: "0034100175054",  # Miller Genuine Draft, 6-pack
}


def barcode(request: HttpRequest, product_id: int) -> HttpResponse:
    gtin = PRODUCTS.get(product_id)
    if gtin is None:
        raise Http404("no such product")
    return HttpResponse(EAN13Encoder(gtin).get_imagedata(), content_type="image/png")


urlpatterns = [path("product/<int:product_id>/barcode.png", barcode)]

if __name__ == "__main__":
    execute_from_command_line([sys.argv[0], "runserver"])
