"""Sphinx configuration for pyStrich documentation."""

import shutil
import sys
from pathlib import Path

import tomllib

# Docs-only helpers (anatomy diagrams) live alongside conf.py.
sys.path.insert(0, str(Path(__file__).parent))

_pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())

project = "pyStrich"
author = "Michael Mulqueen"
copyright = "pyStrich contributors"
release = _pyproject["project"]["version"]
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_sitemap",
    "sphinxarg.ext",
    "sphinxext.opengraph",
]

copybutton_prompt_text = r">>> |\.\.\. |\$ "
copybutton_prompt_is_regexp = True

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "pillow": ("https://pillow.readthedocs.io/en/stable", None),
}

autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "show-inheritance": True,
    "inherited-members": "object, dict, BaseException, tuple",
}
autodoc_type_aliases = {
    "PILImage": "PIL.Image.Image",
}
add_module_names = False

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

templates_path = ["_templates"]

html_baseurl = "https://www.method-b.uk/pyStrich/docs/"
html_theme = "furo"
html_title = "pyStrich — the Python 1D/2D barcode encoder"
html_logo = "static/logo.svg"
html_favicon = "static/favicon.svg"
html_static_path = ["static"]
html_css_files = ["custom.css"]

# NamedTuple field descriptors and methods report __module__ as 'collections'
# (they come from collections.namedtuple's exec'd factory), which would
# otherwise drag a viewcode source page for the stdlib collections module
# into our output.
viewcode_follow_imported_members = False

# sphinx-sitemap: omit the default {lang}{version} URL prefix and skip
# auto-generated pages that aren't useful in search results. lastmod
# is populated from git log; sphinx-sitemap quietly omits it when git
# history is unavailable (e.g. shallow clones, local checkouts without
# the relevant commits).
sitemap_url_scheme = "{link}"
sitemap_show_lastmod = True
sitemap_excludes = [
    "search.html",
    "genindex.html",
    "py-modindex.html",
    "_modules/*",
]

# sphinxext-opengraph: per-page :description: drives <meta name="description">;
# per-page :og:description: drives the social-preview description. Auto-extraction
# is disabled (ogp_description_length=0) so untagged pages get no description
# rather than a comma-mashed dump of headings.
ogp_site_url = html_baseurl
ogp_site_name = "pyStrich"
ogp_type = "website"
ogp_image = f"{html_baseurl}_static/logo-social.png"
ogp_image_alt = "pyStrich — Python 1D/2D barcode encoder"
ogp_enable_meta_description = False
ogp_description_length = 0


def _generate_example_images(app):
    from pystrich.aztec import AztecEncoder
    from pystrich.code39 import Code39Encoder
    from pystrich.code128 import Code128Encoder
    from pystrich.datamatrix import FNC1, DataMatrixData, DataMatrixEncoder
    from pystrich.ean13 import EAN13Encoder
    from pystrich.marks import MarkShape
    from pystrich.pdf417 import PDF417Encoder
    from pystrich.qrcode import QRCodeEncoder

    out = Path(app.srcdir) / "examples"
    out.mkdir(exist_ok=True)

    pystrich_url = DataMatrixData("https://github.com/mmulqueen/pyStrich", encoding="ascii")

    # Text-only assets used by .. literalinclude:: in every builder.
    (out / "qrcode-terminal.txt").write_text(
        QRCodeEncoder("https://github.com/mmulqueen/pyStrich").get_terminal_art(ansi_bg=False),
        encoding="utf-8",
    )
    (out / "datamatrix-terminal.txt").write_text(
        DataMatrixEncoder(pystrich_url).get_terminal_art(ansi_bg=False),
        encoding="utf-8",
    )
    (out / "datamatrix-rausschmeisser-terminal.txt").write_text(
        DataMatrixEncoder(DataMatrixData("Rausschmeißer", auto_encoding=True)).get_terminal_art(
            ansi_bg=False
        ),
        encoding="utf-8",
    )
    (out / "pdf417-terminal.txt").write_text(
        PDF417Encoder("WDBCA45D2HA327260").get_terminal_art(ansi_bg=False),
        encoding="utf-8",
    )
    (out / "aztec-terminal.txt").write_text(
        AztecEncoder("https://github.com/mmulqueen/pyStrich").get_terminal_art(ansi_bg=False),
        encoding="utf-8",
    )

    if app.builder.name != "html":
        # Non-HTML builders parse .. image:: directives but don't render the
        # bytes, so missing example PNGs are a non-issue. Suppress the
        # corresponding warning so we can skip generation here without
        # breaking -W.
        app.config.suppress_warnings.append("image.not_readable")
        return

    label_options = {
        "height": 200,
        "label_border": 10,
        "bottom_border": 10,
        "ttf_fontsize": 24,
    }

    Code39Encoder("64755").save(str(out / "code39-example.png"))
    Code39Encoder("64755").save(str(out / "code39-wide.png"), bar_width=6)
    Code39Encoder("64755", options=label_options).save(str(out / "code39-custom.png"), bar_width=4)
    Code39Encoder("64755").save_svg(str(out / "code39-example.svg"))

    Code128Encoder("WDBCA45D2HA327260").save(str(out / "code128-example.png"))
    Code128Encoder("WDBCA45D2HA327260").save(str(out / "code128-wide.png"), bar_width=6)
    Code128Encoder("WDBCA45D2HA327260", options=label_options).save(
        str(out / "code128-custom.png"), bar_width=4
    )
    Code128Encoder("WDBCA45D2HA327260").save_svg(str(out / "code128-example.svg"))

    DataMatrixEncoder(pystrich_url).save(str(out / "datamatrix-example.png"))
    DataMatrixEncoder(pystrich_url).save_svg(str(out / "datamatrix-example.svg"))
    DataMatrixEncoder(pystrich_url).save_svg(
        str(out / "datamatrix-example-circles.svg"),
        mark_shape=MarkShape.CIRCULAR_CELLS,
    )
    DataMatrixEncoder(pystrich_url).save(str(out / "datamatrix-large.png"), cellsize=10)
    DataMatrixEncoder(DataMatrixData(FNC1, "0105050070007664", encoding="ascii")).save(
        str(out / "datamatrix-gs1.png"), cellsize=8
    )
    DataMatrixEncoder(
        DataMatrixData(FNC1, "0109501234543213", "17261231", "10BF07", encoding="ascii")
    ).save(str(out / "datamatrix-gs1-multi-fixed.png"), cellsize=8)
    DataMatrixEncoder(DataMatrixData(FNC1, "10BF07", FNC1, "2119890519", encoding="ascii")).save(
        str(out / "datamatrix-gs1-multi.png"), cellsize=8
    )
    DataMatrixEncoder(
        DataMatrixData("Ich dachte, Sie wären kräftiger", encoding="iso-8859-1")
    ).save(str(out / "datamatrix-latin1.png"), cellsize=8)
    DataMatrixEncoder(DataMatrixData("€5 親切にしろ 🐻‍❄️", encoding="utf-8")).save(
        str(out / "datamatrix-utf8.png"), cellsize=8
    )

    EAN13Encoder("5050070007664").save(str(out / "ean13-example.png"))
    EAN13Encoder("5050070007664").save(str(out / "ean13-wide.png"), bar_width=6)
    EAN13Encoder("5050070007664", options={"first_digit_y_offset": 0}).save(
        str(out / "ean13-level.png"), bar_width=4
    )
    EAN13Encoder("5050070007664").save_svg(str(out / "ean13-example.svg"))

    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save(str(out / "qrcode-example.png"))
    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg(str(out / "qrcode-example.svg"))
    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg(
        str(out / "qrcode-example-circles.svg"),
        mark_shape=MarkShape.CIRCULAR_CELLS,
    )
    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save(
        str(out / "qrcode-large.png"), cellsize=10
    )

    PDF417Encoder("WDBCA45D2HA327260").save(str(out / "pdf417-example.png"))
    PDF417Encoder("WDBCA45D2HA327260").save_svg(str(out / "pdf417-example.svg"))
    PDF417Encoder("WDBCA45D2HA327260").save(str(out / "pdf417-large.png"), cellsize=10)
    PDF417Encoder("Ich dachte, Sie wären kräftiger").save(
        str(out / "pdf417-latin1.png"), cellsize=4
    )
    PDF417Encoder("€5 親切にしろ 🐻‍❄️").save(str(out / "pdf417-utf8.png"), cellsize=4)

    AztecEncoder("https://github.com/mmulqueen/pyStrich").save(str(out / "aztec-example.png"))
    AztecEncoder("https://github.com/mmulqueen/pyStrich").save_svg(str(out / "aztec-example.svg"))
    AztecEncoder("https://github.com/mmulqueen/pyStrich").save(
        str(out / "aztec-large.png"), cellsize=10
    )
    AztecEncoder("Ich dachte, Sie wären kräftiger").save(str(out / "aztec-latin1.png"), cellsize=8)
    AztecEncoder("€5 親切にしろ 🐻‍❄️").save(str(out / "aztec-utf8.png"), cellsize=8)

    from _anatomy import (
        aztec_anatomy_svg,
        datamatrix_anatomy_svg,
        qrcode_anatomy_svg,
    )

    (out / "aztec-anatomy.svg").write_text(aztec_anatomy_svg(), encoding="utf-8")
    (out / "datamatrix-anatomy.svg").write_text(datamatrix_anatomy_svg(), encoding="utf-8")
    (out / "qrcode-anatomy.svg").write_text(qrcode_anatomy_svg(), encoding="utf-8")

    # Damage-tolerance demos for docs/printing.rst. The matching
    # ``test_*_smudge_tolerance`` tests in each symbology's test module
    # apply the same damage and assert zxing-cpp still decodes.
    from pystrich._simulate_damage import (
        aztec_smudge_demo,
        datamatrix_smudge_demo,
        qrcode_smudge_demo,
    )

    url = "https://github.com/mmulqueen/pyStrich"
    aztec_smudge_demo(url).save(str(out / "aztec-damaged.png"))
    datamatrix_smudge_demo(url).save(str(out / "datamatrix-damaged.png"))
    qrcode_smudge_demo(url).save(str(out / "qrcode-damaged.png"))


def _copy_text_to_html(app, exception):
    """Sit the text-builder output next to its HTML siblings.

    The page.html template adds a "View as plain text" link to <pagename>.txt,
    which only resolves if the text file is alongside the HTML in the served
    output. Avoids html_extra_path = ["_build/text"], which Sphinx warns
    about because the path lives inside the source tree's _build directory.
    """
    if exception is not None or app.builder.name != "html":
        return
    text_dir = Path(app.srcdir) / "_build" / "text"
    if not text_dir.exists():
        return
    for src in text_dir.glob("*.txt"):
        shutil.copy(src, Path(app.outdir) / src.name)


def setup(app):
    app.connect("builder-inited", _generate_example_images)
    app.connect("build-finished", _copy_text_to_html)
