from pathlib import Path

from bfabric import Bfabric
from bfabric.experimental.entity_lookup_cache import EntityLookupCache
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.app_runner.resolve_app import load_workunit_information
from bfabric_app_runner.app_runner.runner import run_app, Runner
from bfabric_app_runner.output_registration import register_outputs


@use_client
def cmd_chunk_run_all(
    app_spec: Path | str,
    work_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    read_only: bool = False,
    client: Bfabric,
) -> None:
    """Run all chunks, including input preparation, processing, and output registration.

    :param app_spec: Path to the app spec file or module.
    :param work_dir: Path to the work directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    :param force_storage: Path to the storage.yml for the output files instead of where it should go (for testing).
    :param read_only: If True, results will not be registered and the workunit status will not be changed.
    """
    app_version, workunit_ref = load_workunit_information(
        app_spec=app_spec, client=client, work_dir=work_dir, workunit_ref=workunit_ref
    )

    run_app(
        app_spec=app_version,
        workunit_ref=workunit_ref,
        work_dir=work_dir,
        client=client,
        ssh_user=ssh_user,
        read_only=read_only,
        dispatch_active=False,
        force_storage=force_storage,
    )


@use_client
def cmd_chunk_process(app_spec: Path | str, chunk_dir: Path, *, client: Bfabric) -> None:
    """Process a chunk.

    Note that the input files must be prepared before running this command.
    :param app_spec: Path to the app spec file or module.
    :param chunk_dir: Path to the chunk directory.
    """
    chunk_dir = chunk_dir.resolve()

    # TODO this lookup of workunit_definition is very problematic now! FIX NEEDED
    app_version, workunit_ref = load_workunit_information(
        app_spec=app_spec, client=client, work_dir=chunk_dir, workunit_ref=chunk_dir / ".." / "workunit_definition.yml"
    )

    with EntityLookupCache.enable():
        runner = Runner(spec=app_version, client=client, ssh_user=None)
        runner.run_process(chunk_dir=chunk_dir)


@use_client
def cmd_chunk_outputs(
    app_spec: Path | str,
    chunk_dir: Path,
    workunit_ref: int | Path,
    *,
    ssh_user: str | None = None,
    force_storage: Path | None = None,
    read_only: bool = False,
    reuse_default_resource: bool = True,
    client: Bfabric,
) -> None:
    """Register the output files of a chunk.

    :param app_spec: Path to the app spec file or module.
    :param chunk_dir: Path to the chunk directory.
    :param workunit_ref: Reference to the workunit (ID or YAML file path).
    :param ssh_user: SSH user to use for downloading the input files, instead of the current user.
    :param read_only: If True, the workunit will not be set to processing.
    :param reuse_default_resource: If True, the default resource will be reused for the output files. (recommended)
    """
    # TODO redundant functionality with "outputs register"
    chunk_dir = chunk_dir.resolve()

    app_version, workunit_ref = load_workunit_information(
        app_spec=app_spec, client=client, work_dir=chunk_dir, workunit_ref=workunit_ref
    )

    runner = Runner(spec=app_version, client=client, ssh_user=ssh_user)
    runner.run_collect(workunit_ref=workunit_ref, chunk_dir=chunk_dir)
    # TODO specify cache file
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=client)
    if not read_only:
        register_outputs(
            outputs_yaml=chunk_dir / "outputs.yml",
            workunit_definition=workunit_definition,
            client=client,
            ssh_user=ssh_user,
            force_storage=force_storage,
            reuse_default_resource=reuse_default_resource,
        )
