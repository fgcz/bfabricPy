import shutil
from pathlib import Path
from loguru import logger
import cyclopts

from bfabric import Bfabric
from bfabric.config.config_data import ConfigData
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.cli_uv.environment import write_env_data
from bfabric_app_runner.cli_uv.wheel_info import infer_app_module_from_wheel, is_wheel_reference

cli_app = cyclopts.App()


def _setup_env(
    uv_bin: Path,
    work_dir: Path,
    app: Path | str,
    workunit: Path | int,
    client: Bfabric,
    *,
    write_config_data: bool = True,
) -> None:
    work_dir.mkdir(parents=True, exist_ok=True)

    # write the workunit definition
    workunit_def_path = work_dir / "workunit_definition.yml"
    workunit_def = WorkunitDefinition.from_ref(workunit=workunit, client=client)
    workunit_def.to_yaml(workunit_def_path)

    # write the env data
    # TODO this can be added after `bfabric` release
    # client = client.config_data
    config_data = ConfigData(client=client.config, auth=client._auth)
    if not write_config_data:
        config_data = None
    write_env_data(config_data=config_data, work_dir=work_dir, app=app, workunit=workunit_def_path, uv_bin=uv_bin)

    # write the Makefile
    # TODO


@cli_app.command
@use_client
def cmd_dispatch(
    deps_string: str,
    *,
    work_dir: Path,
    workunit: int | Path,
    app: Path | str | None = None,
    uv_bin: Path | None = None,
    client: Bfabric,
) -> None:
    """
    :param deps_string: The dependencies to load to execute the app. This can be any valid `uv run --with` argument,
        but if possible it is recommended to supply a wheel file path as that will also configure the app_ref for you.
    :param work_dir: The working directory where app data and files will be created, this should be specific for this
        workunit and not shared.
    :param workunit: Workunit ID or WorkunitDefinition YAML file path.
    :param app: Required if `deps_string` is not a wheel file path, or, if the app.yml is not at the expected location.
        You can specify the module or the path to the app.yml file here. (TODO this should be explained more thoroughly
        later.)
    :param uv_bin: Optionally, you can provide an alternative path to the uv binary.
    """
    # Resolve the requested environment information
    is_wheel = is_wheel_reference(deps_string=deps_string)
    if app is None:
        if is_wheel:
            app = infer_app_module_from_wheel(Path(deps_string))
        else:
            msg = "If the deps is not a wheel file, you need to provide the app module or path to the app.yml file."
            raise ValueError(msg)
    logger.info(f"Dispatching app with {deps_string=} and {app=}")

    # Actually dispatch the environment
    if uv_bin is None:
        uv_bin = Path(shutil.which("uv"))
    _setup_env(uv_bin=uv_bin, work_dir=work_dir, app=app, workunit=workunit, client=client)


@cli_app.command
def cmd_exec(work_dir: Path, *app_runner_cmd: list[str]) -> None:
    """Executes a command in the managed environment for you.

    :param work_dir: The working directory to operate in, which was dispatched with `dispatch`.
    :param app_runner_cmd: The app-runner command to execute in the managed environment.
    """
    pass


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


# app_dispatch = cyclopts.App(name="bfabric-app-runner-uv dispatch")
#
#
#
# def handle_run(argv: list[str]) -> None:
#    """Handles the main run commands, which will be executed in the managed bfabric-app-runner environment."""
#    pass
#
#
# def handle_cli(argv: list[str]) -> None:
#    """Handles the command line interface for the bfabric-app-runner-uv CLI.
#
#    Since we want to dispatch the command to the managed `bfabric-app-runner` in some cases, this function
#    performs some direct handling of the command line arguments. This is kind of restrictive compared
#    to other commands, but gives us the most flexibility for now.
#
#    TODO this might be reconsidered later. maybe it could be done cleaner with cyclopts too
#    """
#    argv = argv[1:]
#
#    if argv[0] == "run":
#        # send the command ot the bfabric-app-runner env
#        handle_run(argv[1:])
#    elif argv[0] == "dispatch":
#        app_dispatch(argv[1:])
#    else:
#        raise ValueError(f"Unknown command: {argv[0]}")
#
#
# def main() -> None:
#    """Main entry point for the `bfabric-app-runner-uv` CLI."""
#    handle_cli(sys.argv)


if __name__ == "__main__":
    cli_app()
