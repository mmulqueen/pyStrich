Data Matrix
===========

Data Matrix (ECC 200) is a 2D symbology suitable for short payloads, capable
of encoding up to 174 ASCII characters in pyStrich's implementation.

.. seealso::

   `Data Matrix on Wikipedia <https://en.wikipedia.org/wiki/Data_Matrix>`_
   for background on the symbology itself.

Example
-------

Wrap the input in :class:`DataMatrixData` and pass an explicit ``encoding``.
Use ``"ascii"`` for any payload that fits in 7-bit ASCII (URLs, identifiers,
GS1 AI strings); see :ref:`datamatrix-non-ascii` below for ``"iso-8859-1"``
and ``"utf-8"``.

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save("datamatrix-example.png")

.. image:: examples/datamatrix-example.png
   :alt: Data Matrix encoding the pyStrich GitHub URL.

Sizing
------

The ``cellsize`` argument to :meth:`~DataMatrixEncoder.save` and
:meth:`~DataMatrixEncoder.get_imagedata` sets the pixel side length of one
module (default ``5``).

.. code-block:: python

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save("datamatrix-large.png", cellsize=10)

.. image:: examples/datamatrix-large.png
   :alt: Data Matrix encoding the pyStrich GitHub URL rendered with cellsize=10.

The ``quiet_zone`` argument to :class:`DataMatrixEncoder` sets the width
(in modules) of the white border applied at render time. The Data Matrix
specification requires at least one module of quiet zone on each side;
pyStrich defaults to ``2`` (set
:data:`~pystrich.datamatrix.renderer.DATAMATRIX_DEFAULT_QUIET_ZONE`). Reduce
to ``1`` for the most compact symbol; increase if your printing process
tends to bleed into the margin.

.. code-block:: python

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload, quiet_zone=4)

.. seealso::

   :doc:`printing` for guidance on selecting ``cellsize`` for printed
   output.

SVG output
----------

For embedding in web pages or any workflow that benefits from
resolution-independent output, use :meth:`~DataMatrixEncoder.save_svg` (or
:meth:`~DataMatrixEncoder.get_svg` to receive the SVG as a string).

.. code-block:: python

   payload = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")
   DataMatrixEncoder(payload).save_svg("datamatrix.svg")

The SVG's ``viewBox`` is in module units, while ``width`` and ``height``
scale by ``cellsize``.

.. versionadded:: 0.12

DXF (CAD) output
----------------

For direct part marking applications -- where the symbol is engraved or
laser-etched onto a physical part -- :meth:`~DataMatrixEncoder.get_dxf`
returns a DXF representation of the symbol. DXF is the file format CAD and
CAM tools read; the output can be handed straight to the engraving or
etching tool. The ``cellsize`` is in your chosen ``units`` (default
``"mm"``) rather than pixels.

.. code-block:: python

   payload = DataMatrixData("PART-001234", encoding="ascii")
   encoder = DataMatrixEncoder(payload)
   with open("part.dxf", "w") as f:
       f.write(encoder.get_dxf(cellsize=0.5, units="mm"))

GS1 / FNC1
----------

.. seealso::

   `GS1 DataMatrix Guideline
   <https://www.gs1.org/standards/gs1-datamatrix-guideline/25>`_ -- the
   authoritative reference for AI selection, encoding rules and print
   quality requirements for GS1 Data Matrix.

GS1 Data Matrix uses an FNC1 codeword as the first symbol to signal that the
payload is a sequence of GS1 Application Identifiers, and again as a
separator after any variable-length AI that is not the final element of the
message. Pass :data:`FNC1` as the first segment to :class:`DataMatrixData`
to emit codeword 232 directly:

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder, FNC1

   # (01) GTIN-14 -- pad a GTIN-13 with a leading "0" indicator digit.
   payload = DataMatrixData(FNC1, "0105050070007664", encoding="ascii")
   DataMatrixEncoder(payload).save("gs1.png")

.. image:: examples/datamatrix-gs1.png
   :alt: GS1 Data Matrix encoding (01) GTIN 05050070007664.

A typical pharmaceutical / medical-device payload combines a GTIN with an
expiry date and a batch number. ``(01)`` and ``(17)`` are fixed-length, so
no separator is required between them; ``(10)`` is variable-length, but
because it is the last element of the message no trailing separator is
required either:

.. code-block:: python

   # (01) GTIN + (17) expiry YYMMDD + (10) batch
   payload = DataMatrixData(
       FNC1, "0109501234543213", "17261231", "10ABC123", encoding="ascii"
   )
   DataMatrixEncoder(payload).save("gs1-multi-fixed.png")

.. image:: examples/datamatrix-gs1-multi-fixed.png
   :alt: GS1 Data Matrix encoding (01) GTIN 09501234543213, (17) expiry 261231, (10) batch ABC123.

When a variable-length AI is followed by another AI, separate them with a
further :data:`FNC1`:

.. code-block:: python

   # (10) batch + (21) serial -- (10) is variable-length and not last,
   # so an FNC1 separator is required between the two AIs.
   payload = DataMatrixData(
       FNC1, "10ABC123", FNC1, "21SERIAL01", encoding="ascii"
   )
   DataMatrixEncoder(payload).save("gs1-multi.png")

.. image:: examples/datamatrix-gs1-multi.png
   :alt: GS1 Data Matrix encoding (10) batch ABC123 and (21) serial SERIAL01 separated by FNC1.

.. note::

   GS1 Data Matrix payloads must be ASCII -- the GS1 General Specifications
   restrict AI values to a 7-bit character set (essentially ASCII). Do not
   combine :data:`FNC1` with non-ASCII encodings.

.. deprecated:: 0.11

   Older code triggered FNC1 by prefixing the payload with ``chr(231)`` --
   originally a bug in this library that downstream users came to rely on
   (see `issue #13 <https://github.com/mmulqueen/pyStrich/issues/13>`_).
   The shim still works but emits a
   :class:`~pystrich.exceptions.Fnc1WorkaroundCompatWarning`. New code
   should use :data:`FNC1`.

.. _datamatrix-non-ascii:

Non-ASCII text
--------------

The Data Matrix ASCII codeword set only covers bytes 0-127. To encode
anything outside that range in a non-GS1 symbol, wrap the input in
:class:`DataMatrixData` and choose an encoding:

================  ===================================================================
Encoding          Behaviour
================  ===================================================================
``"compat"``      Default for backwards compatibility. Non-ASCII characters emit
                  :class:`~pystrich.exceptions.DataMatrixNonAsciiWarning` and produce
                  output that will not decode correctly. Deprecated; a future release
                  will make ``"ascii"`` the default.
``"ascii"``       Raises :class:`~pystrich.exceptions.PyStrichInvalidInput` on any
                  byte > 127.
``"iso-8859-1"``  Latin-1 -- the default character set for Data Matrix per ISO/IEC
                  16022. Bytes 128-255 are emitted via the Upper Shift codeword
                  (235); no ECI prefix is required and conformant decoders pick up
                  the encoding automatically.
``"utf-8"``       Declares ECI 26 once at the start of the symbol and byte-encodes
                  the input. Conformant decoders pick up the encoding automatically.
================  ===================================================================

.. tip::

   For the most compact symbol, prefer the most restrictive encoding that
   fits your data: ``"ascii"`` first, then ``"iso-8859-1"``, then
   ``"utf-8"``. Each step adds overhead -- Latin-1 spends an extra codeword
   per high byte, and UTF-8 adds a two-codeword ECI prefix and emits
   multi-byte sequences for anything outside ASCII.

.. code-block:: python

   from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder

   # Latin-1: smaller symbol if all your input fits in one byte per char.
   DataMatrixEncoder(DataMatrixData("café", encoding="iso-8859-1")).save("latin1.png")

.. image:: examples/datamatrix-latin1.png
   :alt: Data Matrix encoding "café" as Latin-1.

.. code-block:: python

   # UTF-8: required for anything outside Latin-1 (€, CJK, emoji).
   DataMatrixEncoder(DataMatrixData("€5 親切にしろ 🙂", encoding="utf-8")).save("utf8.png")

.. image:: examples/datamatrix-utf8.png
   :alt: Data Matrix encoding "€5 親切にしろ 🙂" as UTF-8 (ECI 26).

If you pass a string with the wrong encoding, the raised error suggests the
encoding that *would* have worked:

.. doctest::

   >>> from pystrich.datamatrix import DataMatrixData
   >>> DataMatrixData("café", encoding="ascii")
   Traceback (most recent call last):
       ...
   pystrich.exceptions.PyStrichInvalidInput: DataMatrix encoding 'ascii' expects ASCII; got 'café'. Try DataMatrixData('café', encoding='iso-8859-1').

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
