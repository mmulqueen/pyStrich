# /// script
# requires-python = ">=3.10"
# dependencies = ["pystrich"]
# ///
"""Draw a QR Code with Python's turtle, driven by get_rect_marks().

``get_rect_marks`` returns the dark modules as ``(x, y, w, h)`` rectangles in a
top-left-origin grid; here each is redrawn as a filled square with the turtle.
Opens a turtle window (needs a display); nothing is written to disk.
"""

import turtle

from pystrich.marks import MarkShape
from pystrich.qrcode import QRCodeEncoder

MODULE = 12  # pixels per module

marks = QRCodeEncoder("https://github.com/mmulqueen/pyStrich").get_rect_marks(
    mark_shape=MarkShape.SQUARE_CELLS
)

screen = turtle.Screen()
screen.setup(marks.width * MODULE + 40, marks.height * MODULE + 40)
screen.tracer(0)

pen = turtle.Turtle(visible=False)
pen.penup()
pen.fillcolor("black")

# Turtle's y points up while marks point down, so centre the grid and flip y.
for x, y, width, height in marks.marks:
    pen.goto((x - marks.width / 2) * MODULE, (marks.height / 2 - y) * MODULE)
    pen.begin_fill()
    for dx, dy in ((width, 0), (0, -height), (-width, 0), (0, height)):
        pen.goto(pen.xcor() + dx * MODULE, pen.ycor() + dy * MODULE)
    pen.end_fill()

screen.update()
turtle.done()
