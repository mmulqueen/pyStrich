pyStrich
========

pyStrich is a Python module for generating 1D and 2D barcodes. It supports
Code 39, Code 128, EAN-13, Data Matrix and QR Code symbologies. All emit
PNG images via :class:`Pillow <PIL.Image.Image>`; Data Matrix and QR Code
also emit SVG.

pyStrich is encoder-only -- it does not read barcodes.

* Source: https://github.com/mmulqueen/pyStrich
* PyPI: https://pypi.org/project/pyStrich/

Installation
------------

.. code-block:: console

   $ pip install pyStrich

Quick start
-----------

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save("datamatrix-example.png")

.. image:: examples/datamatrix-example.png
   :alt: Data Matrix encoding the pyStrich GitHub URL.

A minimal example for each of the other symbologies:

.. code-block:: python

   from pystrich.code39 import Code39Encoder
   Code39Encoder("PART-1234").save("code39.png")

.. code-block:: python

   from pystrich.code128 import Code128Encoder
   Code128Encoder("PyStrich-2026").save("code128.png")

.. code-block:: python

   from pystrich.ean13 import EAN13Encoder
   EAN13Encoder("5050070007664").save("ean13.png")

.. code-block:: python

   from pystrich.qrcode import QRCodeEncoder
   QRCodeEncoder("https://example.com").save("qrcode.png")

For more patterns -- serving barcodes from a web request, generating in
bulk, compositing onto a label -- see :doc:`recipes`.

Symbologies
-----------

.. toctree::
   :maxdepth: 1

   datamatrix
   code128
   code39
   ean13
   qrcode

Guides
------

.. toctree::
   :maxdepth: 1

   recipes
   printing

Reference
---------

.. toctree::
   :maxdepth: 1

   exceptions
   changelog
   contributors

Background
----------

pyStrich is a fork of `huBarcode
<https://github.com/hudora/huBarcode>`_, originally developed by `HuDoRa
<https://www.hudora.de/de-en/>`_ from at least 2007. The upstream project
has not been active since late 2013. `Method B Ltd
<https://www.method-b.uk/>`_ forked it to provide Python 3 support and to
continue development.

Thank you to the folks at HuDoRa for doing most of the hard work; the
porting was the easy part.

Licence
-------

.. literalinclude:: ../LICENSE
   :language: text
