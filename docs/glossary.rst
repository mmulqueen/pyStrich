Glossary
========

Definitions for the barcode terms used throughout the pyStrich
documentation.

.. glossary::

   1D barcode
      A linear symbology that encodes data as parallel bars and spaces
      of varying widths, read along a single axis. EAN-13, Code 128
      and Code 39 are 1D barcodes.

   2D barcode
      A matrix or stacked symbology that encodes data in two
      dimensions, giving much higher data density than a 1D barcode.
      QR Code, Data Matrix, Aztec Code and PDF417 are 2D barcodes.

   codeword
      A fixed-size unit of encoded data produced after the payload has
      been mapped from text or bytes into the format's internal
      representation. Codewords are what Reed-Solomon error correction
      operates on, and the total codeword count fixes the symbol's
      data capacity.

   direct part marking
      Engraving, dot-peening, chemical etching or laser marking a barcode
      directly onto a physical part, in place of a printed label.
      Used where labels would not be suitable.

   DPI
      Dots per inch. The resolution at which a printer lays down ink
      or a scanner samples an image. DPI sets the lower bound on how
      small a module can be reproduced reliably.

   DXF
      Drawing Exchange Format. A CAD-oriented vector file format
      originally from AutoCAD, useful for handing barcode geometry to
      engraving or laser-cutting workflows.

   ECI
      Extended Channel Interpretation. A standardised escape mechanism
      (defined by AIM) that lets a 2D symbol declare which character
      encoding -- UTF-8, ISO-8859-1 and so on -- the following data
      uses, so decoders return text in the right charset.

   EPS
      Encapsulated PostScript. A vector format for embedding a
      PostScript drawing inside another document, long-used in print
      production and still accepted by most prepress and imposition
      tools.

   error correction level
      The amount of redundancy a symbol carries, expressed differently
      per format: QR Code uses L / M / Q / H, PDF417 uses levels 0-8,
      Aztec Code uses a percentage. Higher levels recover from more
      damage at the cost of holding less payload.

   finder pattern
      A distinctive marker at fixed positions inside a 2D symbol so
      scanners can locate the code and determine its orientation. Each
      symbology uses its own design: QR Code's three corner squares,
      Data Matrix's solid-L, Aztec Code's central bullseye.

   FNC1
      Function Code 1. A non-data control character that 2D symbols
      use to signal that the payload follows the GS1 Application
      Identifier format. It is always emitted at the start of the
      data and may also separate variable-length identifiers within
      the payload.

   GS1
      A global standards body that maintains identifiers such as the
      GTIN and the Application Identifier format used to encode
      structured product data in barcodes. "GS1 mode" in a 2D symbol
      uses FNC1 to mark the payload as following these rules.

   GTIN
      Global Trade Item Number. The GS1 identifier used to uniquely
      identify a retail product, structured as a 14-digit number with
      a check digit. EAN-13 barcodes carry GTINs directly; 2D symbols
      can carry them inside GS1 Application Identifier payloads.

   module
      The smallest individual element of a barcode: one dark or light
      unit. In 2D symbologies it is a square cell; in 1D symbologies
      it is the narrowest bar or space. Symbol sizes and quiet zones
      are both measured in modules.

   occlusion
      Partial covering of a symbol by another object -- a finger, a
      sticker, a smudge, a tear. Error-correction codewords let a
      decoder recover the payload as long as the occluded area stays
      within tolerance.

   projective distortion
      The geometric warping that appears when a flat symbol is
      photographed from an angle: parallel edges no longer stay
      parallel and modules vary in size across the image. Decoders
      correct for it using known reference points such as alignment
      patterns.

   quiet zone
      The blank margin around a barcode that lets a scanner separate
      the symbol from surrounding artwork. Most specifications mandate
      a minimum quiet zone in modules; without it, decoders may fail
      to lock on or may misread the outer edges.

   Reed-Solomon
      A widely-used error-correction algorithm that adds redundant
      codewords to a message so the original data can be recovered
      even if some codewords are damaged or unreadable. Used by Data
      Matrix, QR Code, Aztec Code, PDF417 and many other formats.

   symbology
      A specification defining how data is encoded as a barcode: the
      character sets it accepts, how codewords are laid out, the
      error correction it applies, and how a scanner should read it.
      Data Matrix and QR Code are symbologies.

   timing pattern
      A row or column of alternating dark and light cells inside a 2D
      symbol that lets a scanner count modules across the symbol and
      recover from grid skew. Data Matrix has one along the top and
      right of each region; QR Code has one row and one column
      between the corner finders.

   X-dimension
      The width of the narrowest bar or module in a printed symbol,
      traditionally measured in mils or millimetres. The X-dimension
      sets how small the symbol can be printed and how far away a
      scanner can read it from.
