EAN-13
======

EAN-13 is the 13-digit retail product barcode -- the same symbology as
GTIN-13, the global identifier issued by GS1 and printed on virtually every
consumer product. Pass either 12 digits (the check digit will be computed
and appended) or 13 digits (the final digit is treated as a check digit and
recomputed).

.. seealso::

   `International Article Number on Wikipedia
   <https://en.wikipedia.org/wiki/International_Article_Number>`_ for
   background on the symbology itself.

.. warning::

   Real-world EAN-13 codes must be allocated by GS1 to your organisation;
   you cannot simply invent one. Inventing a code will produce a scannable
   barcode, but it will collide with -- or be rejected by -- retailer
   product databases. The number used in this page's examples,
   ``5050070007664``, is the GTIN of a real product (a DVD of *Road House*).

Input must be exactly 12 or 13 digits, ASCII ``0``-``9``. Anything else
raises :class:`~pystrich.exceptions.PyStrichInvalidInput`. The human-readable
label below the bars is mandated by the EAN-13 specification and always
rendered; the only customisation hook is the cosmetic
:class:`EAN13RenderOptions` dict (see `Sizing, label, font and layout`_ below).

The check digit is always computed by pyStrich; pass either 12 digits (it
is appended) or 13 digits (the supplied final digit is discarded and
recomputed):

.. doctest::

   >>> from pystrich.ean13 import EAN13Encoder
   >>> EAN13Encoder("505007000766").full_code
   '5050070007664'
   >>> EAN13Encoder("5050070007660").full_code
   '5050070007664'

Example
-------

.. code-block:: python

   from pystrich.ean13 import EAN13Encoder

   encoder = EAN13Encoder("5050070007664")
   encoder.save_svg("ean13-example.svg")

.. image:: examples/ean13-example.svg
   :alt: EAN-13 barcode encoding "5050070007664".

Sizing, label, font and layout
------------------------------

The ``bar_width`` argument to :meth:`~EAN13Encoder.save` and
:meth:`~EAN13Encoder.get_imagedata` sets the pixel width of the narrowest
bar (default ``3``).

The GS1 specification mandates an asymmetric quiet zone (white space) of
11 modules on the left and 7 modules on the right of the symbol; pyStrich
renders this automatically and it is not configurable. If you composite
the saved PNG into another image, do not crop into the white margin or
retail scanners may fail to read the symbol.

.. versionchanged:: 0.11
   The quiet zone was previously 9 modules on each side, which is below
   spec on the left.

By default pyStrich draws the leading number-system digit slightly higher
than the two main digit groups. To draw all three groups on a level baseline
instead, pass an ``options`` dict with ``first_digit_y_offset`` set to ``0``:

The value is the gap between the first digit and the others, expressed as
a fraction of image height. ``0.1`` (the default) preserves the classic
look; ``0`` aligns all three groups.

.. versionadded:: 0.11
   The ``options`` dict and ``first_digit_y_offset`` key.

.. seealso::

   :doc:`printing` for guidance on selecting ``bar_width`` for printed
   output.

.. code-block:: python

   encoder = EAN13Encoder(
       "5050070007664", options={"first_digit_y_offset": 0}
   )
   encoder.save("ean13-level.png", bar_width=4)

.. image:: examples/ean13-level.png
   :alt: EAN-13 barcode encoding "5050070007664" with a level label baseline.

Output formats
--------------

SVG output
~~~~~~~~~~

For embedding in web pages or any workflow that benefits from
resolution-independent output, use :meth:`~EAN13Encoder.save_svg` (or
:meth:`~EAN13Encoder.get_svg` to receive the SVG as a string).

.. code-block:: python

   EAN13Encoder("5050070007664").save_svg("ean13.svg")

.. image:: examples/ean13-example.svg
   :alt: SVG EAN-13 barcode encoding "5050070007664".

The SVG's ``viewBox`` is in module units, while ``width`` and ``height``
scale by ``bar_width``. The 11-module left and 7-module right quiet zones
required by GS1 are applied automatically. Guard bars extend 5 modules
below the data-bar baseline, also per the GS1 General Specifications.

.. versionadded:: 0.12

PNG output
~~~~~~~~~~

For raster output, use :meth:`~EAN13Encoder.save` to write a PNG file or
:meth:`~EAN13Encoder.get_imagedata` to receive the raw PNG bytes.

.. code-block:: python

   EAN13Encoder("5050070007664").save("ean13.png")

EPS output
~~~~~~~~~~

For embedding in LaTeX (``\includegraphics``) or other vector print
workflows, use :meth:`~EAN13Encoder.save_eps` (or
:meth:`~EAN13Encoder.get_eps` to receive the EPS as a string).

.. code-block:: python

   EAN13Encoder("5050070007664").save_eps("ean13.eps")

The ``bar_width`` argument is the width of the narrowest bar in PostScript
points (1 point = 1/72 inch). The GS1 quiet zones (11 modules left, 7
modules right) and the 5-module guard-bar offset are applied
automatically.

.. versionadded:: 0.12

API
---

.. autoclass:: pystrich.ean13.EAN13Encoder

.. autoclass:: pystrich.ean13.EAN13RenderOptions
   :members:
