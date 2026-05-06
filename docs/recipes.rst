Recipes
=======

Common patterns for using pyStrich in real applications.

Serving barcodes from a web request
-----------------------------------

Every encoder has a :meth:`get_imagedata` method that returns the PNG as a
``bytes`` object, suitable for streaming straight back to a client without
touching the filesystem.

With Flask:

.. code-block:: python

   from flask import Flask, Response
   from pystrich.code39 import Code39Encoder

   app = Flask(__name__)

   @app.route("/barcode/<text>")
   def barcode(text):
       encoder = Code39Encoder(text)
       return Response(encoder.get_imagedata(), mimetype="image/png")

The same pattern applies to FastAPI, Django, or any other framework -- the
encoder produces raw PNG bytes that can be returned with the
``image/png`` content type.

Generating barcodes in bulk
---------------------------

Each encoder constructs a fresh symbol; there is no shared state to reset
between calls. To generate many barcodes, loop over your inputs:

.. code-block:: python

   from pathlib import Path
   from pystrich.code128 import Code128Encoder

   out = Path("labels")
   out.mkdir(exist_ok=True)

   for sku in ["ABC-001", "ABC-002", "ABC-003"]:
       Code128Encoder(sku).save(out / f"{sku}.png")

Loading the output into PIL for further processing
--------------------------------------------------

To composite a barcode onto a label template, call
:meth:`get_pilimage` to obtain a :class:`PIL.Image.Image` directly:

.. code-block:: python

   from PIL import Image
   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

   payload = DataMatrixData("PART-1234", encoding="ascii")
   barcode = DataMatrixEncoder(payload).get_pilimage(cellsize=8)

   label = Image.new("RGB", (400, 200), "white")
   label.paste(barcode, (20, 20))
   label.save("label.png")

Saving to memory only
---------------------

There is no separate "to memory" entry point: :meth:`get_imagedata` is the
in-memory equivalent of :meth:`save`. The two paths share the same
renderer; saving the bytes yourself afterwards is identical to calling
:meth:`save` directly.

.. code-block:: python

   data = Code128Encoder("ABC-12345").get_imagedata()
   # ... do something with `data`, e.g. attach to an email or upload.
