"""QR Code renderer"""

from io import BytesIO
try:
    from PIL import Image
except ImportError:
    import Image


class QRCodeRenderer:
    """Rendering class - given a pre-populated QR Code matrix.
    it will add edge handles and render to either to an image
    (including quiet zone) or ascii printout"""

    def __init__(self, matrix):

        self.mtx_size = len(matrix)
        self.matrix = matrix

    def add_border(self, colour=1, width=4):
        """Wrap the matrix in a border of given width
            and colour"""

        self.mtx_size += width * 2

        self.matrix = [[colour, ] * self.mtx_size, ] * width + \
                      [[colour, ] * width + self.matrix[i] + [colour, ] * width
                          for i in range(0, self.mtx_size - (width * 2))] + \
                      [[colour, ] * self.mtx_size, ] * width

    def get_pilimage(self, cellsize):
        """Return the matrix as a PIL object"""

        # add the quiet zone (4 x cell width)
        self.add_border(colour=0, width=4)

        # get the matrix into the right buffer format
        buff = self.get_buffer(cellsize)

        # write the buffer out to an image
        img = Image.frombuffer(
            'L',
            (self.mtx_size * cellsize, self.mtx_size * cellsize),
            buff, 'raw', 'L', 0, -1)
        return img

    def write_file(self, cellsize, filename):
        """Write the matrix out to an image file"""
        img = self.get_pilimage(cellsize)
        img.save(filename)

    def get_imagedata(self, cellsize):
        """Write the matrix out as PNG to an bytestream"""
        imagedata = BytesIO()
        img = self.get_pilimage(cellsize)
        img.save(imagedata, "PNG")
        return imagedata.getvalue()

    def get_buffer(self, cellsize):
        """Convert the matrix into the buffer format used by PIL"""

        def pixel(value):
            """return pixel representation of a matrix value
            0 => white, 1 => black"""
            if value == 0:
                return b"\xff"
            elif value == 1:
                return b"\x00"

        # PIL writes image buffers from the bottom up,
        # so feed in the rows in reverse
        buf = b""
        for row in self.matrix[::-1]:
            bufrow = b''.join([pixel(cell) * cellsize for cell in row])
            for _ in range(0, cellsize):
                buf += bufrow
        return buf

    def get_ascii(self):
        """Write an ascii version of the matrix out to screen"""

        def symbol(value):
            """return ascii representation of matrix value"""
            if value == 0:
                return ' '
            elif value == 1:
                return 'X'

        return '\n'.join([
            ''.join([symbol(cell) for cell in row])
            for row in self.matrix]) + '\n'
    
    def get_dxf(self, cellsize, inverse, units):
        """Write an DXF version of the matrix to a string"""
        dxf = []
        dxf.append("0\nSECTION\n2\nHEADER\n")
        # AutoCAD drawing version number (AC1006 = R10, AC1009 = R11/R12, AC1012 = R13, AC1014 = R14)
        dxf.append("9\n$ACADVER\n1\nAC1006\n")
        # Default drawing units (1 = Inches; 2 = Feet; 3 = Miles; 4 = Millimeters; 5 = Centimeters; 6 = Meters)
        dxf.append("9\n$INSUNITS\n70\n")
        dxf.append("4\n" if units == "mm" else "0\n")
        dxf.append("0\nENDSEC\n0\nSECTION\n2\nENTITIES\n")
        
        def coord(x,y,c):
            # Group codes 10,11,12,13 are X1,X2,X3,X4 coordinates
            # Group codes 20,21,22,23 are Y1,Y2,Y3,Y4 coordinates
            # Group codes 30,31,32,33 are Z1,Z2,Z3,Z4 coordinates
            return '\n'.join(map(str,(10+c, x, 20+c, y, 30+c, 0, '')))
        def solid(x,y,w=cellsize,h=cellsize):
            # calculate corner coordinates
            cl = ((x,y,0), (x+w,y,1), (x,y-h,2), (x+w,y-h,3))
            return "0\nSOLID\n8\nbarcode\n" + "".join( [coord(x,y,c) for x,y,c in cl] )
        dxf.extend( [ ''.join([solid(x*cellsize, (self.mtx_size-y)*cellsize)
                               if bool(val) != inverse else ''
                              for x, val in enumerate(row)])
                    for y, row in enumerate(self.matrix)] )
        if inverse:
            qz = 4 #quietzone
            dxf.append(solid(-qz*cellsize, 0, self.mtx_size + 2 * qz * cellsize, qz*cellsize))
            dxf.append(solid(-qz*cellsize, self.mtx_size+qz*cellsize, self.mtx_size + 2 * qz * cellsize, qz*cellsize))
            dxf.append(solid(-qz*cellsize, self.mtx_size*cellsize, qz*cellsize, self.mtx_size*cellsize))
            dxf.append(solid(self.mtx_size*cellsize, self.mtx_size*cellsize, qz*cellsize, self.mtx_size*cellsize))
        dxf.append("0\nENDSEC\n0\nEOF\n")
        return "".join(dxf)    
