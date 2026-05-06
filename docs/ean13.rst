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
:class:`EAN13RenderOptions` dict (see `Label baseline`_ below).

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
   encoder.save("ean13-example.png")

.. image:: examples/ean13-example.png
   :alt: EAN-13 barcode encoding "5050070007664".

Sizing and quiet zones
----------------------

The ``bar_width`` argument to :meth:`~EAN13Encoder.save` and
:meth:`~EAN13Encoder.get_imagedata` sets the pixel width of the narrowest
bar (default ``3``).

.. code-block:: python

   encoder = EAN13Encoder("5050070007664")
   encoder.save("ean13-wide.png", bar_width=6)

.. image:: examples/ean13-wide.png
   :alt: EAN-13 barcode encoding "5050070007664" rendered with bar_width=6.

The GS1 specification mandates an asymmetric quiet zone (white space) of
11 modules on the left and 7 modules on the right of the symbol; pyStrich
renders this automatically and it is not configurable. If you composite
the saved PNG into another image, do not crop into the white margin or
retail scanners may fail to read the symbol.

.. versionchanged:: 0.11
   The quiet zone was previously 9 modules on each side, which is below
   spec on the left.

.. seealso::

   :doc:`printing` for guidance on selecting ``bar_width`` for printed
   output.

Label baseline
--------------

By default pyStrich draws the leading number-system digit slightly higher
than the two main digit groups. To draw all three groups on a level baseline instead, pass an
``options`` dict with ``first_digit_y_offset`` set to ``0``:

.. code-block:: python

   encoder = EAN13Encoder(
       "5050070007664", options={"first_digit_y_offset": 0}
   )
   encoder.save("ean13-level.png")

The value is the gap between the first digit and the others, expressed as
a fraction of image height. ``0.1`` (the default) preserves the classic
look; ``0`` aligns all three groups.

.. versionadded:: 0.11
   The ``options`` dict and ``first_digit_y_offset`` key.

API
---

.. autoclass:: pystrich.ean13.EAN13Encoder

.. autoclass:: pystrich.ean13.EAN13RenderOptions
   :members:
