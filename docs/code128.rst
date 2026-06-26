:og:description: Generate Code 128 barcodes in Python with pyStrich. Automatic A/B/C code-set switching, mod-103 checksum, full ASCII; PNG, SVG and EPS output.

.. meta::
   :description: Generate Code 128 barcodes in Python with pyStrich. Automatic A/B/C code-set switching, mod-103 checksum, full ASCII; PNG, SVG and EPS output.

Code 128
========

Code 128 is a high-density 1D symbology covering the full ASCII range.
pyStrich automatically switches between code sets A, B and C to minimise
symbol length, and computes the mod-103 checksum for you.

.. seealso::

   `Code 128 on Wikipedia <https://en.wikipedia.org/wiki/Code_128>`_ for
   background on the symbology itself.

Example
-------

.. code-block:: python

   from pystrich.code128 import Code128Encoder

   encoder = Code128Encoder("WDBCA45D2HA327260")
   encoder.save_svg("code128-example.svg")

.. image:: examples/code128-example.svg
   :alt: Code 128 barcode encoding "WDBCA45D2HA327260".

GS1-128
-------

.. seealso::

   `GS1-128 on Wikipedia <https://en.wikipedia.org/wiki/GS1-128>`_ for
   background on the GS1 variant.

GS1-128 is Code 128 with an FNC1 in the first data position, signalling
that the payload is a sequence of GS1 Application Identifiers.
:meth:`Code128Data.gs1` builds the payload from typed field wrappers and
handles FNC1 placement automatically -- one at the start of the message
and one after each variable-length Application Identifier that is not
the final element. Wrap each Application Identifier / value pair in
:class:`~pystrich.gs1.GS1Fixed` for fixed-length Application Identifiers
(``(01)``, ``(17)``, ``(11)`` ...) or :class:`~pystrich.gs1.GS1Variable`
otherwise. The GS1 General Specifications recommend variable-length
Application Identifiers come last:

.. code-block:: python

   from pystrich.code128 import Code128Data, Code128Encoder
   from pystrich.gs1 import GS1Fixed, GS1Variable

   # (01) GTIN + (17) expiry YYMMDD + (10) batch
   payload = Code128Data.gs1(
       GS1Fixed("01", "09501234543213"),
       GS1Fixed("17", "261231"),
       GS1Variable("10", "BF07"),
   )
   Code128Encoder(payload).save("code128-gs1.png")

.. image:: examples/code128-gs1.png
   :alt: GS1-128 barcode encoding (01) GTIN 09501234543213, (17) expiry 261231, (10) batch BF07.

For full control over the codeword stream -- or to mix FNC2, FNC3 or
Latin-1 segments with the GS1 markers -- pass :data:`FNC1` and the plain
Application Identifier / value strings to :class:`Code128Data` directly;
this is the path :meth:`~Code128Data.gs1` wraps.

Latin-1 text
------------

For Latin-1 input, wrap the payload in :class:`Code128Data` with
``encoding="iso-8859-1"`` (or ``auto_encoding=True``). Bytes 128-255
emit an FNC4 single-shift on the wire; characters outside Latin-1 are
rejected.

.. code-block:: python

   from pystrich.code128 import Code128Data, Code128Encoder

   Code128Encoder(
       Code128Data("Rausschmeißer", encoding="iso-8859-1")
   ).save("code128-latin1.png")

.. image:: examples/code128-latin1.png
   :alt: Code 128 barcode encoding "Rausschmeißer" via FNC4 Latin-1 shifts.

Sizing, label, font and layout
------------------------------

The ``bar_width`` argument to :meth:`~Code128Encoder.save` and
:meth:`~Code128Encoder.get_imagedata` sets the pixel width of the narrowest
bar (default ``3``).

The ``options`` dict passed to :class:`Code128Encoder` controls the
human-readable label and the surrounding layout. All keys are optional.

``show_label``
   Whether to render the human-readable label underneath the bars. Defaults
   to ``True``; set to ``False`` to suppress it.
``ttf_font``
   Absolute path to a TrueType font file used for the label. Defaults to a
   bundled bitmap font if unset.
``ttf_fontsize``
   Font size in points.
``height``
   Total image height in pixels. Defaults to roughly a third of the image
   width.
``label_border``
   Pixels of vertical space between the bars and the label.
``bottom_border``
   Pixels of vertical space between the label and the bottom edge.

.. seealso::

   :doc:`printing` for guidance on selecting ``bar_width`` for printed
   output.

.. code-block:: python

   options = {
       "height": 200,
       "label_border": 10,
       "bottom_border": 10,
       "ttf_fontsize": 24,
       # "ttf_font": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
   }
   encoder = Code128Encoder("WDBCA45D2HA327260", options=options)
   encoder.save("code128-custom.png", bar_width=4)

.. image:: examples/code128-custom.png
   :alt: Code 128 barcode encoding "WDBCA45D2HA327260" with a taller image and larger label.

Output formats
--------------

SVG output
~~~~~~~~~~

For embedding in web pages or any workflow that benefits from
resolution-independent output, use :meth:`~Code128Encoder.save_svg` (or
:meth:`~Code128Encoder.get_svg` to receive the SVG as a string).

.. code-block:: python

   Code128Encoder("WDBCA45D2HA327260").save_svg("code128.svg")

.. image:: examples/code128-example.svg
   :alt: SVG Code 128 barcode encoding "WDBCA45D2HA327260".

The SVG's ``viewBox`` is in module units (one narrow bar = one unit), while
``width`` and ``height`` scale by ``bar_width``. The 10-module quiet zones
mandated by the standard are applied automatically on each side.

.. versionadded:: 0.12

PNG output
~~~~~~~~~~

For raster output, use :meth:`~Code128Encoder.save` to write a PNG file or
:meth:`~Code128Encoder.get_imagedata` to receive the raw PNG bytes.

.. code-block:: python

   Code128Encoder("WDBCA45D2HA327260").save("code128.png")

EPS output
~~~~~~~~~~

For embedding in LaTeX (``\includegraphics``) or other vector print
workflows, use :meth:`~Code128Encoder.save_eps` (or
:meth:`~Code128Encoder.get_eps` to receive the EPS as a string).

.. code-block:: python

   Code128Encoder("WDBCA45D2HA327260").save_eps("code128.eps")

The ``bar_width`` argument is the width of the narrowest bar in PostScript
points (1 point = 1/72 inch). The 10-module quiet zones are applied
automatically.

.. versionadded:: 0.12

API
---

.. autoclass:: pystrich.code128.Code128Encoder

.. autoclass:: pystrich.code128.Code128Data

.. autoclass:: pystrich.code128.Code128Marker

.. py:data:: pystrich.code128.FNC1
.. py:data:: pystrich.code128.FNC2
.. py:data:: pystrich.code128.FNC3

   FNC marker constants (instances of :class:`Code128Marker`). Concatenate
   with strings via ``+`` to build a :class:`Code128Data`; ``FNC1`` in
   first position makes the symbol a GS1-128 (see :meth:`Code128Data.gs1`
   for the structured API).
