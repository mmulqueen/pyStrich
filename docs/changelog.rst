Changelog
=========

0.12 — unreleased
-----------------

- SVG output for QR Code and Data Matrix via new ``save_svg`` /
  ``get_svg`` methods on :class:`~pystrich.qrcode.QRCodeEncoder` and
  :class:`~pystrich.datamatrix.DataMatrixEncoder`.

0.11 — 2026-05-07
-----------------

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

0.10 — 2025-09-24
-----------------

- Make the DataMatrix quiet zone configurable
  (`issue #17 <https://github.com/mmulqueen/pyStrich/issues/17>`_).
- Add Python 3.13 to the supported and tested versions (Python 3.8 to 3.13).

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

0.8 — 2016-07-06
----------------

- Fix `issue #5 <https://github.com/mmulqueen/pyStrich/issues/5>`_.

0.7 — 2015-07-26
----------------

- Raise the Data Matrix payload limit from 44 characters to 174 characters
  (or 348 digits) by supporting larger symbol sizes
  (`issue #2 <https://github.com/mmulqueen/pyStrich/issues/2>`_).

0.6 — 2015-07-21
----------------

- Released as "This time with fonts and data".
- Remove test relying on ``dmtxwrite`` due to issues in the previous commit.

0.4 — 2015-07-19
----------------

- Released as "First working version on PyPI".
- Fix ``setup.py`` so the PyPI package is no longer broken.
