import shlex
import subprocess
import sys
from pathlib import Path

from loguru import logger


# TODO this is a total hack and proof of concept right now


def wheel_dispatch(argv: list[str]) -> None:
    """tbd"""
    argv = argv.copy()
    wheel_path = argv.pop(0)

    if not Path(wheel_path).is_file():
        raise FileNotFoundError(f"Wheel {wheel_path} is not a file.")

    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    command = [
        "uv",
        "run",
        "-p",
        python_version,
        "--isolated",
        "--no-project",
        "--with",
        wheel_path,
        "bfabric-app-runner",
        # TODO infer the package name and bind it -> this will require making it possible to inject it optionally
        #  at top level,,
        #  alternatively we could hack it at the end depending on the command (make it toggleable maybe)
        *argv,
    ]
    cmd = shlex.join(command)
    logger.info(f"Executing: {cmd}")
    subprocess.run(command, check=False)


def main() -> None:
    """tbd"""
    wheel_dispatch(sys.argv[1:])


# import cyclopts
#
# cmd_wheel = cyclopts.App()
## TODO the docs should actually be consumed from the wheel. this should not perform the CLI arg handling
#
# @cmd_wheel.command
# def dispatch(wheel_path: Path) -> None:
#    pass
#
# @cmd_wheel.command
# def run(wheel_path: Path) -> None:
#    pass
#
# @cmd_wheel.command
# def process(wheel_path: Path) -> None:
#    pass
#
# @cmd_wheel.command
# def inputs(wheel_path: Path) -> None:
#    pass
#
# @cmd_wheel.command
# def stage(wheel_path: Path) -> None:
#    pass
#
