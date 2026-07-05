:min-version: 0.16
:og:description: Generate GS1 ITF-14 and basic Interleaved 2 of 5 barcodes in Python with pyStrich. PNG, SVG and EPS output.

.. meta::
   :description: Generate GS1 ITF-14 and basic Interleaved 2 of 5 barcodes in Python with pyStrich. PNG, SVG and EPS output.

.. title:: ITF

ITF-14
======

.. versionadded:: 0.16
   ITF-14 and Interleaved 2 of 5 support were added in this release.

ITF-14 is the GS1 barcode for a GTIN-14 -- the 14-digit identifier printed on
shipping cartons and cases rather than on the retail item inside. It is an
application of Interleaved 2 of 5 (ITF), which packs pairs of digits into
alternating bars and spaces, wrapped in a *bearer bar* that frames the symbol.
Pass either 13 digits (the check digit is computed and appended) or 14 digits
(the final digit is treated as a check digit and recomputed).

.. seealso::

   `Interleaved 2 of 5 on Wikipedia
   <https://en.wikipedia.org/wiki/Interleaved_2_of_5>`_ for background on the
   symbology.

   Interleaved 2 of 5 barcodes are defined in `ISO/IEC 16390
   <https://www.iso.org/standard/43898.html>`_.

.. warning::

   Real-world GTIN-14 codes are derived from a GS1-allocated GTIN; you cannot
   simply invent one.

Input must be exactly 13 or 14 digits, ASCII ``0``-``9``. Anything else raises
:class:`~pystrich.exceptions.PyStrichInvalidInput`. The 14-digit human-readable
label below the bars is rendered by default (see :ref:`itf-label` to suppress it).

The check digit is always computed by pyStrich; pass either 13 digits (it is
appended) or 14 digits (the supplied final digit is discarded and recomputed):

.. doctest::

   >>> from pystrich.itf import ITF14Encoder
   >>> ITF14Encoder("1505007000766").full_code
   '15050070007661'
   >>> ITF14Encoder("15050070007660").full_code
   '15050070007661'

Example
-------

.. code-block:: python

   from pystrich.itf import ITF14Encoder

   encoder = ITF14Encoder("1505007000766")
   encoder.save_svg("itf14-example.svg")

.. image:: examples/itf14-example.svg
   :alt: ITF-14 barcode encoding "15050070007661".

Bearer bar
----------

ITF-14 is drawn with a full-frame bearer bar -- the heavy border enclosing the
symbol. It reduces the chance of a partial scan being
misread as a short, valid code. Its thickness defaults to 4 narrow-bar widths;
adjust it with the ``bearer_width`` key of :class:`ITFRenderOptions` (set it to
``0`` to omit the bearer):

.. code-block:: python

   ITF14Encoder("1505007000766", options={"bearer_width": 6}).save("itf14.png")

.. _itf-label:

Label
-----

The human-readable label is rendered by default. To lay out your own instead,
suppress it with ``show_label``:

.. code-block:: python

   ITF14Encoder("1505007000766", options={"show_label": False}).save("itf14.png")

Interleaved 2 of 5
------------------

For a plain Interleaved 2 of 5 symbol -- any even number of digits -- use
:class:`~pystrich.itf.ITFEncoder` directly. It has no bearer bar by
default, but accepts the same ``bearer_width`` option.

.. code-block:: python

   from pystrich.itf import ITFEncoder

   ITFEncoder("1234567890").save_svg("itf-example.svg")

.. image:: examples/itf-example.svg
   :alt: Interleaved 2 of 5 barcode encoding "1234567890".

Output formats
--------------

Like the other 1D symbologies, ITF-14 renders to SVG
(:meth:`~pystrich.itf.ITF14Encoder.save_svg`), PNG
(:meth:`~pystrich.itf.ITF14Encoder.save`) and EPS
(:meth:`~pystrich.itf.ITF14Encoder.save_eps`). The ``bar_width`` argument sets
the width of the narrowest bar.

.. seealso::

   :doc:`printing` for guidance on selecting ``bar_width`` for printed output.

API
---

.. autoclass:: pystrich.itf.ITF14Encoder

.. autoclass:: pystrich.itf.ITFEncoder

.. autoclass:: pystrich.itf.ITFRenderOptions
   :members:
