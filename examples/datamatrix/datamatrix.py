# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""Data Matrix (ECC 200), saved as SVG.

``auto_encoding`` picks the narrowest encoding that fits the input.
"""

from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", auto_encoding=True)
DataMatrixEncoder(payload).save_svg("datamatrix.svg")
