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

    def _read(image_path: str) -> str:
        # -C 0 disables error correction; --corrections-max=0 is rejected by dmtxread.
        return subprocess.check_output([path, "-C", "0", image_path]).decode()

    return _read
