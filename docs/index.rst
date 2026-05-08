pyStrich
========

pyStrich is a Python module for generating 1D and 2D barcodes. It supports
Code 39, Code 128, EAN-13, Data Matrix and QR Code symbologies. All five
emit PNG (via :class:`Pillow <PIL.Image.Image>`), SVG and EPS. Data Matrix
and QR Code additionally render to terminal art and DXF for direct part
marking.

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

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", auto_encoding=True)
   DataMatrixEncoder(payload).save_svg("datamatrix-example.svg")

.. image:: examples/datamatrix-example.svg
   :alt: Data Matrix encoding the pyStrich GitHub URL.

A minimal example for each of the other symbologies:

.. code-block:: python

   from pystrich.code39 import Code39Encoder
   Code39Encoder("64755").save_svg("code39-example.svg")

.. image:: examples/code39-example.svg
   :alt: Code 39 barcode encoding "64755".

.. code-block:: python

   from pystrich.code128 import Code128Encoder
   Code128Encoder("WDBCA45D2HA327260").save_svg("code128-example.svg")

.. image:: examples/code128-example.svg
   :alt: Code 128 barcode encoding "WDBCA45D2HA327260".

.. code-block:: python

   from pystrich.ean13 import EAN13Encoder
   EAN13Encoder("5050070007664").save_svg("ean13-example.svg")

.. image:: examples/ean13-example.svg
   :alt: EAN-13 barcode encoding "5050070007664".

.. code-block:: python

   from pystrich.qrcode import QRCodeEncoder
   QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg("qrcode-example.svg")

.. image:: examples/qrcode-example.svg
   :alt: QR code encoding the pyStrich GitHub URL.

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

   cli
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
