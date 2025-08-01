import shlex
import subprocess

import pytest


@pytest.mark.parametrize(
    "command",
    [
        "--help",
        "inputs --help",
        "inputs check --help",
        "inputs clean --help",
        "inputs list --help",
        "inputs prepare --help",
        "outputs --help",
        "outputs register --help",
        "outputs register-single-file --help",
        "validate --help",
        "validate app-spec --help",
        "validate app-spec-template --help",
        "validate inputs-spec --help",
        "validate outputs-spec --help",
    ],
)
def test_help(command):
    subprocess.run(["bfabric-app-runner"] + shlex.split(command), check=True)
