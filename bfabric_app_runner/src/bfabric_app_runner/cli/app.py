import importlib.metadata
import importlib.resources
import os
import sys
from pathlib import Path

from loguru import logger

from bfabric import Bfabric
from bfabric.experimental.entity_lookup_cache import EntityLookupCache
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.app_runner.resolve_app import load_workunit_information
from bfabric_app_runner.app_runner.runner import run_app, Runner


@use_client
def cmd_app_run(
    app_spec: Path | str,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    read_only: bool = False,
    client: Bfabric,
) -> None:
    """Runs all stages of an app."""
    # TODO doc
    app_version, workunit_ref = load_workunit_information(app_spec, client, work_dir, workunit_ref)

    copy_dev_makefile(work_dir=work_dir)

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
    app_spec: Path | str,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    create_makefile: bool = False,
    client: Bfabric,
    read_only: bool = True,
) -> None:
    """Create chunks, which can be processed individually.

    :param app_spec: Path to the app spec file or module.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param create_makefile: If True, a Makefile will be created in the app directory.
    """

    work_dir = work_dir.resolve()
    # TODO set workunit to processing? (i.e. add read-only option here)

    app_version, workunit_ref = load_workunit_information(app_spec, client, work_dir, workunit_ref)
    with EntityLookupCache.enable():
        runner = Runner(spec=app_version, client=client, ssh_user=None)
        runner.run_dispatch(workunit_ref=workunit_ref, work_dir=work_dir)

    if create_makefile:
        copy_dev_makefile(work_dir=work_dir)


def copy_dev_makefile(work_dir: Path) -> None:
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


def _write_file_chmod(path: Path, text: str, mode: int) -> None:
    if sys.platform == "win32":
        msg = f"Platform {sys.platform} does not support chmod, if this is a deployment it may be insecure."
        logger.warning(msg)
        path.write_text(text)
    else:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT, mode)
        with os.fdopen(fd, "w") as file:
            file.write(text)
