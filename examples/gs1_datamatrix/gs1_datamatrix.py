# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""GS1 Data Matrix: (01) GTIN + (17) expiry + (10) batch, saved as SVG."""

from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder
from pystrich.gs1 import GS1Fixed, GS1Variable

payload = DataMatrixData.gs1(
    GS1Fixed("01", "05050070007664"),
    GS1Fixed("17", "261231"),
    GS1Variable("10", "W126"),
)
DataMatrixEncoder(payload).save_svg("gs1_datamatrix.svg")
