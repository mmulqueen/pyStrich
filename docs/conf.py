"""Sphinx configuration for pyStrich documentation."""
import shutil
import tomllib
from pathlib import Path

_pyproject = tomllib.loads((Path(__file__).parent.parent / "pyproject.toml").read_text())

project = "pyStrich"
author = "Michael Mulqueen"
copyright = "pyStrich contributors"
release = _pyproject["tool"]["poetry"]["version"]
version = release

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.doctest",
    "sphinx.ext.napoleon",
    "sphinx.ext.intersphinx",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
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
}
autodoc_type_aliases = {
    "PILImage": "PIL.Image.Image",
}
add_module_names = False

exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

templates_path = ["_templates"]

html_theme = "furo"
html_title = f"pyStrich {release}"
html_logo = "logo.svg"
html_favicon = "favicon.svg"


def _generate_example_images(app):
    if app.builder.name != "html":
        # Non-HTML builders parse .. image:: directives but don't render the
        # bytes, so missing example PNGs are a non-issue. Suppress the
        # corresponding warning so we can skip generation here without
        # breaking -W.
        app.config.suppress_warnings.append("image.not_readable")
        return

    from pystrich.code39 import Code39Encoder
    from pystrich.code128 import Code128Encoder
    from pystrich.datamatrix import DataMatrixData, DataMatrixEncoder, FNC1
    from pystrich.ean13 import EAN13Encoder
    from pystrich.marks import MarkShape
    from pystrich.qrcode import QRCodeEncoder

    out = Path(app.srcdir) / "examples"
    out.mkdir(exist_ok=True)

    label_options = {
        "height": 200,
        "label_border": 10,
        "bottom_border": 10,
        "ttf_fontsize": 24,
    }

    pystrich_url = DataMatrixData(
        "https://github.com/mmulqueen/pyStrich", encoding="ascii"
    )

    Code39Encoder("PART-1234").save(str(out / "code39-example.png"))
    Code39Encoder("PART-1234").save(str(out / "code39-wide.png"), bar_width=6)
    Code39Encoder("PART-1234", options=label_options).save(
        str(out / "code39-custom.png"), bar_width=4
    )

    Code128Encoder("PyStrich-2026").save(str(out / "code128-example.png"))
    Code128Encoder("PyStrich-2026").save(str(out / "code128-wide.png"), bar_width=6)
    Code128Encoder("PyStrich-2026", options=label_options).save(
        str(out / "code128-custom.png"), bar_width=4
    )

    DataMatrixEncoder(pystrich_url).save(str(out / "datamatrix-example.png"))
    DataMatrixEncoder(pystrich_url).save_svg(str(out / "datamatrix-example.svg"))
    DataMatrixEncoder(pystrich_url).save_svg(
        str(out / "datamatrix-example-circles.svg"),
        mark_shape=MarkShape.CIRCULAR_CELLS,
    )
    DataMatrixEncoder(pystrich_url).save(
        str(out / "datamatrix-large.png"), cellsize=10
    )
    DataMatrixEncoder(
        DataMatrixData(FNC1, "0105050070007664", encoding="ascii")
    ).save(str(out / "datamatrix-gs1.png"), cellsize=8)
    DataMatrixEncoder(
        DataMatrixData(
            FNC1, "0109501234543213", "17261231", "10ABC123", encoding="ascii"
        )
    ).save(str(out / "datamatrix-gs1-multi-fixed.png"), cellsize=8)
    DataMatrixEncoder(
        DataMatrixData(FNC1, "10ABC123", FNC1, "21SERIAL01", encoding="ascii")
    ).save(str(out / "datamatrix-gs1-multi.png"), cellsize=8)
    DataMatrixEncoder(DataMatrixData("café", encoding="iso-8859-1")).save(
        str(out / "datamatrix-latin1.png"), cellsize=8
    )
    DataMatrixEncoder(DataMatrixData("€5 親切にしろ 🙂", encoding="utf-8")).save(
        str(out / "datamatrix-utf8.png"), cellsize=8
    )

    EAN13Encoder("5050070007664").save(str(out / "ean13-example.png"))
    EAN13Encoder("5050070007664").save(str(out / "ean13-wide.png"), bar_width=6)

    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save(
        str(out / "qrcode-example.png")
    )
    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg(
        str(out / "qrcode-example.svg")
    )
    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save_svg(
        str(out / "qrcode-example-circles.svg"),
        mark_shape=MarkShape.CIRCULAR_CELLS,
    )
    QRCodeEncoder("https://github.com/mmulqueen/pyStrich").save(
        str(out / "qrcode-large.png"), cellsize=10
    )


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
