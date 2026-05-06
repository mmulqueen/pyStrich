Printing barcodes
=================

The most common cause of "my barcode does not scan" is not encoding -- it
is print resolution. pyStrich emits PNG images sized in pixels; you have to
choose a pixel size that, once printed at your printer's DPI, produces a
physical bar (or module) wide enough for your scanner to resolve.

X-dimension
-----------

The *X-dimension* is the width of the narrowest bar (1D) or one module
(2D) in the printed symbol. Most barcode standards specify a minimum and
recommended X-dimension for each application.

For ``bar_width`` (1D) and ``cellsize`` (2D), the relationship is:

.. code-block:: text

   X-dimension (mm) = bar_width (px) * 25.4 / DPI

So at 300 DPI, the default ``bar_width=3`` produces an X-dimension of
roughly 0.25 mm; at 600 DPI, the same default produces 0.13 mm. The
following table summarises typical X-dimension targets:

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

These are guidance values, not specifications -- always confirm against the
relevant standard for your application (GS1 General Specifications for
retail and supply-chain symbols; ISO/IEC 15415 / 15416 for print quality
verification).

Choosing bar_width / cellsize
-----------------------------

Working back from a target X-dimension and printer DPI:

.. code-block:: text

   bar_width (px) = X-dimension (mm) * DPI / 25.4

At 300 DPI, an X-dimension of 0.25 mm requires ``bar_width=3`` (rounded up
from 2.95). At 600 DPI, the same X-dimension requires ``bar_width=6``.

Round *up* to the nearest integer pixel; rounding down may push the
X-dimension below the readable limit.

Quiet zones
-----------

Every symbology in pyStrich requires white space ("quiet zone") around the
symbol so that scanners can locate its boundaries. pyStrich emits a quiet
zone automatically; do not crop into the white margin when compositing the
output into another image.

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

If a printed barcode does not scan reliably, verify in this order:

1. Open the PNG on screen and try to scan it with a phone or handheld
   scanner. If it fails on screen, the encoding (or sizing) is wrong; if
   it succeeds on screen but fails in print, the print process is the
   issue.
2. Check the X-dimension with a ruler or loupe and compare against the
   table above.
3. Check the quiet zone has not been cropped or printed against a coloured
   background.
4. Check print contrast -- low-DPI thermal printers or worn ribbons can
   produce bars that are too grey to be read.

For production deployments printing barcodes at scale, consider using a
print-quality verifier (an instrument that scores symbols against ISO/IEC
15415 / 15416). A passing grade once during integration is worth more than
re-printing a thousand failed labels.
