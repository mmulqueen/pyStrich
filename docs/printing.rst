Printing barcodes
=================

The most common cause of "my barcode does not scan" is not encoding -- the
bars are too small. Scanners need the narrowest bar (1D) or one module
(2D) -- the *X-dimension* -- to be wide enough for their optics to
resolve. As features shrink below that threshold, read rates drop like a
stone. Most barcode standards specify a minimum and recommended
X-dimension for each application:

================  ======================  ================================
Symbology         X-dimension (typical)   Notes
================  ======================  ================================
Code 39           0.19 - 0.50 mm          0.25 mm is a safe default for
                                          industrial labelling.
Code 128          0.19 - 0.50 mm          0.25 mm reads reliably with
                                          most fixed and handheld scanners.
EAN-13 (retail)   0.26 - 0.66 mm          GS1 specifies a nominal X of
                                          0.33 mm (100% magnification);
                                          retail scanning typically allows
                                          80%-200% of nominal.
Data Matrix       0.25 - 0.50 mm          Smaller is feasible for direct
                                          part marking with appropriate
                                          imagers.
QR Code           0.25 - 0.50 mm          Mobile phone cameras typically
                                          need >=0.4 mm at arm's length.
================  ======================  ================================

These are guidance values, not specifications -- always confirm against
the relevant standard for your application (GS1 General Specifications
for retail and supply-chain symbols; ISO/IEC 15415 / 15416 for print
quality verification).

.. tip::

   Reach for SVG or EPS where your toolchain supports them. Vector
   output scales losslessly, so you size the symbol at layout time
   rather than locking in a physical size at encode time.

Vector output (SVG / EPS)
-------------------------

For SVG and EPS, pyStrich doesn't determine the print size at all. The
output is resolution-independent -- pick any ``bar_width`` (or
``cellsize``), and let the consuming layout tool scale to the X-dimension
you need:

* **SVG**: set ``width`` and ``height`` in HTML / CSS, or via the
  ``viewBox`` in your design tool.
* **EPS**: scale at inclusion time -- ``\includegraphics[width=40mm]{...}``
  in LaTeX, or via the placement size in Illustrator / InDesign.

The EPS ``bar_width`` is in PostScript points (1 pt = 1/72 inch ≈
0.353 mm), so the default already produces a physically sensible size if
you don't override it at inclusion time.

.. tip::

   For PDF output, embed the SVG in an HTML template and render with
   `WeasyPrint <https://weasyprint.org/>`_. This is a clean route to
   multi-up label sheets, packing slips and similar print-ready
   documents.

Raster output (PNG)
-------------------

PNG is the only output format where ``bar_width`` / ``cellsize`` fixes
the print size, because raster images don't scale losslessly. Working
back from a target X-dimension and printer DPI:

.. code-block:: text

   bar_width (px) = X-dimension (mm) * DPI / 25.4

At 300 DPI, an X-dimension of 0.25 mm requires ``bar_width=3`` (rounded
up from 2.95). At 600 DPI, the same X-dimension requires ``bar_width=6``.

Round *up* to the nearest integer pixel; rounding down pushes the
X-dimension below the readable limit.

Quiet zones
-----------

Every symbology requires white space (the *quiet zone*) around the
symbol so scanners can locate its boundaries. pyStrich emits a quiet
zone automatically; do not crop into the white margin when compositing
the output into another image.

=============  =====================================================
Symbology      Quiet zone applied by pyStrich
=============  =====================================================
Code 39        10x ``bar_width`` on each side.
Code 128       10x ``bar_width`` on each side.
EAN-13         11x ``bar_width`` left, 7x right (mandated by GS1).
Data Matrix    Configurable via ``quiet_zone`` (default 2 modules,
               spec minimum 1 module).
QR Code        4 modules on each side (mandated by spec).
=============  =====================================================

Verification
------------

If a printed barcode does not scan reliably:

1. Try to scan it on screen first. If it fails on screen, the encoding
   or sizing is wrong; if it succeeds on screen but fails in print, the
   print process is the issue.
2. Measure the X-dimension with a ruler or loupe and verify the quiet
   zone is intact -- not cropped, not printed against a coloured
   background.
3. Check print contrast -- low-DPI thermal printers or worn ribbons can
   produce bars that are too grey to be read.

For production deployments printing barcodes at scale, consider using a
print-quality verifier (an instrument that scores symbols against
ISO/IEC 15415 / 15416). A passing grade once during integration is
worth more than re-printing a thousand failed labels.