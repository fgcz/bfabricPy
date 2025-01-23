import shlex
import subprocess

import pytest


@pytest.mark.parametrize(
    "command",
    [
        "--help",
    ],
)
def test_command_runs(command):
    subprocess.run(["bfabric-cli"] + shlex.split(command), check=True)
