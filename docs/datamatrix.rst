:og:description: Generate Data Matrix (ECC 200) barcodes in Python with pyStrich. Encodes up to 1558 ASCII characters; PNG, SVG, EPS, DXF and terminal art output.

.. meta::
   :description: Generate Data Matrix (ECC 200) barcodes in Python with pyStrich. Encodes up to 1558 ASCII characters; PNG, SVG, EPS, DXF and terminal art output.

Data Matrix
===========

Data Matrix (ECC 200) is a 2D symbology suitable for short payloads, capable
of encoding up to 1558 ASCII characters in the largest 144x144 symbol.

.. seealso::

   `Data Matrix on Wikipedia <https://en.wikipedia.org/wiki/Data_Matrix>`_
   for background on the symbology itself.

   Data Matrix barcodes are defined in `ISO/IEC 16022
   <https://www.iso.org/standard/80926.html>`_.

Example
-------

Wrap the input in :class:`DataMatrixData`. The simplest path is
``auto_encoding=True``, which picks the narrowest encoding that fits the
input automatically. For control over the encoded byte sequence -- to
enforce ``"ascii"`` for a 7-bit payload (URLs, identifiers, GS1 Application
Identifier strings)
or to require Latin-1 / UTF-8 -- pass an explicit ``encoding`` instead;
see :ref:`datamatrix-non-ascii` below.

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", auto_encoding=True)
   DataMatrixEncoder(payload).save_svg("datamatrix-example.svg")

.. image:: examples/datamatrix-example.svg
   :alt: Data Matrix encoding the pyStrich GitHub URL.

Sizing and quiet zone
---------------------

The ``cellsize`` argument to :meth:`~DataMatrixEncoder.save` and
:meth:`~DataMatrixEncoder.get_imagedata` sets the pixel side length of one
module (default ``5``).

The ``quiet_zone`` argument to :class:`DataMatrixEncoder` sets the width
(in modules) of the white border applied at render time. The Data Matrix
specification requires at least one module of quiet zone on each side;
pyStrich defaults to ``2`` (set
:data:`~pystrich.datamatrix.renderer.DATAMATRIX_DEFAULT_QUIET_ZONE`). Reduce
to ``1`` for the most compact symbol; increase if your printing process
tends to bleed into the margin.

.. seealso::

   :doc:`printing` for guidance on selecting ``cellsize`` for printed
   output.

.. code-block:: python

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save("datamatrix-large.png", cellsize=10)

.. image:: examples/datamatrix-large.png
   :alt: Data Matrix encoding the pyStrich GitHub URL rendered with cellsize=10.

Output formats
--------------

SVG output
~~~~~~~~~~

For embedding in web pages or any workflow that benefits from
resolution-independent output, use :meth:`~DataMatrixEncoder.save_svg` (or
:meth:`~DataMatrixEncoder.get_svg` to receive the SVG as a string).

.. code-block:: python

   from pystrich.marks import MarkShape

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save_svg("datamatrix.svg")
   DataMatrixEncoder(payload).save_svg(
       "datamatrix-circles.svg", mark_shape=MarkShape.CIRCULAR_CELLS
   )

.. only:: not text

   .. list-table::
      :widths: 50 50
      :header-rows: 1

      * - Default
        - ``mark_shape=MarkShape.CIRCULAR_CELLS``
      * - .. image:: examples/datamatrix-example.svg
             :alt: SVG Data Matrix with the default rectangular cells.
        - .. image:: examples/datamatrix-example-circles.svg
             :alt: SVG Data Matrix with circular cells.

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

For raster output, use :meth:`~DataMatrixEncoder.save` to write a PNG file
or :meth:`~DataMatrixEncoder.get_imagedata` to receive the raw PNG bytes.

.. code-block:: python

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save("datamatrix.png")

EPS output
~~~~~~~~~~

For embedding in LaTeX (``\includegraphics``) or other vector print
workflows, use :meth:`~DataMatrixEncoder.save_eps` (or
:meth:`~DataMatrixEncoder.get_eps` to receive the EPS as a string).

.. code-block:: python

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save_eps("datamatrix.eps")

The ``cellsize`` argument is the side length of one module in PostScript
points (1 point = 1/72 inch).

.. versionadded:: 0.12

Terminal output
~~~~~~~~~~~~~~~

For quick on-screen display, :meth:`~DataMatrixEncoder.get_terminal_art`
returns a scannable rendering using Unicode half-block characters. Each
character represents two matrix rows and one column, so cells appear
roughly square in a typical fixed-width terminal font.

.. code-block:: python

   print(DataMatrixEncoder(payload).get_terminal_art())

.. literalinclude:: examples/datamatrix-terminal.txt
   :language: text
   :class: terminal-art

By default the output is wrapped in ANSI escape codes that force a white
background and black foreground, so the symbol scans regardless of the
terminal's colour scheme. Pass ``ansi_bg=False`` for plain output (correct
only on a light-themed terminal).

.. versionadded:: 0.12

DXF (CAD) output
~~~~~~~~~~~~~~~~

For direct part marking applications -- where the symbol is engraved or
laser-etched onto a physical part -- :meth:`~DataMatrixEncoder.get_dxf`
returns a DXF representation of the symbol. DXF is the file format CAD and
CAM tools read; the output can be handed straight to the engraving or
etching tool. The ``cellsize`` is in your chosen ``units`` (default
``"mm"``) rather than pixels.

.. code-block:: python

   payload = DataMatrixData("A1268172415", encoding="ascii")
   encoder = DataMatrixEncoder(payload)
   with open("part.dxf", "w") as f:
       f.write(encoder.get_dxf(cellsize=0.5, units="mm"))

The default ``inverse=True`` emits geometry for the light modules,
including the quiet zone -- so the bounding box frames the symbol. Pass
``inverse=False`` to emit only the dark modules instead, matching the
symbol's normal appearance; the bounding box then hugs the dark cells and
the quiet zone has to be reintroduced downstream.

.. seealso::

   `SAE AS9132B
   <https://www.sae.org/standards/as9132b-data-matrix-quality-requirements-parts-marking>`_
   -- aerospace/defense quality standard for Data Matrix marks applied to metal parts.

GS1 / FNC1
----------

.. seealso::

   `GS1 DataMatrix Guideline
   <https://www.gs1.org/standards/gs1-datamatrix-guideline/25>`_ -- the
   authoritative reference for Application Identifier selection, encoding
   rules and print quality requirements for GS1 Data Matrix.

GS1 Data Matrix uses an FNC1 codeword as the first symbol to signal that
the payload is a sequence of GS1 Application Identifiers, and again as a
separator after any variable-length Application Identifier that is not
the final element of the message. :meth:`DataMatrixData.gs1` builds the
payload from typed field wrappers and handles separator placement
automatically. Wrap each Application Identifier / value pair in
:class:`~pystrich.gs1.GS1Fixed` for Application Identifiers whose data
length is fixed or :class:`~pystrich.gs1.GS1Variable` otherwise:

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder
   from pystrich.gs1 import GS1Fixed, GS1Variable

   # (01) GTIN-14 -- pad a GTIN-13 with a leading "0" indicator digit.
   payload = DataMatrixData.gs1(GS1Fixed("01", "05050070007664"))
   DataMatrixEncoder(payload).save("gs1.png")

.. image:: examples/datamatrix-gs1.png
   :alt: GS1 Data Matrix encoding (01) GTIN 05050070007664.

A typical pharmaceutical / medical-device payload combines a GTIN with
an expiry date and a batch number. ``(01)`` and ``(17)`` are
fixed-length, so :class:`~pystrich.gs1.GS1Fixed` declares them; ``(10)``
is variable-length, so :class:`~pystrich.gs1.GS1Variable` carries it.
The GS1 General Specifications recommend variable-length Application
Identifiers come last -- positioning ``(10)`` at the end of the message
means no FNC1 separator is needed between the fields:

.. code-block:: python

   payload = DataMatrixData.gs1(
       GS1Fixed("01", "09501234543213"),
       GS1Fixed("17", "261231"),
       GS1Variable("10", "BF07"),
   )
   DataMatrixEncoder(payload).save("gs1-multi-fixed.png")

.. image:: examples/datamatrix-gs1-multi-fixed.png
   :alt: GS1 Data Matrix encoding (01) GTIN 09501234543213, (17) expiry 261231, (10) batch BF07.

When a variable-length Application Identifier is not the last field, the
FNC1 separator is inserted automatically:

.. code-block:: python

   payload = DataMatrixData.gs1(
       GS1Variable("10", "BF07"),
       GS1Variable("21", "19890519"),
   )
   DataMatrixEncoder(payload).save("gs1-multi.png")

.. image:: examples/datamatrix-gs1-multi.png
   :alt: GS1 Data Matrix encoding (10) batch BF07 and (21) serial 19890519 separated by FNC1.

For full control over the codeword stream, pass :data:`FNC1` and the
plain Application Identifier / value strings to :class:`DataMatrixData`
directly -- this is
the path :meth:`~DataMatrixData.gs1` wraps:

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, FNC1

   payload = DataMatrixData(FNC1, "10BF07", FNC1, "2119890519", encoding="ascii")

.. note::

   GS1 Data Matrix payloads must be ASCII -- the GS1 General
   Specifications restrict Application Identifier values to a 7-bit
   character set (essentially ASCII). :meth:`~DataMatrixData.gs1` hardcodes
   ``"ascii"``; when placing FNC1 yourself, do not combine it with
   non-ASCII encodings.

.. deprecated:: 0.11

   Older code triggered FNC1 by prefixing the payload with ``chr(231)`` --
   originally a bug in this library that downstream users came to rely on
   (see `issue #13 <https://github.com/mmulqueen/pyStrich/issues/13>`_).
   The shim still works but emits a
   :class:`~pystrich.exceptions.Fnc1WorkaroundCompatWarning`. New code
   should use :meth:`~DataMatrixData.gs1` (or :data:`FNC1` for the raw
   path).

.. _datamatrix-non-ascii:

Non-ASCII text
--------------

The Data Matrix ASCII codeword set only covers bytes 0-127. To encode
anything outside that range in a non-GS1 symbol, wrap the input in
:class:`DataMatrixData` and either pass ``auto_encoding=True`` (the
constructor picks the narrowest fitting encoding for you) or specify an
encoding explicitly:

================  ===================================================================
Encoding          Behaviour
================  ===================================================================
``"ascii"``       Raises :class:`~pystrich.exceptions.PyStrichInvalidInput` on any
                  byte > 127.
``"iso-8859-1"``  Latin-1 -- the default character set for Data Matrix per ISO/IEC
                  16022. Bytes 128-255 are emitted via the Upper Shift codeword
                  (235); no ECI prefix is required and conformant decoders pick up
                  the encoding automatically.
``"utf-8"``       Declares ECI 26 once at the start of the symbol and byte-encodes
                  the input. Conformant decoders pick up the encoding automatically.
``"compat"``      Legacy lenient mode. Non-ASCII characters emit
                  :class:`~pystrich.exceptions.DataMatrixNonAsciiWarning` and produce
                  output that will not decode correctly. Deprecated; pick one of
                  the above instead.
================  ===================================================================

.. tip::

   For the most compact symbol, prefer the most restrictive encoding that
   fits your data: ``"ascii"`` first, then ``"iso-8859-1"``, then
   ``"utf-8"``. Each step adds overhead -- Latin-1 spends an extra codeword
   per high byte, and UTF-8 adds a two-codeword ECI prefix and emits
   multi-byte sequences for anything outside ASCII. ``auto_encoding=True``
   makes the same choice for you if you'd rather not pick by hand.

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

   # Latin-1: smaller symbol if all your input fits in one byte per char.
   DataMatrixEncoder(DataMatrixData("Ich dachte, Sie wären kräftiger", encoding="iso-8859-1")).save("latin1.png")

.. image:: examples/datamatrix-latin1.png
   :alt: Data Matrix encoding "Ich dachte, Sie wären kräftiger" as Latin-1.

.. code-block:: python

   # UTF-8: required for anything outside Latin-1 (€, CJK, emoji).
   DataMatrixEncoder(DataMatrixData("€5 親切にしろ 🐻‍❄️", encoding="utf-8")).save("utf8.png")

.. image:: examples/datamatrix-utf8.png
   :alt: Data Matrix encoding "€5 親切にしろ 🐻‍❄️" as UTF-8 (ECI 26).

If you pass a string with the wrong encoding, the raised error suggests
the encoding that *would* have worked:

.. doctest::

   >>> from pystrich.datamatrix import DataMatrixData
   >>> DataMatrixData("Ich dachte, Sie wären kräftiger", encoding="ascii")
   Traceback (most recent call last):
       ...
   pystrich.exceptions.PyStrichInvalidInput: DataMatrixData encoding ASCII cannot encode the input; try DataMatrixData('Ich dachte, Sie wären kräftiger', encoding='iso-8859-1') or pass auto_encoding=True to select an encoding automatically.

Encodation modes
----------------

pyStrich supports the following encodation modes: ASCII/bytes (with
numeric digit pairing), Text, C40 and X12. Base 256 is not currently
supported. Due to concerns about decoder/scanner support, we have made
the decision not to implement EDIFACT.\ [#edifact]_

.. [#edifact] Some Honeywell scanners decode every other Data Matrix
   mode but not EDIFACT. See `Honeywell's support article
   <https://sps-support.honeywell.com/s/article/Can-Honeywell-scanners-read-Data-Matrix-Base-256-mode-symbols>`_.

..
   Wayback Machine snapshots in case the Honeywell links die:
   https://web.archive.org/web/20260608122836/https://sps-support.honeywell.com/s/article/Can-Honeywell-scanners-read-Data-Matrix-Base-256-mode-symbols
   https://web.archive.org/web/20260608122743/https://sps-support.honeywell.com/sfc/servlet.shepherd/document/download/0692G00000QymxFQAR?operationContext=S1

Anatomy
-------

Each Data Matrix region is built from the same three elements. Sizes
from 10x10 to 26x26 use a single region; larger sizes tile the region
in a 2x2, 4x4 or 6x6 grid. The diagram below labels a 36x36 ECC 200
symbol (2x2 regions of 16x16).

.. image:: examples/datamatrix-anatomy.svg
   :alt: Annotated 36x36 Data Matrix showing the solid L finder, timing pattern, data area and quiet zone across four regions.

* **Solid L finder** -- two solid edges (left and bottom of each
  region) that identify the symbol's size and orientation.
* **Timing pattern** -- the opposite two edges of each region
  (top and right), alternating dark and light cells so the scanner
  can count modules across the region.
* **Data area** -- everything inside the region's L and timing edges:
  the encoded :term:`codewords <codeword>` plus :term:`Reed-Solomon`
  error correction, mapped to cells by the ECC 200 placement
  algorithm.
* **Quiet zone** -- white margin around the symbol; the spec requires
  at least one module, and pyStrich defaults to two.

API
---

.. autoclass:: pystrich.datamatrix.DataMatrixEncoder

.. autoclass:: pystrich.datamatrix.DataMatrixData

.. autoclass:: pystrich.datamatrix.DataMatrixCodeword

.. py:data:: pystrich.datamatrix.FNC1

   The GS1 FNC1 marker (Data Matrix codeword 232). An instance of
   :class:`DataMatrixCodeword`; concatenate with strings via ``+`` to build a
   GS1 payload.

   .. versionadded:: 0.11
