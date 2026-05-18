:og:description: Generate 1D and 2D barcodes in Python with pyStrich – Code 39, Code 128, EAN-13, Data Matrix, QR Code, PDF417 and Aztec Code as PNG, SVG, EPS, DXF and terminal art.

.. meta::
   :description: Generate 1D and 2D barcodes in Python with pyStrich – Code 39, Code 128, EAN-13, Data Matrix, QR Code, PDF417 and Aztec Code as PNG, SVG, EPS, DXF and terminal art.

pyStrich
========

pyStrich is a Python module for generating 1D and 2D barcodes. It supports
Code 39, Code 128, EAN-13, Data Matrix, QR Code, PDF417 and Aztec Code
symbologies. All seven emit PNG (via :class:`Pillow <PIL.Image.Image>`),
SVG and EPS. The 2D formats additionally render to terminal art and DXF
for direct part marking.

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

.. code-block:: python

   from pystrich.pdf417 import PDF417Encoder
   PDF417Encoder("WDBCA45D2HA327260").save_svg("pdf417-example.svg")

.. image:: examples/pdf417-example.svg
   :alt: PDF417 encoding "WDBCA45D2HA327260".

.. code-block:: python

   from pystrich.aztec import AztecEncoder
   AztecEncoder("https://github.com/mmulqueen/pyStrich").save_svg("aztec-example.svg")

.. image:: examples/aztec-example.svg
   :alt: Aztec Code encoding the pyStrich GitHub URL.

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
   pdf417
   aztec

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
   glossary
   changelog
   contributors

Background
----------

pyStrich was originally a fork of `huBarcode
<https://github.com/hudora/huBarcode>`_. huBarcode was developed by
`HuDoRa <https://www.hudora.de/de-en/>`_ from at least 2007, and has not
been active since late 2013. `Method B Ltd <https://www.method-b.uk/>`_
forked huBarcode as pyStrich to provide Python 3 support and to continue
development.
pyStrich has been substantially enhanced over the years and has gone far
beyond a simple port to Python 3. As of 2026, pyStrich is a modern Python
package with full use of typing, linting and a comprehensive test suite.

Thanks to the folks at HuDoRa for the original huBarcode library that
pyStrich grew out of.

Licence
-------

.. literalinclude:: ../LICENSE
   :language: text
