import subprocess
from pathlib import Path

from bfabric import Bfabric
from bfabric.experimental.workunit_definition import WorkunitDefinition
from bfabric.utils.cli_integration import use_client
from bfabric_app_runner.cli.cmd_prepare import cmd_prepare_workunit
from bfabric_app_runner.errors import CommandFailedError


@use_client
def cmd_run_workunit(app_definition: Path, scratch_root: Path, workunit_ref: int | Path, *, client: Bfabric) -> None:
    """Runs a workunit by preparing the workunit and executing it."""
    workunit_definition = WorkunitDefinition.from_ref(workunit_ref, client=client)
    assert workunit_definition.registration is not None
    workunit_id = workunit_definition.registration.workunit_id
    try:
        _ = client.save("workunit", {"id": workunit_id, "status": "processing"})
        work_dir = (
            scratch_root
            / f"A{workunit_definition.registration.application_id}_{workunit_definition.registration.application_name}"
            / f"WU{workunit_id}"
        )
        work_dir.mkdir(parents=True, exist_ok=True)
        # TODO caching of workunit_definition
        cmd_prepare_workunit(app_spec=app_definition, work_dir=work_dir, workunit_ref=workunit_ref)
        # TODO directly call through python
        # Raising inside the try (rather than check=True, or SystemExit) keeps the workunit marked failed.
        proc = subprocess.run(["make", "run-all"], cwd=work_dir, check=False)
        if proc.returncode != 0:
            raise CommandFailedError(["make", "run-all"], proc.returncode)
        _ = client.save("workunit", {"id": workunit_id, "status": "available"})
    except Exception:
        _ = client.save("workunit", {"id": workunit_id, "status": "failed"})
        raise
