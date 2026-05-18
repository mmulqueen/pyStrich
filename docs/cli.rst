:og:description: Generate barcodes from the command line with the pyStrich CLI.

.. meta::
   :description: Generate barcodes from the command line with the pyStrich CLI.

Command-line interface
======================

Installing pyStrich exposes a ``pystrich`` console script with a subcommand
per format and PNG / SVG / EPS / ASCII / terminal / DXF output.

.. code-block:: console

   $ pystrich qrcode --text "https://en.wikipedia.org/wiki/Jasper,_Missouri" -o jasper.svg
   $ pystrich code128 --text "Dalton" -o dalton.png
   $ pystrich ean13 --text "5050070007664" -o ean13.png
   $ echo "DLB 573" | pystrich code39 -o code39.png
   $ pystrich datamatrix --text "Rausschmeißer"   # terminal preview

The last example produces:

.. literalinclude:: examples/datamatrix-rausschmeisser-terminal.txt
   :language: text
   :class: terminal-art

Reference
---------

.. argparse::
   :module: pystrich.cli
   :func: _build_parser
   :prog: pystrich

Format auto-detection
---------------------

The output format is auto-detected from the ``-o`` filename
(``.png``, ``.svg``, ``.eps``, ``.dxf``); without ``-o`` it defaults to
``terminal`` for 2D formats when stdout is a TTY. Piped or redirected
output without an explicit ``-t`` is rejected, to avoid dumping binary
into the next tool by accident.

GS1 Data Matrix from the shell
------------------------------

GS1 Data Matrix uses ASCII with ``FNC1`` markers separating application
identifiers and their values. ``--substitute-with-fnc1`` lets you build
that input from a shell-friendly string:

.. code-block:: console

   $ pystrich datamatrix \
       --text "|0105050070007664" \
       --substitute-with-fnc1 "|" \
       -o gs1.png

See :doc:`datamatrix` for the full encoding discussion.

Limitations
-----------

The CLI doesn't expose every Python-API knob. Reach for the Python API for
1D label fonts, custom borders, EAN-13's ``first_digit_y_offset``, or the
deprecated DataMatrix ``compat`` encoding.

API
---

.. automodule:: pystrich.cli
   :members: main
