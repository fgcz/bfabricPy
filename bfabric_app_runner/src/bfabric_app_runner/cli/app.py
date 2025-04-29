import importlib.metadata
import importlib.resources
import shlex
from pathlib import Path

from loguru import logger

from bfabric import Bfabric
from bfabric.config.config_data import ConfigData, export_config_data
from bfabric.experimental.entity_lookup_cache import EntityLookupCache
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.app_runner.resolve_app import load_workunit_information
from bfabric_app_runner.app_runner.runner import run_app, Runner


@use_client
def cmd_app_run(
    app_spec: Path,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    read_only: bool = False,
    create_env_file: bool = True,
    client: Bfabric,
) -> None:
    """Runs all stages of an app."""
    # TODO doc
    app_version, workunit_ref = load_workunit_information(app_spec, client, work_dir, workunit_ref)

    # TODO use client.config_data (once 1.13.27 is released)
    copy_dev_makefile(
        work_dir=work_dir,
        config_data=ConfigData(client=client.config, auth=client._auth),
        create_env_file=create_env_file,
    )

    # TODO(#107): usage of entity lookup cache was problematic -> beyond the full solution we could also consider
    #             to deactivate the cache for the output registration
    # with EntityLookupCache.enable():
    run_app(
        app_spec=app_version,
        workunit_ref=workunit_ref,
        work_dir=work_dir,
        client=client,
        ssh_user=ssh_user,
        read_only=read_only,
        force_storage=force_storage,
    )


@use_client
def cmd_app_dispatch(
    app_spec: Path,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    client: Bfabric,
) -> None:
    """Create chunks, which can be processed individually.

    :param app_spec: Path to the app spec file.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    """
    work_dir = work_dir.resolve()
    # TODO set workunit to processing? (i.e. add read-only option here)

    app_version, workunit_ref = load_workunit_information(app_spec, client, work_dir, workunit_ref)

    with EntityLookupCache.enable():
        runner = Runner(spec=app_version, client=client, ssh_user=None)
        runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)


def copy_dev_makefile(work_dir: Path, config_data: ConfigData, create_env_file: bool) -> None:
    """Copies the workunit.mk file to the work directory, and sets the version of the app runner.

    It also creates a .env file containing the BFABRICPY_CONFIG_OVERRIDE environment variable containing the configured
    connection. For security reasons it will be chmod 600.
    """
    with importlib.resources.path("bfabric_app_runner", "resources/workunit.mk") as source_path:
        target_path = work_dir / "Makefile"

        makefile_template = source_path.read_text()
        app_runner_version = importlib.metadata.version("bfabric_app_runner")
        makefile = makefile_template.replace("@RUNNER_VERSION@", app_runner_version)

        if target_path.exists():
            logger.info("Renaming existing Makefile to Makefile.bak")
            target_path.rename(work_dir / "Makefile.bak")
        logger.info(f"Copying Makefile from {source_path} to {target_path}")
        target_path.parent.mkdir(exist_ok=True, parents=True)
        target_path.write_text(makefile)

    if create_env_file:
        env_file_content = f"BFABRICPY_CONFIG_OVERRIDE={shlex.quote(export_config_data(config_data))}\n"
        env_file_path = work_dir / ".env"
        if env_file_path.exists():
            logger.info("Renaming existing .env file to .env.bak")
            env_file_path.rename(work_dir / ".env.bak")
        logger.info(f"Creating .env file at {env_file_path}")
        env_file_path.write_text(env_file_content)
        env_file_path.chmod(0o600)
