import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Literal

import cyclopts
import yaml
from loguru import logger

from bfabric import Bfabric
from bfabric.config.config_data import ConfigData
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.cli_uv.dev_makefile import write_dev_makefile, format_env_data
from bfabric_app_runner.cli_uv.environment import write_env_data, ENV_KEY_PYTHON_VERSION, ENV_KEY_DEPS_STRING
from bfabric_app_runner.cli_uv.wheel_info import infer_app_module_from_wheel, is_wheel_reference

cli_app = cyclopts.App()


def _setup_env(
    uv_bin: Path,
    work_dir: Path,
    app: Path | str,
    workunit: Path | int,
    client: Bfabric,
    *,
    deps_string: str,
    write_config_data: bool = True,
    python_version: str = "3.13",
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
    env_data = write_env_data(
        config_data=config_data,
        work_dir=work_dir,
        app=app,
        workunit=workunit_def_path,
        uv_bin=uv_bin,
        python_version=python_version,
        deps_string=deps_string,
    )

    # write the Makefile
    write_dev_makefile(work_dir=work_dir, env_data=env_data)


@cli_app.command(name="dispatch")
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
    _setup_env(uv_bin=uv_bin, work_dir=work_dir, app=app, workunit=workunit, client=client, deps_string=deps_string)


# TODO after all doing this with cyclopts is problematic and we will have to parse manually
#  -> use cyclopts for the commands which are ok on a per-command basis, and handle this one manually as it is special
#  (i.e. we don't want help on this command either as it should be dispatched)


@cli_app.command(name="exec")
def cmd_exec(*app_runner_cmd: str) -> None:
    """Executes a command in the managed environment for you.
    :param app_runner_cmd: The app-runner command to execute in the managed environment.
    """
    env_path = Path("env.yml")
    env = yaml.safe_load(env_path.read_text())
    print(env)
    cmd = [
        "uv",
        "run",
        "-p",
        env[ENV_KEY_PYTHON_VERSION],
        "--isolated",
        "--no-project",
        "--with",
        env[ENV_KEY_DEPS_STRING],
        "bfabric-app-runner",
        *app_runner_cmd,
    ]
    print(cmd)
    logger.info(f"Executing command: {shlex.join(cmd)}")
    subprocess.run(cmd, check=False)


@cli_app.command(name="print-env-vars")
def cmd_print_env_vars(work_dir: Path, format: Literal["bash", "fish", "makefile"]) -> None:
    """Prints the environment variables for the managed environment."""
    env_data = yaml.safe_load((work_dir / "env.yml").read_text())
    print(format_env_data(env_data=env_data, format=format))


if __name__ == "__main__":
    cli_app()
