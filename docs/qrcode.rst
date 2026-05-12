QR Code
=======

QR Code is a 2D symbology widely used for URLs and contact details.

.. seealso::

   `QR code on Wikipedia <https://en.wikipedia.org/wiki/QR_code>`_ for
   background on the symbology itself.

.. note::

   The QR support in pyStrich is less actively maintained than the other
   symbologies. If your project's main need is QR codes, consider whether
   `python-qrcode <https://github.com/lincolnloop/python-qrcode>`_ is a
   better fit -- it has a larger feature set (logos, styled modules).
   pyStrich's QR support is most useful when you also need one of its other
   symbologies and want a single dependency.

Example
-------

.. code-block:: python

   from pystrich.qrcode import QRCodeEncoder

   encoder = QRCodeEncoder("https://github.com/mmulqueen/pyStrich")
   encoder.save_svg("qrcode-example.svg")

.. image:: examples/qrcode-example.svg
   :alt: QR code encoding the pyStrich GitHub URL.

Sizing and quiet zone
---------------------

The ``cellsize`` argument to :meth:`~QRCodeEncoder.save` and
:meth:`~QRCodeEncoder.get_imagedata` sets the pixel side length of one
module (default ``5``).

.. seealso::

   :doc:`printing` for guidance on selecting ``cellsize`` for printed
   output.

.. code-block:: python

   encoder = QRCodeEncoder("https://github.com/mmulqueen/pyStrich")
   encoder.save("qrcode-large.png", cellsize=10)

.. image:: examples/qrcode-large.png
   :alt: QR code encoding the pyStrich GitHub URL rendered with cellsize=10.

Output formats
--------------

SVG output
~~~~~~~~~~

For embedding in web pages or any workflow that benefits from
resolution-independent output, use :meth:`~QRCodeEncoder.save_svg` (or
:meth:`~QRCodeEncoder.get_svg` to receive the SVG as a string).

.. code-block:: python

   from pystrich.marks import MarkShape

   QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg("qr.svg")
   QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg(
       "qr-circles.svg", mark_shape=MarkShape.CIRCULAR_CELLS
   )

.. only:: not text

   .. list-table::
      :widths: 50 50
      :header-rows: 1

      * - Default
        - ``mark_shape=MarkShape.CIRCULAR_CELLS``
      * - .. image:: examples/qrcode-example.svg
             :alt: SVG QR code with the default rectangular cells.
        - .. image:: examples/qrcode-example-circles.svg
             :alt: SVG QR code with circular cells.

The SVG's ``viewBox`` is in module units, while ``width`` and ``height``
scale by ``cellsize``. The ``mark_shape`` keyword selects how matched
cells are drawn -- horizontal runs of rectangles (the default) or one
filled circle per cell.

.. note::

   Circular cells fall outside the standard module shape and decoder
   support varies. Test with your target scanner before deploying.

.. versionadded:: 0.12

PNG output
~~~~~~~~~~

For raster output, use :meth:`~QRCodeEncoder.save` to write a PNG file or
:meth:`~QRCodeEncoder.get_imagedata` to receive the raw PNG bytes.

.. code-block:: python

   QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save("qrcode.png")

EPS output
~~~~~~~~~~

For embedding in LaTeX (``\includegraphics``) or other vector print
workflows, use :meth:`~QRCodeEncoder.save_eps` (or
:meth:`~QRCodeEncoder.get_eps` to receive the EPS as a string).

.. code-block:: python

   QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_eps("qr.eps")

The ``cellsize`` argument is the side length of one module in PostScript
points (1 point = 1/72 inch).

.. versionadded:: 0.12

Terminal output
~~~~~~~~~~~~~~~

For quick on-screen display, :meth:`~QRCodeEncoder.get_terminal_art`
returns a scannable rendering using Unicode half-block characters. Each
character represents two matrix rows and one column, so cells appear
roughly square in a typical fixed-width terminal font.

.. code-block:: python

   print(QRCodeEncoder("https://github.com/mmulqueen/pyStrich").get_terminal_art())

.. literalinclude:: examples/qrcode-terminal.txt
   :language: text
   :class: terminal-art

By default the output is wrapped in ANSI escape codes that force a white
background and black foreground, so the symbol scans regardless of the
terminal's colour scheme. Pass ``ansi_bg=False`` for plain output (correct
only on a light-themed terminal).

.. versionadded:: 0.12

DXF (CAD) output
~~~~~~~~~~~~~~~~

For direct part marking applications, :meth:`~QRCodeEncoder.get_dxf`
returns a DXF representation of the symbol that CAD and CAM tools can read
directly. The ``cellsize`` is in your chosen ``units`` (default ``"mm"``)
rather than pixels.

.. code-block:: python

   encoder = QRCodeEncoder("WDBCA45D2HA327260")
   with open("part.dxf", "w") as f:
       f.write(encoder.get_dxf(cellsize=0.5, units="mm"))

The default ``inverse=True`` emits geometry for the light modules,
including the quiet zone -- so the bounding box frames the symbol. Pass
``inverse=False`` to emit only the dark modules instead, matching the
symbol's normal appearance; the bounding box then hugs the dark cells and
the quiet zone has to be reintroduced downstream.

Error correction level
----------------------

QR Codes embed redundant data so that a partly-damaged symbol can still be
read. The error correction level (ECL) sets how much redundancy is added,
and is one of:

==========  =====================================================
``"L"``     Low: ~7% of codewords recoverable. Smallest symbol.
``"M"``     Medium: ~15%. **Default** if ``ecl`` is not supplied.
``"Q"``     Quartile: ~25%.
``"H"``     High: ~30%. Largest symbol; tolerates the most damage.
==========  =====================================================

Higher levels produce a denser symbol for the same payload (or, equivalently,
require a larger symbol to fit the same payload), so pick the lowest level
that meets your durability needs. ``"H"`` is typically reserved for symbols
that may be partly obscured (e.g. by a logo) or printed on surfaces likely
to be scratched, smudged or torn.

.. code-block:: python

   QRCodeEncoder("https://en.wikipedia.org/wiki/Kings_River_(California)", ecl="H").save("qr-high.png")

GS1 Digital Link
----------------

`GS1 Digital Link <https://www.gs1uk.org/standards-services/get-market-ready/qr-codes-powered-by-gs1/design-guidelines>`_
encodes a GTIN (with optional batch, expiry, serial, ...) as a URL.
It's just a URL -- pass it to :class:`QRCodeEncoder` directly:

.. code-block:: python

   QRCodeEncoder("https://id.gs1.org/01/05050070007664/10/W126").save("dl.png")

Raw AI-syntax GS1 QR (FNC1 mode indicator) is not supported; for that,
use :doc:`datamatrix`.

.. _qrcode-non-ascii:

Non-ASCII text
--------------

:class:`QRCodeEncoder` accepts any Unicode string directly and picks the
narrowest character set that fits. Wrap the input in :class:`QRCodeData`
only when you want to constrain that choice -- for example, to enforce
``"ascii"`` so a stray non-ASCII character raises instead of silently
growing the symbol:

================  ===================================================================
Encoding          Behaviour
================  ===================================================================
``"ascii"``       Raises :class:`~pystrich.exceptions.PyStrichInvalidInput` on any
                  byte > 127.
``"iso-8859-1"``  Latin-1. Declares ECI 3 at the start of the symbol so decoders
                  do not fall back to Shift-JIS heuristics on high bytes.
``"utf-8"``       Declares ECI 26 and byte-encodes the input. Conformant decoders
                  pick up the encoding automatically.
================  ===================================================================

.. tip::

   The auto-selected encoding is always the narrowest one that fits, so
   passing a plain ``str`` already gives you the smallest symbol. Picking
   an encoding by hand is mostly useful for input validation -- e.g.
   reject anything outside ASCII at the boundary.

.. code-block:: python

   # Plain str: Latin-1 picked automatically, ECI 3 emitted.
   QRCodeEncoder("Ich dachte, Sie wären kräftiger").save("latin1.png")

.. code-block:: python

   # Plain str: UTF-8 picked automatically, ECI 26 emitted.
   QRCodeEncoder("€5 親切にしろ 🐻‍❄️").save("utf8.png")

If you pin an encoding that does not fit the input, the raised error
names the offending character and suggests the encoding that *would*
have worked:

.. doctest::

   >>> from pystrich.qrcode import QRCodeData
   >>> QRCodeData("Ich dachte, Sie wären kräftiger", encoding="ascii")
   Traceback (most recent call last):
       ...
   pystrich.exceptions.PyStrichInvalidInput: QRCodeData encoding 'ascii' expects ASCII; got 'ä'. Try QRCodeData('Ich dachte, Sie wären kräftiger', encoding='iso-8859-1') or pass auto_encoding=True to select an encoding automatically.

API
---

.. autoclass:: pystrich.qrcode.QRCodeEncoder

.. autoclass:: pystrich.qrcode.QRCodeData
