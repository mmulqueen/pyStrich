:og:description: Generate Aztec Code 2D barcodes in Python with pyStrich. Strong rotation tolerance, sizes from compact to full-range. PNG, SVG, EPS, DXF.

.. meta::
   :description: Generate Aztec Code 2D barcodes in Python with pyStrich. Strong rotation tolerance, sizes from compact to full-range. PNG, SVG, EPS, DXF.

Aztec Code
==========

Aztec Code is a 2D symbology used on transport tickets, boarding passes
and medical records. It needs no quiet zone, and its strong central
bullseye finder decodes reliably from any rotation. Symbols range from
15x15 modules (compact) up to 151x151 (full-range).

.. seealso::

   `Aztec Code on Wikipedia <https://en.wikipedia.org/wiki/Aztec_Code>`_
   for background on the symbology itself.

   Aztec Code is defined in `ISO/IEC 24778
   <https://www.iso.org/standard/82441.html>`_.

Example
-------

.. code-block:: python

   from pystrich.aztec import AztecEncoder

   encoder = AztecEncoder("https://github.com/mmulqueen/pyStrich")
   encoder.save_svg("aztec-example.svg")

.. image:: examples/aztec-example.svg
   :alt: Aztec Code encoding the pyStrich GitHub URL.

Sizing
------

The ``cellsize`` argument to :meth:`~AztecEncoder.save` and
:meth:`~AztecEncoder.get_imagedata` sets the pixel side length of one
module (default ``5``).

Aztec Code does not require a quiet zone, but pyStrich adds a 2-module
margin by default to give scanners a stable background. Pass
``quiet_zone=`` to :class:`AztecEncoder` to change the border width (in
modules) per call; pass ``0`` to drop the margin entirely.

.. code-block:: python

   AztecEncoder("Hello", quiet_zone=0).save("aztec-no-margin.png")

.. seealso::

   :doc:`printing` for guidance on selecting ``cellsize`` for printed
   output.

.. code-block:: python

   encoder = AztecEncoder("https://github.com/mmulqueen/pyStrich")
   encoder.save("aztec-large.png", cellsize=10)

.. image:: examples/aztec-large.png
   :alt: Aztec Code encoding the pyStrich GitHub URL rendered with cellsize=10.

Output formats
--------------

SVG output
~~~~~~~~~~

For embedding in web pages or any workflow that benefits from
resolution-independent output, use :meth:`~AztecEncoder.save_svg` (or
:meth:`~AztecEncoder.get_svg` to receive the SVG as a string).

.. code-block:: python

   from pystrich.marks import MarkShape

   AztecEncoder("https://github.com/mmulqueen/pyStrich").save_svg("aztec.svg")
   AztecEncoder("https://github.com/mmulqueen/pyStrich").save_svg(
       "aztec-circles.svg", mark_shape=MarkShape.CIRCULAR_CELLS
   )

The SVG's ``viewBox`` is in module units, while ``width`` and ``height``
scale by ``cellsize``. The ``mark_shape`` keyword selects how matched
cells are drawn -- horizontal runs of rectangles (the default) or one
filled circle per cell.

PNG output
~~~~~~~~~~

For raster output, use :meth:`~AztecEncoder.save` to write a PNG file or
:meth:`~AztecEncoder.get_imagedata` to receive the raw PNG bytes.

.. code-block:: python

   AztecEncoder("https://github.com/mmulqueen/pyStrich").save("aztec.png")

EPS output
~~~~~~~~~~

For embedding in LaTeX (``\includegraphics``) or other vector print
workflows, use :meth:`~AztecEncoder.save_eps` (or
:meth:`~AztecEncoder.get_eps` to receive the EPS as a string).

.. code-block:: python

   AztecEncoder("https://github.com/mmulqueen/pyStrich").save_eps("aztec.eps")

The ``cellsize`` argument is the side length of one module in PostScript
points (1 point = 1/72 inch).

Terminal output
~~~~~~~~~~~~~~~

For quick on-screen display, :meth:`~AztecEncoder.get_terminal_art`
returns a scannable rendering using Unicode half-block characters. Each
character represents two matrix rows and one column, so cells appear
roughly square in a typical fixed-width terminal font.

.. code-block:: python

   print(AztecEncoder("https://github.com/mmulqueen/pyStrich").get_terminal_art())

.. literalinclude:: examples/aztec-terminal.txt
   :language: text
   :class: terminal-art

By default the output is wrapped in ANSI escape codes that force a white
background and black foreground, so the symbol scans regardless of the
terminal's colour scheme. Pass ``ansi_bg=False`` for plain output
(correct only on a light-themed terminal).

DXF (CAD) output
~~~~~~~~~~~~~~~~

For direct part marking applications, :meth:`~AztecEncoder.get_dxf`
returns a DXF representation of the symbol that CAD and CAM tools can
read directly. The ``cellsize`` is in your chosen ``units`` (default
``"mm"``) rather than pixels.

.. code-block:: python

   encoder = AztecEncoder("WDBCA45D2HA327260")
   with open("part.dxf", "w") as f:
       f.write(encoder.get_dxf(cellsize=0.5, units="mm"))

The default ``inverse=True`` emits geometry for the light modules,
including the quiet zone -- so the bounding box frames the symbol. Pass
``inverse=False`` to emit only the dark modules instead, matching the
symbol's normal appearance; the bounding box then hugs the dark cells
and the quiet zone has to be reintroduced downstream.

Symbol kind and size
--------------------

Aztec Code comes in two formats:

* **Compact** symbols are 15x15 to 27x27 modules (1-4 data layers) and
  carry up to 76 codewords. Use them for short payloads where space is
  tight.
* **Full-range** symbols are 19x19 to 151x151 modules (1-32 data layers)
  and carry up to 1664 codewords. A reference grid runs through the
  larger symbols to keep scanners aligned across the whole symbol.

With the default ``symbol_kind="auto"`` the encoder picks the smallest
symbol that fits the payload at the requested error-correction
percentage. Compact is preferred over full-range at the same module
count.

.. code-block:: python

   # Force a full-range symbol even for short input.
   AztecEncoder("Hello", symbol_kind="full").save("aztec-full.png")

   # Pin both kind and layer count for a fixed symbol size.
   AztecEncoder("WDBCA45D2HA327260", symbol_kind="full", layers=5).save(
       "aztec-full-l5.png"
   )

Pinning ``layers`` requires an explicit ``symbol_kind``; the encoder
raises :class:`~pystrich.exceptions.PyStrichInvalidOption` otherwise. If
the payload does not fit at the requested size, it raises
:class:`~pystrich.exceptions.PyStrichInvalidInput`.

Error correction
----------------

Aztec Code embeds redundant data so that a partly-damaged symbol can
still be read. Unlike QR Code's discrete levels, the redundancy is set
as an integer percentage 5-95 via the ``ecc`` argument; the encoder
adds the requested percentage of the symbol capacity plus 3 codewords:

.. code-block:: python

   # Default: 23% -- the spec's recommended minimum.
   AztecEncoder("WDBCA45D2HA327260").save("aztec-default.png")

   # 50% redundancy for harsher environments.
   AztecEncoder("WDBCA45D2HA327260", ecc=50).save("aztec-high.png")

Higher percentages produce a denser symbol for the same payload (or,
equivalently, require a larger symbol to fit the same payload). The
default of 23% is the spec's recommended minimum for general use; pick
higher values for symbols likely to be partly obscured or printed on
surfaces likely to be scratched, smudged or torn.

Non-ASCII text
--------------

:class:`AztecEncoder` accepts any Unicode string directly and picks the
narrowest character set that fits. Wrap the input in :class:`AztecData`
only when you want to constrain that choice -- for example, to enforce
``"ascii"`` so a stray non-ASCII character raises instead of silently
growing the symbol:

================  ===================================================================
Encoding          Behaviour
================  ===================================================================
``"ascii"``       Raises :class:`~pystrich.exceptions.PyStrichInvalidInput` on any
                  byte > 127.
``"iso-8859-1"``  Latin-1. Declares ECI 3 at the start of the symbol so decoders
                  do not fall back to ASCII heuristics on high bytes.
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
   AztecEncoder("Ich dachte, Sie wären kräftiger").save("latin1.png")

.. image:: examples/aztec-latin1.png
   :alt: Aztec Code encoding "Ich dachte, Sie wären kräftiger" as Latin-1.

.. code-block:: python

   # Plain str: UTF-8 picked automatically, ECI 26 emitted.
   AztecEncoder("€5 親切にしろ 🐻‍❄️").save("utf8.png")

.. image:: examples/aztec-utf8.png
   :alt: Aztec Code encoding "€5 親切にしろ 🐻‍❄️" as UTF-8 (ECI 26).

If you pin an encoding that does not fit the input, the raised error
names the offending character and suggests the encoding that *would*
have worked:

.. doctest::

   >>> from pystrich.aztec import AztecData
   >>> AztecData("Ich dachte, Sie wären kräftiger", encoding="ascii")
   Traceback (most recent call last):
       ...
   pystrich.exceptions.PyStrichInvalidInput: AztecData encoding 'ascii' expects ASCII; got 'ä'. Try AztecData('Ich dachte, Sie wären kräftiger', encoding='iso-8859-1') or pass auto_encoding=True to select an encoding automatically.

Aztec Runes
-----------

Aztec Runes -- tiny single-byte Aztec-like symbols -- are not supported.
If you need them, you can build them on top of the geometry primitives
in :mod:`pystrich.aztec.placement`. Please file an issue on GitHub
describing what you need.

Anatomy
-------

Aztec symbols combine a few fixed structural elements with a variable
data area. The diagram below labels a full-range 5-layer symbol
(37x37 modules); compact symbols use the same parts in a smaller core
and skip the reference grid.

.. image:: examples/aztec-anatomy.svg
   :alt: Annotated Aztec Code showing the bullseye finder, orientation marks, mode message, reference grid, data layers and quiet zone.

* **Bullseye finder** -- concentric central squares (9x9 in compact
  symbols, 13x13 in full-range). The Aztec's signature pattern;
  scanners lock onto it from any rotation.
* **Orientation marks** -- L-shaped three-cell patterns at each corner
  of the core; the dark-cell count decreases clockwise (3, 2, 1, 0),
  encoding the symbol's rotation.
* **Mode message** -- the outermost ring of the core (one cell wide),
  encoding the symbol's layer count and :term:`codeword` count so the
  decoder knows how big the data area is.
* **Reference grid** -- sparse strips of alternating dark and light
  cells that run across full-range symbols every 16 modules to keep
  scanners aligned. Compact symbols do not need them.
* **Data layers** -- concentric rings of modules carrying the payload
  plus :term:`Reed-Solomon` error correction. The number of layers
  determines the symbol size.
* **Quiet zone** -- white margin around the symbol; not required by
  the spec.

API
---

.. autoclass:: pystrich.aztec.AztecEncoder

.. autoclass:: pystrich.aztec.AztecData
