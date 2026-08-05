# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich", "django"]
# ///
"""Self-contained Django app inlining barcodes as data: URLs via template filters.

In a real project the filters live in ``<app>/templatetags/pystrich_filters.py``;
here they are in this module and registered via the template ``libraries`` option,
so ``barcodes.html`` can ``{% load pystrich_filters %}``. Run it and open
http://127.0.0.1:8000/.
"""

import sys
from pathlib import Path

from django import template
from django.conf import settings
from django.core.management import execute_from_command_line
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.template.defaultfilters import stringfilter
from django.urls import path

from pystrich.ean13 import EAN13Encoder
from pystrich.qrcode import QRCodeEncoder

HERE = Path(__file__).parent

register = template.Library()


@register.filter
@stringfilter
def ean13_dataurl(code: str) -> str:
    return EAN13Encoder(code).svg_dataurl()


@register.filter
@stringfilter
def qr_dataurl(text: str) -> str:
    return QRCodeEncoder(text).svg_dataurl(cellsize=4)


# runserver binds 127.0.0.1 by default; DEBUG=True auto-allows localhost hosts.
settings.configure(
    DEBUG=True,
    SECRET_KEY="django-insecure-example-only",
    ROOT_URLCONF=__name__,
    TEMPLATES=[
        {
            "BACKEND": "django.template.backends.django.DjangoTemplates",
            "DIRS": [HERE],
            "OPTIONS": {"libraries": {"pystrich_filters": __name__}},
        }
    ],
)


def index(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "barcodes.html",
        {"gtin": "5050070007664", "url": "https://github.com/mmulqueen/pyStrich"},
    )


urlpatterns = [path("", index)]

if __name__ == "__main__":
    execute_from_command_line([sys.argv[0], "runserver"])
