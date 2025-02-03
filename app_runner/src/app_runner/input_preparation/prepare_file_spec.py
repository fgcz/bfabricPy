import shlex
import shutil
import subprocess
from pathlib import Path
from subprocess import CalledProcessError
from typing import assert_never

from loguru import logger

from app_runner.specs.inputs.file_copy_spec import (
    FileSpec,
    FileSourceSsh,
    FileSourceLocal,
    FileSourceSshValue,
    FileMode,
)
from app_runner.util.scp import scp
from bfabric import Bfabric


def prepare_file_spec(spec: FileSpec, client: Bfabric, working_dir: Path, ssh_user: str | None) -> None:
    """Prepares the file specified by the spec."""
    output_path = working_dir / spec.resolve_filename(client=client)
    output_path.parent.mkdir(exist_ok=True, parents=True)
    operations_mapping = {
        FileMode.try_rsync: ["copy_rsync", "copy_cp"],
        FileMode.force_rsync: ["copy_rsync"],
        FileMode.force_scp: ["copy_scp"],
        FileMode.force_cp: ["copy_cp"],
    }
    operations = operations_mapping[spec.mode]
    for operation in operations:
        logger.debug("Trying to copy file using operation: {}", operation)
        raise NotImplementedError


def _operation_copy_rsync(spec: FileSpec, output_path: Path, ssh_user: str | None) -> bool:
    match spec.source:
        case FileSourceLocal(local):
            source_str = str(Path(local).resolve())
        case FileSourceSsh(FileSourceSshValue(host, path)):
            source_str = f"{ssh_user}@{host}:{path}" if ssh_user else f"{host}:{path}"
        case _:
            assert_never(spec.source)
    cmd = ["rsync", "-Pav", source_str, str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def _operation_copy_scp(spec: FileSpec, output_path: Path, ssh_user: str | None) -> bool:
    try:
        source_str = f"{spec.source.ssh.host}:{spec.source.ssh.path}"
        scp(source=source_str, target=output_path, user=ssh_user)
    except CalledProcessError:
        return False
    return True


def _operation_copy_cp(spec: FileSpec, output_path: Path) -> bool:
    cmd = [str(Path(spec.source.local).resolve()), str(output_path)]
    logger.info(shlex.join(["cp"] + cmd))
    shutil.copyfile(*cmd)
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def _operation_link_symbolic(spec: FileSpec, output_path: Path) -> bool:
    pass
