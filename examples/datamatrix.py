"""Example code for datamatrix library"""

__revision__ = "$Revision$"

import logging
import os.path
import sys

from pystrich.datamatrix import DataMatrixEncoder

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir))

logging.getLogger("datamatrix").setLevel(logging.DEBUG)
logging.getLogger("datamatrix").addHandler(logging.StreamHandler(sys.stdout))

if __name__ == "__main__":
    encoder = DataMatrixEncoder(sys.argv[1])
    encoder.save("test.png")
    print(encoder.get_ascii())
    with open("test.dxf", "w") as text_file:
        text_file.write(encoder.get_dxf(inverse=True, cellsize=0.1))
