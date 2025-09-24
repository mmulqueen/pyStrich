#!/usr/bin/env python

"""2D Datamatrix barcode encoder

All needed by the user is done via the DataMatrixEncoder class:

>>> encoder = DataMatrixEncoder("HuDoRa")
>>> # encoder.save( "test.png" )
>>> print encoder.get_ascii()
XX  XX  XX  XX  XX  XX  XX
XX  XXXX  XXXXXX      XXXXXX
XXXXXX    XX          XX
XXXXXX    XX        XXXX  XX
XXXX  XX  XXXXXX
XXXXXX    XXXXXXXX    XXXXXX
XX    XX  XXXXXXXX  XXXX
XX    XX      XXXX      XXXX
XX  XXXXXXXXXX    XXXX
XX  XXXX    XX            XX
XX  XXXXXX  XXXXXX      XX
XXXXXX  XX  XX  XX  XX    XX
XX    XX              XX
XXXXXXXXXXXXXXXXXXXXXXXXXXXX


Implemented by Helen Taylor for HUDORA GmbH.
Updated and ported to Python 3 by Michael Mulqueen for Method B Ltd.

Detailed documentation on the format here:
http://grandzebu.net/informatique/codbar-en/datamatrix.htm
Further resources here: http://www.libdmtx.org/resources.php

You may use this under a BSD License.
"""

__revision__ = "$Rev$"

from .textencoder import TextEncoder
from .placement import DataMatrixPlacer
from .renderer import DataMatrixRenderer, DATAMATRIX_DEFAULT_QUIET_ZONE


class DataMatrixEncoder:
    """Top-level class which handles the overall process of
    encoding input data, placing it in the matrix and
    outputting the result"""

    def __init__(self, text, *, quiet_zone=DATAMATRIX_DEFAULT_QUIET_ZONE):
        """Set up the encoder with the input text.
        This will encode the text,
        and create a matrix with the resulting codewords"""

        enc = TextEncoder()
        codewords = enc.encode(text)
        self.width = 0
        self.height = 0
        matrix_size = enc.mtx_size*enc.regions
        self.regions = enc.regions
        self.quiet_zone = quiet_zone

        self.matrix = [[None] * matrix_size for _ in range(0, matrix_size)]

        placer = DataMatrixPlacer()
        placer.place(codewords, self.matrix)

    def init_renderer(self):
        dmtx = DataMatrixRenderer(self.matrix, self.regions, quiet_zone=self.quiet_zone)
        self.width = dmtx.width
        self.height = dmtx.height
        return dmtx

    def save(self, filename, cellsize=5):
        """Write the matrix out to an image file"""
        dmtx = self.init_renderer()
        dmtx.write_file(cellsize, filename)

    def get_imagedata(self, cellsize=5):
        """Write the matrix out to an PNG bytestream"""
        dmtx = self.init_renderer()
        return dmtx.get_imagedata(cellsize)

    def get_ascii(self):
        """Return an ascii representation of the matrix"""
        dmtx = self.init_renderer()
        return dmtx.get_ascii()

    def get_dxf(self, cellsize=1.0, inverse=True, units="mm"):
        """Return a DXF representation of the matrix"""
        dmtx = self.init_renderer()
        return dmtx.get_dxf(cellsize, inverse, units)
        