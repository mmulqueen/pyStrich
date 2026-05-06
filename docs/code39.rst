Code 39
=======

Code 39 is a 1D symbology widely used for industrial labelling. The default
character set is uppercase letters, digits, space and ``-.$/+%``; pass
``full_ascii=True`` to encode any 7-bit character as a pair of symbols.

.. seealso::

   `Code 39 on Wikipedia <https://en.wikipedia.org/wiki/Code_39>`_ for
   background on the symbology itself.

Example
-------

.. code-block:: python

   from pystrich.code39 import Code39Encoder

   encoder = Code39Encoder("PART-1234")
   encoder.save("code39-example.png")

.. image:: examples/code39-example.png
   :alt: Code 39 barcode encoding "PART-1234".

Sizing
------

The ``bar_width`` argument to :meth:`~Code39Encoder.save` and
:meth:`~Code39Encoder.get_imagedata` sets the pixel width of the narrowest
bar (default ``3``).

.. code-block:: python

   encoder = Code39Encoder("PART-1234")
   encoder.save("code39-wide.png", bar_width=6)

.. image:: examples/code39-wide.png
   :alt: Code 39 barcode encoding "PART-1234" rendered with bar_width=6.

.. seealso::

   :doc:`printing` for guidance on selecting ``bar_width`` for printed
   output.

Label, font and layout
----------------------

The ``options`` dict passed to :class:`Code39Encoder` controls the
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
   Total image height in pixels. Defaults to ``120``.
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
   encoder = Code39Encoder("PART-1234", options=options)
   encoder.save("code39-custom.png", bar_width=4)

.. image:: examples/code39-custom.png
   :alt: Code 39 barcode encoding "PART-1234" with a taller image and larger label.

API
---

.. autoclass:: pystrich.code39.Code39Encoder
