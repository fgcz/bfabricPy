import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

import cyclopts
from loguru import logger

app = cyclopts.App()


# TODO i need to decide what is better
#  - boilerplate -> this creates at least a clean implementation, but it could have potential versioning issues
#  - hack -> this would completely defer the parsing to the wrapped bfabric-app-runner
#            but the big challenge is how to hack the "app_spec" information into it cleanly...
#            TODO to be checked and solved)

# OK
# - assuming i refactor he existing app runner interface to make `app_spec` an optional parameter that can be filled
#   with an env variable, or as a top level argument for the CLI, would that solve my problem?


def _handle(*args: str, wheel_path: Path, **kwargs: Any) -> None:
    python_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    command = [
        "uv",
        "run",
        "-p",
        python_version,
        "--isolated",
        "--no-project",
        "--with",
        str(wheel_path),
        "bfabric-app-runner",
        *args,
        # TODO infer the package name and bind it -> this will require making it possible to inject it optionally
        #  at top level,,
        #  alternatively we could hack it at the end depending on the command (make it toggleable maybe)
    ]
    for key, value in kwargs.items():
        key_fmt = key.replace("_", "-")

        if isinstance(value, bool):
            if value:
                command.append(f"--{key_fmt}")
            else:
                command.append(f"--no-{key_fmt}")
        else:
            command.append(f"--{key_fmt}={value}")
    cmd = shlex.join(command)
    logger.info(f"Executing: {cmd}")
    subprocess.run(command, check=False)


def _get_package_name(wheel_path: Path) -> str:
    """Get the package name from the wheel path."""
    return wheel_path.name.split("-")[0]


@app.command
def dispatch(
    wheel_path: Path,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    create_makefile: bool = False,
    create_env_file: bool = True,
) -> None:
    """TODO"""
    _handle(
        "app",
        "dispatch",
        wheel_path=wheel_path,
        app_spec=_get_package_name(wheel_path),
        work_dir=work_dir,
        workunit_ref=workunit_ref,
        create_makefile=create_makefile,
        create_env_file=create_env_file,
    )


@app.command
def run(
    wheel_path: Path,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    read_only: bool = False,
    create_env_file: bool = True,
) -> None:
    """TODO"""
    _handle(
        "app",
        "run",
        wheel_path=wheel_path,
        app_spec=_get_package_name(wheel_path),
        work_dir=work_dir,
        workunit_ref=workunit_ref,
        ssh_user=ssh_user,
        force_storage=force_storage,
        read_only=read_only,
        create_env_file=create_env_file,
    )


@app.command()
def process(
    wheel_path: Path,
    chunk_dir: Path,
) -> None:
    """TODO"""
    _handle(
        "chunk",
        "process",
        wheel_path=wheel_path,
        app_spec=_get_package_name(wheel_path),
        chunk_dir=chunk_dir,
    )


@app.command()
def inputs(
    wheel_path: Path,
    inputs_yaml: Path,
    target_folder: Path | None = None,
    *,
    ssh_user: str | None = None,
    filter: str | None = None,
) -> None:
    """TODO"""
    _handle(
        "inputs",
        "prepare",
        inputs_yaml=inputs_yaml,
        target_folder=target_folder,
        ssh_user=ssh_user,
        filter=filter,
    )


@app.command()
def outputs(
    wheel_path: Path,
    outputs_yaml: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    reuse_default_resource: bool = True,
) -> None:
    """TODO"""
    _handle(
        "outputs",
        "register",
        wheel_path=wheel_path,
        app_spec=_get_package_name(wheel_path),
        outputs_yaml=outputs_yaml,
        workunit_ref=workunit_ref,
        ssh_user=ssh_user,
        force_storage=force_storage,
        reuse_default_resource=reuse_default_resource,
    )
