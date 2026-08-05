# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich>=0.19", "weasyprint>=60"]
# ///
"""Create a GS1 two-barcode logistic label with pyStrich + WeasyPrint."""

from __future__ import annotations

from datetime import date

from weasyprint import HTML

from pystrich.code128 import Code128Data, Code128Encoder
from pystrich.gs1 import GS1Fixed, GS1Variable

GS1Field = GS1Fixed | GS1Variable

# Each value is defined once here, then fed to both the barcodes and the
# printed field block, so the two can't drift apart.
SSCC = "006141410001234560"
CONTENT_GTIN = "00034100175054"
COUNT = 240
USE_BY = date(2027, 12, 25)
VARIANT = "05"
BATCH = "W126"

# Top symbol: (02) GTIN of the contained trade items, (17) use-by, (37) count.
top = [
    GS1Fixed("02", CONTENT_GTIN),
    GS1Fixed("17", USE_BY.strftime("%y%m%d")),
    GS1Variable("37", str(COUNT)),
]
# Bottom symbol: (00) SSCC, (20) variant, (10) batch/lot.
bottom = [
    GS1Fixed("00", SSCC),
    GS1Fixed("20", VARIANT),
    GS1Variable("10", BATCH),
]


def barcode_svg(fields: list[GS1Field]) -> str:
    """A GS1-128 symbol as bare bars (no HRI -- we draw our own below)."""
    data = Code128Data.gs1(*fields)
    return Code128Encoder(data, options={"show_label": False}).svg_dataurl(bar_width=2)


def hri(fields: list[GS1Field]) -> str:
    """Human-readable interpretation: each field as ``(AI)value``."""
    return "".join(f"({f.application_identifier}){f.value}" for f in fields)


html = f"""
<style>
  @page {{ size: 105mm 152mm; margin: 0; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; font-family: "Helvetica Neue", Arial, sans-serif; color: #000; }}
  .label {{ border: 2.5px solid #000; margin: 3mm; padding: 3mm 4mm 4mm; }}
  .company {{ font-size: 19pt; font-weight: 800; letter-spacing: -.4px; line-height: 1.05; }}
  .subtitle {{ font-size: 12.5pt; font-weight: 700; padding-bottom: 2mm;
               border-bottom: 1.5px solid #000; }}
  .fields {{ width: 100%; border-collapse: collapse; margin-top: 1.5mm; }}
  .fields td {{ vertical-align: top; padding: 1.2mm 0; width: 33.33%; }}
  .flabel {{ font-size: 14pt; font-weight: 800; line-height: 1.1; }}
  .fvalue {{ font-size: 12pt; }}
  hr {{ border: none; border-top: 1.5px solid #000; margin: 1mm 0; }}
  .symbol {{ margin-top: 3mm; }}
  .bars {{ text-align: center; }}
  .bars img {{ width: 80%; height: 22mm; }}
  .hri {{ text-align: center; font-family: "Courier New", monospace;
          font-size: 9.5pt; font-weight: 700; margin-top: .5mm; }}
</style>
<div class="label">
  <div class="company">JASPER DISTRIBUTION CO</div>
  <div class="subtitle">additional info goes here</div>

  <table class="fields">
    <tr><td colspan="3">
      <div class="flabel">SSCC</div>
      <div class="fvalue">{SSCC}</div>
    </td></tr>
    <tr>
      <td><div class="flabel">Content</div>
          <div class="fvalue">{CONTENT_GTIN}</div></td>
      <td></td>
      <td><div class="flabel">Count</div>
          <div class="fvalue">{COUNT}</div></td>
    </tr>
    <tr>
      <td><div class="flabel">Use by</div>
          <div class="fvalue">{USE_BY.strftime("%d.%m.%y")}</div></td>
      <td><div class="flabel">Variant</div>
          <div class="fvalue">{VARIANT}</div></td>
      <td><div class="flabel">Batch No.</div>
          <div class="fvalue">{BATCH}</div></td>
    </tr>
  </table>

  <hr>

  <div class="symbol">
    <div class="bars"><img src="{barcode_svg(top)}"></div>
    <div class="hri">{hri(top)}</div>
  </div>

  <div class="symbol">
    <div class="bars"><img src="{barcode_svg(bottom)}"></div>
    <div class="hri">{hri(bottom)}</div>
  </div>
</div>
"""

HTML(string=html).write_pdf("gs1_logistic_label.pdf")
