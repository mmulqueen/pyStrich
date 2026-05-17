"""Tests for the pystrich CLI."""

from __future__ import annotations

import io
import sys

import pytest

from pystrich import cli
from pystrich.datamatrix import FNC1, DataMatrixData, DataMatrixEncoder

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize(
    "subcommand, text",
    [
        pytest.param("code39", "HELLO", id="code39"),
        pytest.param("code128", "Hello, world", id="code128"),
        pytest.param("ean13", "012345678901", id="ean13"),
    ],
)
@pytest.mark.parametrize(
    "output_type, extension, header",
    [
        pytest.param("png", "png", PNG_MAGIC, id="png"),
        pytest.param("svg", "svg", b"<svg ", id="svg"),
        pytest.param("eps", "eps", b"%!PS-Adobe", id="eps"),
    ],
)
def test_1d_smoke(tmp_path, subcommand, text, output_type, extension, header):
    out = tmp_path / f"barcode.{extension}"
    assert cli.main([subcommand, "--text", text, "-t", output_type, "-o", str(out)]) == 0
    assert out.read_bytes().startswith(header)


@pytest.mark.parametrize(
    "subcommand, text",
    [
        pytest.param("datamatrix", "datamatrix payload", id="datamatrix"),
        pytest.param("qrcode", "qr payload", id="qrcode"),
        pytest.param("aztec", "aztec payload", id="aztec"),
    ],
)
@pytest.mark.parametrize(
    "output_type, extension, needle",
    [
        pytest.param("png", "png", PNG_MAGIC, id="png"),
        pytest.param("svg", "svg", b"<svg ", id="svg"),
        pytest.param("eps", "eps", b"%!PS-Adobe", id="eps"),
        pytest.param("ascii", "txt", b"X", id="ascii"),
        pytest.param("terminal", "txt", "▀".encode(), id="terminal"),
        pytest.param("dxf", "dxf", b"SECTION", id="dxf"),
    ],
)
def test_2d_smoke(tmp_path, subcommand, text, output_type, extension, needle):
    out = tmp_path / f"barcode.{extension}"
    assert cli.main([subcommand, "--text", text, "-t", output_type, "-o", str(out)]) == 0
    data = out.read_bytes()
    if output_type == "png":
        assert data.startswith(needle)
    else:
        assert needle in data


def test_stdin_input(tmp_path, monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO("HELLO FROM STDIN\n"))
    out = tmp_path / "barcode.png"
    assert cli.main(["code128", "-o", str(out)]) == 0
    assert out.read_bytes().startswith(PNG_MAGIC)


def test_invalid_input_exits_2(capsys):
    assert cli.main(["ean13", "--text", "not-digits", "-t", "png", "-o", "-"]) == 2
    assert "invalid input" in capsys.readouterr().err


def test_cell_size_rounds_for_raster(tmp_path):
    out_27 = tmp_path / "27.png"
    out_3 = tmp_path / "3.png"
    assert cli.main(["qrcode", "--text", "x", "-o", str(out_27), "--cell-size", "2.7"]) == 0
    assert cli.main(["qrcode", "--text", "x", "-o", str(out_3), "--cell-size", "3"]) == 0
    assert out_27.read_bytes() == out_3.read_bytes()


def test_cell_size_zero_errors(capsys, tmp_path):
    out = tmp_path / "x.png"
    assert cli.main(["qrcode", "--text", "x", "-o", str(out), "--cell-size", "0"]) == 2
    assert "--cell-size" in capsys.readouterr().err


def test_inverse_changes_svg(tmp_path):
    plain = tmp_path / "plain.svg"
    inv = tmp_path / "inv.svg"
    assert cli.main(["qrcode", "--text", "x", "-o", str(plain), "--no-inverse"]) == 0
    assert cli.main(["qrcode", "--text", "x", "-o", str(inv), "--inverse"]) == 0
    assert plain.read_bytes() != inv.read_bytes()


def test_mark_shape_circular_emits_circle(tmp_path):
    out = tmp_path / "x.svg"
    assert cli.main(["qrcode", "--text", "x", "-o", str(out), "--mark-shape", "circular"]) == 0
    assert b"<circle" in out.read_bytes()


def test_mark_shape_default_emits_rect(tmp_path):
    out = tmp_path / "x.svg"
    assert cli.main(["qrcode", "--text", "x", "-o", str(out)]) == 0
    body = out.read_bytes()
    assert b"<rect" in body
    assert b"<circle" not in body


@pytest.mark.parametrize(
    "extra_args, output_type",
    [
        pytest.param(["--inverse"], "png", id="inverse-png"),
        pytest.param(["--inverse"], "ascii", id="inverse-ascii"),
        pytest.param(["--inverse"], "terminal", id="inverse-terminal"),
        pytest.param(["--mark-shape", "circular"], "png", id="mark-shape-png"),
        pytest.param(["--dxf-units", "in"], "png", id="dxf-units-png"),
        pytest.param(["--dxf-units", "in"], "svg", id="dxf-units-svg"),
    ],
)
def test_unsupported_flag_errors(extra_args, output_type, capsys, tmp_path):
    out = tmp_path / f"x.{output_type}"
    rc = cli.main(["qrcode", "--text", "x", "-t", output_type, "-o", str(out), *extra_args])
    assert rc == 2
    err = capsys.readouterr().err
    assert "invalid option" in err
    assert extra_args[0] in err


def test_encoding_choice_routed_to_encoder(capsys, tmp_path):
    out = tmp_path / "dm.png"
    rc = cli.main(["datamatrix", "--text", "café", "--encoding", "ascii", "-o", str(out)])
    assert rc == 2
    assert "invalid input" in capsys.readouterr().err


def test_substitute_with_fnc1_matches_direct_api(tmp_path):
    via_cli = tmp_path / "cli.dxf"
    assert (
        cli.main(
            ["datamatrix", "--text", "01|0123", "--substitute-with-fnc1", "|", "-o", str(via_cli)]
        )
        == 0
    )
    direct = (
        DataMatrixEncoder(DataMatrixData("01", FNC1, "0123", encoding="ascii"))
        .get_dxf()
        .encode("utf-8")
    )
    assert via_cli.read_bytes() == direct


def test_substitute_with_fnc1_multichar_errors(capsys, tmp_path):
    out = tmp_path / "x.png"
    rc = cli.main(["datamatrix", "--text", "x", "--substitute-with-fnc1", "ab", "-o", str(out)])
    assert rc == 2
    assert "--substitute-with-fnc1" in capsys.readouterr().err


@pytest.mark.parametrize(
    "subcommand, extension",
    [
        pytest.param("qrcode", "png", id="png"),
        pytest.param("qrcode", "svg", id="svg"),
        pytest.param("code39", "eps", id="eps"),
        pytest.param("datamatrix", "dxf", id="dxf"),
    ],
)
def test_auto_resolves_from_extension(tmp_path, subcommand, extension):
    out = tmp_path / f"x.{extension}"
    assert cli.main([subcommand, "--text", "X", "-o", str(out)]) == 0
    assert out.stat().st_size > 0


def test_auto_rejects_unsupported_extension_for_format(tmp_path, capsys):
    out = tmp_path / "x.dxf"
    rc = cli.main(["code128", "--text", "x", "-o", str(out)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "'dxf'" in err
    assert "code128" in err


def test_auto_to_tty_2d_picks_terminal(monkeypatch, capfd):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert cli.main(["qrcode", "--text", "x"]) == 0
    out, _ = capfd.readouterr()
    assert "▀" in out or "▄" in out or "█" in out


def test_auto_to_tty_1d_refuses_to_dump_binary(monkeypatch, capsys):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    rc = cli.main(["code128", "--text", "x"])
    assert rc == 2
    assert "refusing to write" in capsys.readouterr().err


def test_auto_pipe_without_type_errors(capsys):
    rc = cli.main(["qrcode", "--text", "x"])
    assert rc == 2
    assert "not a terminal" in capsys.readouterr().err


def test_terminal_output_no_ansi_when_redirected(tmp_path):
    out = tmp_path / "t.txt"
    assert cli.main(["qrcode", "--text", "x", "-t", "terminal", "-o", str(out)]) == 0
    assert b"\x1b[" not in out.read_bytes()


def test_terminal_output_has_ansi_when_tty(monkeypatch, capfd):
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    assert cli.main(["qrcode", "--text", "x", "-t", "terminal"]) == 0
    out, _ = capfd.readouterr()
    assert "\x1b[" in out


def test_version_prints(capsys):
    with pytest.raises(SystemExit) as exc_info:
        cli.main(["--version"])
    assert exc_info.value.code == 0
    assert "pystrich" in capsys.readouterr().out
