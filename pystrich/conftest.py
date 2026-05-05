import os
import subprocess
from shutil import which

import pytest


@pytest.fixture
def zbarimg():
    path = which("zbarimg")
    if not path:
        pytest.skip("zbarimg not installed")

    def _read(image_path: "str | os.PathLike[str]") -> str:
        output = subprocess.check_output(
            [path, "--quiet", "--raw", os.fspath(image_path)]
        ).decode()
        return output.rstrip("\n")

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
