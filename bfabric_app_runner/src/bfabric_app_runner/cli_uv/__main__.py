import sys
from pathlib import Path

import cyclopts

from bfabric_app_runner.cli_uv.wheel import infer_app_module_from_wheel

# @app.default
# def dispatch():
#    pass


# @app.command
# def wheel(
#    *args: str,
#    with_: Path,
# ):
#    if with_.count(",") == 0 and with_.endswith(".whl"):
#        # extract the app ref from it.
#        pass
#
#    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
#    command = [
#        "uv",
#        "run",
#        "-p",
#        python_version,
#        "--isolated",
#        "--no-project",
#        "--with",
#        str(with_),
#        "bfabric-app-runner",
#        *args,
#        # TODO infer the package name and bind it -> this will require making it possible to inject it optionally
#        #  at top level,,
#        #  alternatively we could hack it at the end depending on the command (make it toggleable maybe)
#    ]
#


app_dispatch = cyclopts.App(name="bfabric-app-runner-uv dispatch")


@app_dispatch.default()
def cmd_dispatch(
    app_pkg: Path,
    work_dir: Path,
    workunit_ref: int | Path,
    app_module: str | None = None,
) -> None:
    """Dispatches a bfabric-app-runner environment for the provided package."""
    if app_module is None:
        app_module = infer_app_module_from_wheel(app_pkg)

    pass


def handle_run(argv: list[str]) -> None:
    """Handles the main run commands, which will be executed in the managed bfabric-app-runner environment."""
    pass


def handle_cli(argv: list[str]) -> None:
    """Handles the command line interface for the bfabric-app-runner-uv CLI.

    Since we want to dispatch the command to the managed `bfabric-app-runner` in some cases, this function
    performs some direct handling of the command line arguments. This is kind of restrictive compared
    to other commands, but gives us the most flexibility for now.

    TODO this might be reconsidered later. maybe it could be done cleaner with cyclopts too
    """
    argv = argv[1:]

    if argv[0] == "run":
        # send the command ot the bfabric-app-runner env
        handle_run(argv[1:])
    elif argv[0] == "dispatch":
        app_dispatch(argv[1:])
    else:
        raise ValueError(f"Unknown command: {argv[0]}")


def main() -> None:
    """Main entry point for the `bfabric-app-runner-uv` CLI."""
    handle_cli(sys.argv)


if __name__ == "__main__":
    main()
