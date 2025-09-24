"""Datamatrix renderer"""

__revision__ = "$Rev$"

from io import BytesIO

from PIL import Image

DATAMATRIX_DEFAULT_QUIET_ZONE = 2


def repr_matrix(matrix):
    return "\n".join(repr(x) for x in matrix)


class DataMatrixRenderer:
    """Rendering class - given a pre-populated datamatrix.
    it will add edge handles and render to either to an image
    (including quiet zone) or ascii printout"""

    def __init__(self, matrix, regions, *, quiet_zone=DATAMATRIX_DEFAULT_QUIET_ZONE):
        self.width = len(matrix)
        self.height = len(matrix[0])
        self.regions = regions
        self.region_size = self.width//regions
        if quiet_zone < 0:
            raise ValueError("Quiet zone must be non-negative")
        self.quiet_zone = quiet_zone

        self.matrix = matrix

        # grow the matrix in preparation for the handles
        self.add_border(colour=0)

        # add the edge handles
        self.add_handles()

    def put_cell(self, position, colour=1):
        """Set the contents of the given cell"""

        posx, posy = position
        self.matrix[posy][posx] = colour

    def add_handles(self):
        """Set up the edge handles"""

        for x_index in range(self.regions):
            for y_index in range(self.regions):
                x_origin = x_index * (self.region_size + 2) + self.quiet_zone
                y_origin = y_index * (self.region_size + 2) + self.quiet_zone
                x_max = x_origin + self.region_size + 1
                y_max = y_origin + self.region_size + 1

                # bottom solid border
                for posx in range(x_origin, x_max):
                    self.put_cell((posx, y_max))

                # left solid border
                for posy in range(y_origin, y_max):
                    self.put_cell((x_origin, posy))

                # top broken border
                for i in range(x_origin, x_max, 2):
                    self.put_cell((i, y_origin))

                # right broken border
                for i in range(y_max, y_origin, -2):
                    self.put_cell((x_max, i))

    def add_border(self, colour=1):
        """Wrap the matrix in a border of given width
            and colour"""

        a_gap = 1  # Gap for alignment/"handles"
        self.width += a_gap*2 + self.quiet_zone*2 + (self.regions-1)*a_gap*2
        self.height += a_gap*2 + self.quiet_zone*2 + (self.regions-1)*a_gap*2

        new_matrix = []
        for i in range(a_gap+self.quiet_zone):
            new_matrix += [[colour]*self.width]

        for row_n, row in enumerate(self.matrix):
            if row_n > 0 and row_n % self.region_size == 0:
                # Vertical gap between regions
                for j in range(a_gap*2):
                    new_matrix += [[colour]*self.width]
            # Left gap
            new_row = [colour]*(a_gap+self.quiet_zone)
            # Split according to regions
            for i in range(self.regions):
                part = row[i*self.region_size:(i+1)*self.region_size]
                if i > 0:
                    # Add the space for the alignment gap
                    new_row += [colour]*(a_gap*2)
                new_row += part
            # Right gap
            new_row += [colour]*(a_gap+self.quiet_zone)
            new_matrix.append(new_row)

        for i in range(a_gap+self.quiet_zone):
            new_matrix += [[colour]*self.width]
        self.matrix = new_matrix

    def get_pilimage(self, cellsize):
        """Return the matrix as an PIL object"""

        # get the matrix into the right buffer format
        buff = self.get_buffer(cellsize)

        # write the buffer out to an image
        img = Image.frombuffer('L',
                               (self.width * cellsize, self.height * cellsize),
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
                return '  '
            elif value == 1:
                return 'XX'

        return '\n'.join([''.join([symbol(cell) for cell in row]) for row in self.matrix]) + '\n'

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
        dxf.extend( [ ''.join([solid(x*cellsize, (self.height-y)*cellsize)
                               if bool(val) != inverse else ''
                              for x, val in enumerate(row)])
                    for y, row in enumerate(self.matrix)] )
        dxf.append("0\nENDSEC\n0\nEOF\n")
        return "".join(dxf)
