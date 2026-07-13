<img src="https://raw.githubusercontent.com/mmulqueen/pyStrich/main/docs/static/logo.png" alt="pyStrich" width="200">

pyStrich
========
pyStrich is a fast pure-Python module to generate 1D and 2D barcodes in PNG, SVG and other image formats. Currently it
supports:

 * Code 39 (`code39`)
 * Code 128 and GS1-128 (`code128`)
 * EAN-13 (`ean13`)
 * Interleaved 2 of 5 and ITF-14 (`itf`)
 * Data Matrix and GS1 Data Matrix (`datamatrix`)
 * QR Code (`qrcode`)
 * PDF417 (`pdf417`)
 * Aztec Code (`aztec`)

PNG output requires Pillow, installable via the `pyStrich[png]` extra; SVG, EPS, DXF and terminal output do not. pyStrich supports encoding only, not decoding.

Available from PyPI: https://pypi.org/project/pyStrich/

Documentation: https://www.method-b.uk/pyStrich/docs/

<a href="https://github.com/mmulqueen/pyStrich/actions/workflows/python-qa.yml"><img
                alt="Python QA workflow status"
                src="https://github.com/mmulqueen/pyStrich/workflows/Python%20QA/badge.svg"></a>
<a href="https://pypi.org/project/pyStrich/"><img
alt="Newest PyPI version"
src="https://img.shields.io/pypi/v/pyStrich.svg"></a>

Background
----------
pyStrich was originally a fork of [huBarcode](https://github.com/hudora/huBarcode). huBarcode was developed by
[HuDoRa](http://www.hudora.de/en/) from at least 2007, and has not been active since late 2013.
[Method B Ltd](https://www.method-b.uk/) forked huBarcode as pyStrich in 2015 to provide Python 3 support and to continue
development. pyStrich has been substantially enhanced over the years and has gone far beyond a simple port to Python 3.
As of 2026, pyStrich is a modern Python package with full use of typing, linting and a comprehensive test suite.

Thanks to the folks at HuDoRa for the original huBarcode library that pyStrich grew out of.

License
-------
The code is available under the Apache License, Version 2.0.
