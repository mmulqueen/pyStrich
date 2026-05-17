"""Command-line interface for pyStrich.

Run ``pystrich --help`` for usage. Each subcommand corresponds to a barcode
format and uses the matching ``Encoder`` class.
"""

from __future__ import annotations

import abc
import argparse
import importlib.metadata
import os
import sys
from typing import Any, ClassVar, Literal, get_args

from pystrich.aztec import AZTEC_DEFAULT_QUIET_ZONE, AztecEncoder
from pystrich.code39 import Code39Encoder
from pystrich.code128 import Code128Encoder
from pystrich.datamatrix import (
    DATAMATRIX_DEFAULT_QUIET_ZONE,
    FNC1,
    DataMatrixCodeword,
    DataMatrixData,
    DataMatrixEncoder,
)
from pystrich.dxf import DxfUnit
from pystrich.ean13 import EAN13Encoder, EAN13RenderOptions
from pystrich.exceptions import PyStrichInvalidInput, PyStrichInvalidOption
from pystrich.marks import MarkShape
from pystrich.pdf417 import (
    DEFAULT_ROW_HEIGHT,
    PDF417_DEFAULT_QUIET_ZONE,
    PDF417Encoder,
)
from pystrich.qrcode import QRCodeEncoder
from pystrich.types import BarcodeRenderOptions

OutputType = Literal["png", "svg", "eps", "ascii", "terminal", "dxf"]

_MARK_SHAPE_BY_NAME: dict[str, MarkShape] = {
    "square": MarkShape.SQUARE_CELLS,
    "circular": MarkShape.CIRCULAR_CELLS,
    "horizontal-runs": MarkShape.HORIZONTAL_RUNS,
}

_OUTPUT_BY_EXTENSION: dict[str, OutputType] = {
    ".png": "png",
    ".svg": "svg",
    ".eps": "eps",
    ".dxf": "dxf",
}

_DXF_UNIT_CHOICES = (*get_args(DxfUnit), "unspecified")


class Format(abc.ABC):
    """Abstract barcode format. Leaf subclasses are registered in FORMATS."""

    name: ClassVar[str]
    help: ClassVar[str]
    text_help: ClassVar[str] = "text to encode"
    available_outputs: ClassVar[tuple[OutputType, ...]] = ("png",)

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        sp.add_argument("--text", help=f"{self.text_help} (default: read from stdin)")
        sp.add_argument(
            "-o",
            "--output",
            default=None,
            help="output path; '-' or omitted writes to stdout",
        )
        sp.add_argument(
            "-t",
            "--type",
            dest="output_type",
            choices=("auto", *self.available_outputs),
            default="auto",
            help="output format; 'auto' resolves from -o filename or output context",
        )

    @abc.abstractmethod
    def encoder(self, args: argparse.Namespace) -> Any: ...

    def render(self, args: argparse.Namespace) -> bytes:
        result = getattr(self, f"render_{args.output_type}")(args)
        return result if isinstance(result, bytes) else result.encode("utf-8")


class OneDFormat(Format):
    available_outputs = ("png", "svg", "eps")

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--bar-width",
            type=int,
            default=3,
            help="width of the narrowest bar (default: 3)",
        )
        sp.add_argument(
            "--height",
            type=int,
            default=None,
            help="image height in pixels",
        )

    def render_png(self, args: argparse.Namespace) -> bytes:
        return self.encoder(args).get_imagedata(args.bar_width)

    def render_svg(self, args: argparse.Namespace) -> str:
        return self.encoder(args).get_svg(args.bar_width)

    def render_eps(self, args: argparse.Namespace) -> str:
        return self.encoder(args).get_eps(args.bar_width)


class TwoDFormat(Format):
    available_outputs = ("png", "svg", "eps", "ascii", "terminal", "dxf")

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--cell-size",
            type=float,
            default=None,
            help="side length of one module (default: 5 for raster/SVG/EPS, 1.0 for DXF)",
        )
        sp.add_argument(
            "--inverse",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="invert (light cells filled instead of dark); applies to svg/eps/dxf",
        )
        sp.add_argument(
            "--mark-shape",
            choices=tuple(_MARK_SHAPE_BY_NAME),
            default=None,
            help="how matched cells are drawn in vector output",
        )
        sp.add_argument(
            "--dxf-units",
            choices=_DXF_UNIT_CHOICES,
            default=None,
            help="DXF units (default: mm); 'unspecified' writes $INSUNITS=0",
        )

    @staticmethod
    def _reject_flags(args: argparse.Namespace, output_type: OutputType, *names: str) -> None:
        bad = [_FLAG_LABELS[n] for n in names if getattr(args, n) is not None]
        if bad:
            raise PyStrichInvalidOption(
                f"{', '.join(bad)} not supported for output type {output_type!r}"
            )

    @staticmethod
    def _raster_cell_size(args: argparse.Namespace) -> int:
        if args.cell_size is None:
            return 5
        if args.cell_size <= 0:
            raise PyStrichInvalidOption(f"--cell-size must be positive, got {args.cell_size}")
        return round(args.cell_size)

    @staticmethod
    def _dxf_cell_size(args: argparse.Namespace) -> float:
        if args.cell_size is None:
            return 1.0
        if args.cell_size <= 0:
            raise PyStrichInvalidOption(f"--cell-size must be positive, got {args.cell_size}")
        return float(args.cell_size)

    @staticmethod
    def _vector_kwargs(args: argparse.Namespace) -> dict[str, Any]:
        kwargs: dict[str, Any] = {}
        if args.inverse is not None:
            kwargs["inverse"] = args.inverse
        if args.mark_shape is not None:
            kwargs["mark_shape"] = _MARK_SHAPE_BY_NAME[args.mark_shape]
        return kwargs

    def render_png(self, args: argparse.Namespace) -> bytes:
        self._reject_flags(args, "png", "inverse", "mark_shape", "dxf_units")
        return self.encoder(args).get_imagedata(self._raster_cell_size(args))

    def render_svg(self, args: argparse.Namespace) -> str:
        self._reject_flags(args, "svg", "dxf_units")
        return self.encoder(args).get_svg(self._raster_cell_size(args), **self._vector_kwargs(args))

    def render_eps(self, args: argparse.Namespace) -> str:
        self._reject_flags(args, "eps", "dxf_units")
        return self.encoder(args).get_eps(self._raster_cell_size(args), **self._vector_kwargs(args))

    def render_ascii(self, args: argparse.Namespace) -> str:
        self._reject_flags(args, "ascii", "inverse", "mark_shape", "dxf_units")
        return self.encoder(args).get_ascii() + "\n"

    def render_terminal(self, args: argparse.Namespace) -> str:
        self._reject_flags(args, "terminal", "inverse", "mark_shape", "dxf_units")
        return self.encoder(args).get_terminal_art(ansi_bg=args.is_tty) + "\n"

    def render_dxf(self, args: argparse.Namespace) -> str:
        units: DxfUnit | None
        if args.dxf_units is None or args.dxf_units == "mm":
            units = "mm"
        elif args.dxf_units == "unspecified":
            units = None
        else:
            units = args.dxf_units
        return self.encoder(args).get_dxf(
            cellsize=self._dxf_cell_size(args), units=units, **self._vector_kwargs(args)
        )


_FLAG_LABELS = {
    "inverse": "--inverse",
    "mark_shape": "--mark-shape",
    "dxf_units": "--dxf-units",
}


class Code39(OneDFormat):
    name = "code39"
    help = "Code 39 (1D)"

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--full-ascii",
            action="store_true",
            help="enable full-ASCII Code 39 encoding",
        )
        sp.add_argument(
            "--show-label",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="render the human-readable label below the bars",
        )

    def encoder(self, args: argparse.Namespace) -> Code39Encoder:
        opts: BarcodeRenderOptions = {}
        if args.height is not None:
            opts["height"] = args.height
        if args.show_label is not None:
            opts["show_label"] = args.show_label
        return Code39Encoder(args.text, full_ascii=args.full_ascii, options=opts or None)


class Code128(OneDFormat):
    name = "code128"
    help = "Code 128 (1D)"

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--show-label",
            action=argparse.BooleanOptionalAction,
            default=None,
            help="render the human-readable label below the bars",
        )

    def encoder(self, args: argparse.Namespace) -> Code128Encoder:
        opts: BarcodeRenderOptions = {}
        if args.height is not None:
            opts["height"] = args.height
        if args.show_label is not None:
            opts["show_label"] = args.show_label
        return Code128Encoder(args.text, options=opts or None)


class EAN13(OneDFormat):
    name = "ean13"
    help = "EAN-13 (1D, 12 or 13 digits)"
    text_help = "12 or 13 digits"

    def encoder(self, args: argparse.Namespace) -> EAN13Encoder:
        opts: EAN13RenderOptions = {}
        if args.height is not None:
            opts["height"] = args.height
        return EAN13Encoder(args.text, options=opts or None)


class DataMatrix(TwoDFormat):
    name = "datamatrix"
    help = "Data Matrix (2D)"

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--quiet-zone",
            type=int,
            default=DATAMATRIX_DEFAULT_QUIET_ZONE,
            help=f"quiet-zone width in cells (default: {DATAMATRIX_DEFAULT_QUIET_ZONE})",
        )
        sp.add_argument(
            "--encoding",
            choices=("auto", "ascii", "iso-8859-1", "utf-8"),
            default="auto",
            help="DataMatrix charset (default: auto picks the narrowest that fits)",
        )
        sp.add_argument(
            "--substitute-with-fnc1",
            metavar="CHAR",
            default=None,
            help="replace each occurrence of CHAR in --text with an FNC1 codeword",
        )

    def encoder(self, args: argparse.Namespace) -> DataMatrixEncoder:
        segments = _datamatrix_segments(args.text, args.substitute_with_fnc1)
        if args.encoding == "auto":
            data = DataMatrixData(*segments, auto_encoding=True)
        else:
            data = DataMatrixData(*segments, encoding=args.encoding)
        return DataMatrixEncoder(data, quiet_zone=args.quiet_zone)


def _datamatrix_segments(
    text: str, substitute_with_fnc1: str | None
) -> list[str | DataMatrixCodeword]:
    if substitute_with_fnc1 is None:
        return [text]
    if len(substitute_with_fnc1) != 1:
        raise PyStrichInvalidOption(
            f"--substitute-with-fnc1 must be exactly one character, got {substitute_with_fnc1!r}"
        )
    segments: list[str | DataMatrixCodeword] = []
    for i, chunk in enumerate(text.split(substitute_with_fnc1)):
        if i > 0:
            segments.append(FNC1)
        if chunk:
            segments.append(chunk)
    return segments


class QRCode(TwoDFormat):
    name = "qrcode"
    help = "QR Code (2D)"

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--ecl",
            choices=("L", "M", "Q", "H"),
            help="error-correction level (default: M)",
        )

    def encoder(self, args: argparse.Namespace) -> QRCodeEncoder:
        return QRCodeEncoder(args.text, ecl=args.ecl)


class PDF417(TwoDFormat):
    name = "pdf417"
    help = "PDF417 (stacked 2D)"

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--ecl",
            type=int,
            choices=range(9),
            help="error-correction level 0-8 (default: chosen from data length)",
        )
        sp.add_argument(
            "--columns",
            type=int,
            choices=range(1, 31),
            metavar="N",
            help="data columns 1-30 (default: near-square layout)",
        )
        sp.add_argument(
            "--row-height",
            type=int,
            default=DEFAULT_ROW_HEIGHT,
            help=f"module-rows per codeword row (default: {DEFAULT_ROW_HEIGHT})",
        )
        sp.add_argument(
            "--quiet-zone",
            type=int,
            default=PDF417_DEFAULT_QUIET_ZONE,
            help=f"quiet-zone width in modules (default: {PDF417_DEFAULT_QUIET_ZONE})",
        )

    def encoder(self, args: argparse.Namespace) -> PDF417Encoder:
        return PDF417Encoder(
            args.text,
            ecl=args.ecl,
            columns=args.columns,
            quiet_zone=args.quiet_zone,
            row_height=args.row_height,
        )


class Aztec(TwoDFormat):
    name = "aztec"
    help = "Aztec Code (2D)"

    def add_args(self, sp: argparse.ArgumentParser) -> None:
        super().add_args(sp)
        sp.add_argument(
            "--ecc",
            type=int,
            metavar="PCT",
            default=23,
            help="error-correction percentage 5..95 (default: 23)",
        )
        sp.add_argument(
            "--symbol-kind",
            choices=("auto", "compact", "full"),
            default="auto",
            help="symbol kind (default: auto picks the smallest that fits)",
        )
        sp.add_argument(
            "--layers",
            type=int,
            default=None,
            help="data layer count; requires --symbol-kind compact or full",
        )
        sp.add_argument(
            "--quiet-zone",
            type=int,
            default=AZTEC_DEFAULT_QUIET_ZONE,
            help=f"quiet-zone width in modules (default: {AZTEC_DEFAULT_QUIET_ZONE})",
        )

    def encoder(self, args: argparse.Namespace) -> AztecEncoder:
        return AztecEncoder(
            args.text,
            ecc=args.ecc,
            symbol_kind=args.symbol_kind,
            layers=args.layers,
            quiet_zone=args.quiet_zone,
        )


FORMATS: list[Format] = [Code39(), Code128(), EAN13(), DataMatrix(), QRCode(), PDF417(), Aztec()]


def _build_parser() -> argparse.ArgumentParser:
    try:
        version = importlib.metadata.version("pyStrich")
    except importlib.metadata.PackageNotFoundError:
        version = "unknown"
    parser = argparse.ArgumentParser(
        prog="pystrich",
        description=(
            "Generate 1D/2D barcodes "
            "(Code 39, Code 128, EAN-13, Data Matrix, QR Code, PDF417, Aztec Code). "
            "Pass input via --text or stdin."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {version}")
    sub = parser.add_subparsers(dest="format", required=True, metavar="FORMAT")
    for f in FORMATS:
        f.add_args(sub.add_parser(f.name, help=f.help))
    return parser


def _resolve_text(arg: str | None) -> str:
    if arg is not None:
        return arg
    return sys.stdin.read().rstrip("\n")


def _resolve_output_type(args: argparse.Namespace, fmt: Format) -> OutputType:
    if args.output_type != "auto":
        return args.output_type
    if args.output is not None and args.output != "-":
        ext = os.path.splitext(args.output)[1].lower()
        candidate = _OUTPUT_BY_EXTENSION.get(ext)
        if candidate is not None:
            if candidate not in fmt.available_outputs:
                raise PyStrichInvalidOption(
                    f"output type {candidate!r} (inferred from {args.output!r}) "
                    f"is not supported by {fmt.name}"
                )
            return candidate
    if args.is_tty:
        if "terminal" in fmt.available_outputs:
            return "terminal"
        raise PyStrichInvalidOption(
            f"refusing to write {fmt.name} binary output to a terminal; "
            "pass -o <file> or -t <format>"
        )
    raise PyStrichInvalidOption(
        "specify -t <format> when output is not a terminal "
        "(or pass -o <file> with a recognised extension)"
    )


def _write_payload(output: str | None, payload: bytes) -> None:
    if output is None or output == "-":
        sys.stdout.buffer.write(payload)
        return
    with open(output, "wb") as fp:
        fp.write(payload)


def main(argv: list[str] | None = None) -> int:
    """Run the CLI; return the process exit code."""
    args = _build_parser().parse_args(argv)
    fmt = {f.name: f for f in FORMATS}[args.format]
    args.is_tty = (args.output is None or args.output == "-") and sys.stdout.isatty()
    try:
        args.output_type = _resolve_output_type(args, fmt)
        args.text = _resolve_text(args.text)
        payload = fmt.render(args)
    except PyStrichInvalidInput as exc:
        print(f"pystrich: invalid input: {exc}", file=sys.stderr)
        return 2
    except PyStrichInvalidOption as exc:
        print(f"pystrich: invalid option: {exc}", file=sys.stderr)
        return 2
    _write_payload(args.output, payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
