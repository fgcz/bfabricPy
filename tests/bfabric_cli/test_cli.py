import shlex
import subprocess
import sys

import pytest


@pytest.mark.skipif(sys.version_info < (3, 10), reason="requires python3.10 or higher")
@pytest.mark.parametrize(
    "command",
    [
        "--help",
    ],
)
def test_command_runs(command):
    subprocess.run(["bfabric-cli"] + shlex.split(command), check=True)
