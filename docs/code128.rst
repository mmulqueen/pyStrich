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

   encoder = Code128Encoder("PyStrich-2026")
   encoder.save("code128-example.png")

.. image:: examples/code128-example.png
   :alt: Code 128 barcode encoding "PyStrich-2026".

Sizing
------

The ``bar_width`` argument to :meth:`~Code128Encoder.save` and
:meth:`~Code128Encoder.get_imagedata` sets the pixel width of the narrowest
bar (default ``3``).

.. code-block:: python

   encoder = Code128Encoder("PyStrich-2026")
   encoder.save("code128-wide.png", bar_width=6)

.. image:: examples/code128-wide.png
   :alt: Code 128 barcode encoding "PyStrich-2026" rendered with bar_width=6.

.. seealso::

   :doc:`printing` for guidance on selecting ``bar_width`` for printed
   output.

Label, font and layout
----------------------

The ``options`` dict passed to :class:`Code128Encoder` controls the
human-readable label and the surrounding layout (see also the identical
options on :doc:`code39`). All keys are optional.

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

.. code-block:: python

   options = {
       "height": 200,
       "label_border": 10,
       "bottom_border": 10,
       "ttf_fontsize": 24,
       # "ttf_font": "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
   }
   encoder = Code128Encoder("PyStrich-2026", options=options)
   encoder.save("code128-custom.png", bar_width=4)

.. image:: examples/code128-custom.png
   :alt: Code 128 barcode encoding "PyStrich-2026" with a taller image and larger label.

API
---

.. autoclass:: pystrich.code128.Code128Encoder
