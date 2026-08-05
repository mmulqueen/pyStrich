# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich[png]"]
# ///
"""Compose a shipping label as a printer-ready raster bitmap with Pillow.

Thermal label printers (Zebra, Brother, ...) take a raster at the device's exact
pixel size, so the whole label is built as one image: the address and service
text drawn with Pillow, plus a Code 128 barcode composited via get_pilimage().
"""

from PIL import Image, ImageDraw, ImageFont

from pystrich.code128 import Code128Encoder

# 4x6" label at 203 dpi -- a common thermal-printer raster size.
WIDTH, HEIGHT, DPI = 812, 1218, 203
TRACKING = "1Z999AA10123456784"

label = Image.new("RGB", (WIDTH, HEIGHT), "white")
draw = ImageDraw.Draw(label)
heading = ImageFont.load_default(size=48)
body = ImageFont.load_default(size=36)
small = ImageFont.load_default(size=28)

draw.text((48, 40), "SHIP TO", font=heading, fill="black")
for i, line in enumerate(["Dalton", "The Double Deuce", "Jasper, MO 64755"]):
    draw.text((48, 120 + i * 46), line, font=body, fill="black")

draw.line([(48, 290), (WIDTH - 48, 290)], fill="black", width=3)
draw.text((48, 312), "FROM  Red's Auto Parts, Kansas City, MO", font=small, fill="black")

# Bold service banner.
draw.rectangle([(48, 380), (WIDTH - 48, 480)], fill="black")
draw.text((72, 402), "GROUND", font=heading, fill="white")
draw.text((48, 512), "WT: 12 LB     SHIP DATE: 25 DEC", font=small, fill="black")

# Paste the barcode at its native size -- never rescale a barcode raster by a
# non-integer factor, as that distorts the module widths and can stop it scanning.
barcode = Code128Encoder(TRACKING, options={"show_label": False}).get_pilimage(3)
draw.text((48, HEIGHT - barcode.height - 170), "TRACKING #", font=small, fill="black")
label.paste(barcode, ((WIDTH - barcode.width) // 2, HEIGHT - barcode.height - 120))
draw.text((48, HEIGHT - 88), TRACKING, font=body, fill="black")

label.save("pillow_label.png", dpi=(DPI, DPI))
