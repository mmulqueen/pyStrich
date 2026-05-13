import os
import subprocess
from shutil import which

import pytest


@pytest.fixture
def decode_barcode():
    """Decode a saved barcode image via zxing-cpp.

    Covers every symbology this project generates -- Code 39, Code 128,
    EAN-13, Data Matrix, QR Code and PDF417 -- through one Python binding.
    """
    zxingcpp = pytest.importorskip("zxingcpp")
    PIL_Image = pytest.importorskip("PIL.Image")

    def _read(image_path: "str | os.PathLike[str]") -> str:
        with PIL_Image.open(os.fspath(image_path)) as image:
            results = zxingcpp.read_barcodes(image)
        if not results:
            raise AssertionError(f"zxing-cpp could not decode {image_path}")
        return results[0].text

    return _read


@pytest.fixture
def dmtxread():
    path = which("dmtxread")
    if not path:
        pytest.skip("dmtxread not installed")

    def _read(
        image_path: "str | os.PathLike[str]",
        *,
        gs1: str | None = None,
        encoding: str = "utf-8",
    ) -> str:
        # -C 0 disables error correction; --corrections-max=0 is rejected by dmtxread.
        args = [path, "-C", "0"]
        if gs1 is not None:
            # -G enables GS1 mode and substitutes FNC1 codewords with the given character.
            # dmtxread expects the character as a decimal codepoint, not a literal.
            args += ["-G", str(ord(gs1))]
        args.append(os.fspath(image_path))
        return subprocess.check_output(args).decode(encoding)

    return _read


@pytest.fixture
def svg_to_png():
    path = which("rsvg-convert")
    if not path:
        pytest.skip("librsvg `rsvg-convert` not installed")

    def _convert(
        svg_path: "str | os.PathLike[str]",
        png_path: "str | os.PathLike[str]",
    ) -> None:
        subprocess.check_call(
            [
                path,
                "--background-color=white",
                "--dpi-x=150",
                "--dpi-y=150",
                "--output",
                os.fspath(png_path),
                os.fspath(svg_path),
            ]
        )

    return _convert


@pytest.fixture
def eps_to_png():
    path = which("gs")
    if not path:
        pytest.skip("Ghostscript `gs` not installed")

    def _convert(
        eps_path: "str | os.PathLike[str]",
        png_path: "str | os.PathLike[str]",
    ) -> None:
        subprocess.check_call(
            [
                path,
                "-q",
                "-dSAFER",
                "-dBATCH",
                "-dNOPAUSE",
                "-dEPSCrop",
                "-sDEVICE=png16m",
                "-r150",
                f"-sOutputFile={os.fspath(png_path)}",
                os.fspath(eps_path),
            ]
        )

    return _convert


@pytest.fixture
def dxf_to_svg():
    try:
        import ezdxf
        from ezdxf.addons.drawing import Frontend, RenderContext, config, layout
        from ezdxf.addons.drawing.svg import SVGBackend
    except ImportError:
        pytest.skip("ezdxf not installed")

    def _convert(
        dxf_path: "str | os.PathLike[str]",
        svg_path: "str | os.PathLike[str]",
        *,
        inverse: bool,
        margin_mm: float = 0,
    ) -> None:
        doc = ezdxf.readfile(os.fspath(dxf_path))
        if inverse:
            cfg = config.Configuration(
                color_policy=config.ColorPolicy.WHITE,
                background_policy=config.BackgroundPolicy.BLACK,
            )
        else:
            cfg = config.Configuration(
                color_policy=config.ColorPolicy.BLACK,
                background_policy=config.BackgroundPolicy.WHITE,
            )
        backend = SVGBackend()
        Frontend(RenderContext(doc), backend, config=cfg).draw_layout(doc.modelspace())
        page = layout.Page(0, 0, margins=layout.Margins.all(margin_mm))
        with open(svg_path, "w", encoding="utf-8") as fp:
            fp.write(backend.get_string(page))

    return _convert
