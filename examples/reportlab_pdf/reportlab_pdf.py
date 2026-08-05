# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich[png]", "reportlab"]
# ///
"""Draw a PDF417 barcode into a ReportLab PDF via get_imagedata().

ReportLab's built-in barcodes cover EAN/UPC, Code 128/39, QR and Data Matrix,
but not PDF417 or Aztec -- so pyStrich fills the gap: render the symbol to PNG
bytes and drawImage() them.
"""

from io import BytesIO

from reportlab.lib.pagesizes import A6
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from pystrich.pdf417 import PDF417Encoder

barcode = ImageReader(BytesIO(PDF417Encoder("WDBCA45D2HA327260").get_imagedata()))

pdf = canvas.Canvas("reportlab_pdf.pdf", pagesize=A6)
_, height = A6
pdf.setFont("Helvetica-Bold", 16)
pdf.drawString(18 * mm, height - 22 * mm, "Vehicle record")
pdf.setFont("Helvetica", 11)
pdf.drawString(18 * mm, height - 30 * mm, "VIN: WDBCA45D2HA327260")
pdf.drawImage(
    barcode,
    18 * mm,
    height - 62 * mm,
    width=84 * mm,
    height=30 * mm,
    preserveAspectRatio=True,
    mask="auto",
)
pdf.showPage()
pdf.save()
