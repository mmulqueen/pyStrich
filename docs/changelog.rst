Changelog
=========

.. _v0-16:

0.16 — unreleased
-----------------

- New :class:`~pystrich.itf.ITFEncoder` for plain Interleaved 2 of 5 and
  :class:`~pystrich.itf.ITF14Encoder` for ITF-14 (GTIN-14), with
  PNG / SVG / EPS output and a ``pystrich itf14`` CLI subcommand. See :doc:`itf`.
- pyStrich now imports Pillow only when producing PNGs, and PNG support is
  offered through a ``pyStrich[png]`` extra; SVG, EPS, DXF and terminal output
  no longer need it at import time. Pillow remains installed by default in this version.
- All encoders: render methods gain ``dark_hex`` and ``light_hex`` keywords that
  recolour the modules or bars and the background consistently across PNG, SVG and EPS.
  Can also be used in the CLI ``--dark-hex`` / ``--light-hex``.

.. _v0-15:

0.15 — 2026-06-26
-----------------

- All encoders gain ``svg_dataurl`` and ``png_dataurl`` methods that
  return the symbol as a ``data:`` URL string.
- QR Code: the encoder now mixes Numeric, Alphanumeric and Byte segments
  per input to shrink symbols carrying digits or uppercase runs.
- QR Code: ``QRCodeData(encoding="shift_jis")`` now triggers Kanji-mode
  segmentation under ECI 20, packing JIS X 0208 characters into 13 bits each.
- QR Code: new :meth:`~pystrich.qrcode.QRCodeData.wifi_network` classmethod
  helps build WiFi network joining QR codes.
- Data Matrix: the encoder now mixes ASCII, C40, Text and X12 segments
  per input to shrink symbols carrying uppercase, lowercase or
  CR-delimited X12 records. Payloads built with
  :data:`~pystrich.datamatrix.FNC1` stay in single-mode ASCII as the
  GS1 Data Matrix spec requires.
- Data Matrix: new ``force_byte_mode`` keyword on
  :class:`~pystrich.datamatrix.DataMatrixEncoder` pins the encoder to the
  byte-by-byte path, skipping the C40/Text/X12 optimiser.
- Data Matrix: ``iso-8859-1`` payloads now emit an explicit ECI 3
  designator so heuristic decoders don't misinterpret short Upper-Shift
  sequences as another charset.
- Code 128: new :class:`~pystrich.code128.Code128Data` accepts typed
  :data:`~pystrich.code128.FNC1`, :data:`~pystrich.code128.FNC2` and
  :data:`~pystrich.code128.FNC3` markers (GS1-128 etc.), plus
  ``encoding="iso-8859-1"`` for Latin-1 input.
- GS1: new :class:`~pystrich.gs1.GS1Fixed` /
  :class:`~pystrich.gs1.GS1Variable` field wrappers consumed by
  :meth:`Code128Data.gs1 <pystrich.code128.Code128Data.gs1>` and
  :meth:`DataMatrixData.gs1 <pystrich.datamatrix.DataMatrixData.gs1>` to
  build GS1-128 and GS1 Data Matrix payloads without managing FNC1
  separator placement by hand.

.. _v0-14:

0.14 — 2026-05-18
-----------------

- New :class:`~pystrich.aztec.AztecEncoder` for Aztec Code (compact and
  full-range), with PNG / SVG / EPS / DXF / terminal output and a
  ``pystrich aztec`` CLI subcommand. See :doc:`aztec`.
- New :class:`~pystrich.pdf417.PDF417Encoder` for the PDF417 stacked 2D
  symbology, with PNG / SVG / EPS / DXF / terminal output and a
  ``pystrich pdf417`` CLI subcommand. See :doc:`pdf417`.

.. _v0-13:

0.13 — 2026-05-14
-----------------

- QR Code: accepts any Unicode string and picks the best encoding
  automatically (ASCII, Latin-1 or UTF-8). New
  :class:`~pystrich.qrcode.QRCodeData` exposes explicit charset control
  when you need it.
- QR Code: internal refactor to improve the encoder's spec compliance
  and to share Reed-Solomon and encoding-selection code with
  the Data Matrix module.
- Data Matrix: ``TextEncoder.encode()`` returns ``list[int]`` instead of
  a ``str`` of ``chr()``-packed bytes.
- Data Matrix: support all 24 ECC200 square symbol sizes up to 144x144
  (1558 data codewords), with interleaved Reed-Solomon blocks for the
  larger symbols. Previously capped at 48x48 (174 codewords).
- Data Matrix: fix the bottom-right corner-module pattern for sizes
  where it was previously emitted as four zero cells, and fix
  pad-codeword randomisation to produce the correct value at the
  position-28 boundary.
- Code 128: unencodable characters now raise
  :class:`~pystrich.exceptions.PyStrichInvalidInput` instead of being
  logged and failing later with ``KeyError``.
- Code 39: non-ASCII input under ``full_ascii=True`` now raises
  :class:`~pystrich.exceptions.PyStrichInvalidInput` instead of an
  unwrapped ``UnicodeEncodeError``.
- Typing: the entire ``pystrich`` package is now checked with mypy;
  the remaining per-module ``ignore_errors`` overrides have been removed.

.. _v0-12:

0.12 — 2026-05-09
-----------------

- New ``pystrich`` console script with a subcommand per format and PNG /
  SVG / EPS / ASCII / terminal / DXF output. See :doc:`cli`.
- Data Matrix: :class:`~pystrich.datamatrix.DataMatrixData` now expects
  either an ``encoding=`` argument or ``auto_encoding=True`` to be set
  on construction. The new ``auto_encoding=True`` flag picks the
  narrowest encoding.
- SVG output for QR Code and Data Matrix via new ``save_svg`` /
  ``get_svg`` methods on :class:`~pystrich.qrcode.QRCodeEncoder` and
  :class:`~pystrich.datamatrix.DataMatrixEncoder`.
- SVG output for the 1D barcodes via the same ``save_svg`` / ``get_svg``
  methods on :class:`~pystrich.code39.Code39Encoder`,
  :class:`~pystrich.code128.Code128Encoder` and
  :class:`~pystrich.ean13.EAN13Encoder`.
- EPS output for QR Code and Data Matrix via new ``save_eps`` /
  ``get_eps`` methods on the same classes.
- EPS output for the 1D barcodes via the same ``save_eps`` / ``get_eps``
  methods on :class:`~pystrich.code39.Code39Encoder`,
  :class:`~pystrich.code128.Code128Encoder` and
  :class:`~pystrich.ean13.EAN13Encoder`.
- The human-readable labels for 1D barcodes are rendered with bundled Courier Prime glyph outlines (SIL Open
  Font License).
- DXF: ``get_dxf()`` on
  :class:`~pystrich.qrcode.QRCodeEncoder` and
  :class:`~pystrich.datamatrix.DataMatrixEncoder` now writes the correct
  ``$INSUNITS`` value for ``"in"``, ``"ft"``, ``"mi"``, ``"cm"`` and
  ``"m"`` (previously any value other than ``"mm"`` was silently treated
  as unspecified); you should now pass ``units=None`` if unspecified is
  desired.
- All vector outputs accept a ``mark_shape`` keyword argument
  (:class:`~pystrich.marks.MarkShape`) selecting how matched cells are
  grouped and drawn: horizontal runs (the SVG / EPS default), one
  square mark per cell (the DXF default), or one filled circle per
  cell.
- Tests: round-trip DXF coverage for QR Code and Data Matrix -- the
  rendered DXF is read with ``ezdxf``, rasterised, and decoded back to
  the original string.
- New ``get_terminal_art`` method on :class:`~pystrich.qrcode.QRCodeEncoder`
  and :class:`~pystrich.datamatrix.DataMatrixEncoder`, rendering the
  symbol with Unicode half-block characters so it scans on screen. ANSI
  background/foreground codes are applied by default for readability on
  any terminal theme; pass ``ansi_bg=False`` for plain output.

.. _v0-11:

0.11 — 2026-05-07
-----------------

.. note::

   Erratum: the ``get_dxf()`` docstrings on
   :class:`~pystrich.qrcode.QRCodeEncoder` and
   :class:`~pystrich.datamatrix.DataMatrixEncoder` stated that
   ``inverse=True`` (the default) draws dark modules as filled cells.
   In fact ``inverse=True`` draws the *light* modules; ``inverse=False``
   draws the dark ones. Behaviour is unchanged -- only the description
   was wrong. Corrected in 0.12.

- Documentation: full Sphinx-built docs are now published at
  https://www.method-b.uk/pyStrich/docs/, covering each symbology, recipes
  and printing guidance, exception hierarchy and a reference index.
- DataMatrix: add explicit ``"iso-8859-1"`` and ``"utf-8"`` encodings for
  non-ASCII payloads, selectable via
  :class:`~pystrich.datamatrix.DataMatrixData`.
- DataMatrix: saner handling of non-ASCII input under the legacy
  ``"compat"`` encoding, with deprecation in favour of explicit encodings.
- DataMatrix: proper FNC1 support via the
  :data:`~pystrich.datamatrix.FNC1` marker constant. The long-accepted
  ``chr(231)`` workaround for GS1 still works behind a
  :class:`~pystrich.exceptions.Fnc1WorkaroundCompatWarning` (see
  `issue #13 <https://github.com/mmulqueen/pyStrich/issues/13>`_).
- QR Code: fix `issue #8
  <https://github.com/mmulqueen/pyStrich/issues/8>`_; certain valid
  strings could not generate a QR code.
- EAN-13 quiet zone is now 11 modules left, 7 modules right (per the GS1
  General Specifications); previously 9 modules each side, which was below
  spec on the left.
- EAN-13: the leading digit's vertical position is now
  configurable via an ``options`` dict
  (``first_digit_y_offset``); pass ``0`` for a level baseline across all
  three digit groups (`issue #18
  <https://github.com/mmulqueen/pyStrich/issues/18>`_). The default
  preserves the classic look where the first digit is slightly higher.
- Errors: unified exception hierarchy. All pyStrich-raised errors now
  inherit from :class:`~pystrich.exceptions.PyStrichError`.
- Public ``get_pilimage`` method on every encoder, returning a
  :class:`PIL.Image.Image` directly.
- Typing: encoders and renderers now have type hints and are checked with mypy.
- Tests: refactored test suite to make better use of pytest, and extended
  encode/decode round-trip test coverage to Code 39, Code 128, EAN-13 and
  QR Code (previously DataMatrix only).
- Confirmed compatibility with newer Pillow versions and Python 3.13.
- Drop support for Python 3.8 and 3.9. Supported versions are now Python
  3.10 to 3.14.

.. _v0-10:

0.10 — 2025-09-24
-----------------

- Make the DataMatrix quiet zone configurable
  (`issue #17 <https://github.com/mmulqueen/pyStrich/issues/17>`_).
- Add Python 3.13 to the supported and tested versions (Python 3.8 to 3.13).

.. _v0-9:

0.9 — 2024-10-02
----------------

- Released as "Modernise".
- Add DXF rendering for 2D barcodes (Data Matrix and QR Code), contributed
  by Mike Jones (`PR #7 <https://github.com/mmulqueen/pyStrich/pull/7>`_).
- Pillow >9.5 compatibility: replace deprecated ``ImageFont.getsize`` with
  ``ImageFont.getlength``.
- Drop the ``distutils`` dependency so pyStrich installs on Python 3.12+.
- Switch the build system to Poetry; add a GitHub Action that builds and
  publishes releases.
- Add a CI GitHub Action that runs the test suite with ``dmtx-utils``
  available.
- First automated test for Code 39: output comparison plus known-good
  examples verified with ``zbarimg``.
- Supported and tested on Python 3.8 to 3.12.

.. _v0-8:

0.8 — 2016-07-06
----------------

- Fix `issue #5 <https://github.com/mmulqueen/pyStrich/issues/5>`_.

.. _v0-7:

0.7 — 2015-07-26
----------------

- Raise the Data Matrix payload limit from 44 characters to 174 characters
  (or 348 digits) by supporting larger symbol sizes
  (`issue #2 <https://github.com/mmulqueen/pyStrich/issues/2>`_).

.. _v0-6:

0.6 — 2015-07-21
----------------

- Released as "This time with fonts and data".
- Remove test relying on ``dmtxwrite`` due to issues in the previous commit.

.. _v0-4:

0.4 — 2015-07-19
----------------

- Released as "First working version on PyPI".
- Fix ``setup.py`` so the PyPI package is no longer broken.
