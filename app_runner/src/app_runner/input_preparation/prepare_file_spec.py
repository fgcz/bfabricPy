import shlex
import shutil
import subprocess
from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError
from typing import assert_never

from loguru import logger

from app_runner.specs.inputs.file_copy_spec import (
    FileSpec,
    FileSourceSsh,
    FileSourceLocal,
    FileSourceSshValue,
    LinkingMode,
)
from app_runner.util.scp import scp
from bfabric import Bfabric


def prepare_file_spec(spec: FileSpec, client: Bfabric, working_dir: Path, ssh_user: str | None) -> None:
    """Prepares the file specified by the spec."""
    output_path = working_dir / spec.resolve_filename(client=client)
    output_path.parent.mkdir(exist_ok=True, parents=True)

    success = False
    match spec.link:
        case LinkingMode.copy:
            success = _operation_copy_rsync(spec, output_path, ssh_user)
            if not success:
                success = _operation_copy(spec, output_path, ssh_user)
        case LinkingMode.link:
            success = _operation_link_symbolic(spec, output_path)
        case _:
            assert_never(spec.link)
    if not success:
        raise RuntimeError(f"Failed to copy file: {spec}")


def _operation_copy_rsync(spec: FileSpec, output_path: Path, ssh_user: str | None) -> bool:
    match spec.source:
        case FileSourceLocal(local=local):
            source_str = str(Path(local).resolve())
        case FileSourceSsh(ssh=FileSourceSshValue(host=host, path=path)):
            source_str = f"{ssh_user}@{host}:{path}" if ssh_user else f"{host}:{path}"
        case _:
            assert_never(spec.source)
    cmd = ["rsync", "-Pav", source_str, str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def _operation_copy(spec: FileSpec, output_path: Path, ssh_user: str | None) -> bool:
    match spec.source:
        case FileSourceLocal():
            return _operation_copy_cp(spec, output_path)
        case FileSourceSsh():
            return _operation_copy_scp(spec, output_path, ssh_user)
        case _:
            assert_never(spec.source)


def _operation_copy_scp(spec: FileSpec, output_path: Path, ssh_user: str | None) -> bool:
    try:
        source_str = f"{spec.source.ssh.host}:{spec.source.ssh.path}"
        scp(source=source_str, target=output_path, user=ssh_user)
    except CalledProcessError:
        return False
    return True


def _operation_copy_cp(spec: FileSpec, output_path: Path) -> bool:
    cmd = [str(Path(spec.source.local).resolve()), str(output_path)]
    logger.info(shlex.join(["cp", *cmd]))
    try:
        shutil.copyfile(*cmd)
    except (OSError, SameFileError):
        return False
    return True


def _operation_link_symbolic(spec: FileSpec, output_path: Path) -> bool:
    # the link is created relative to the output file, so it should be more portable across apptainer images etc
    source_path = Path(spec.source.local).resolve().relative_to(output_path.resolve().parent)
    cmd = ["ln", "-s", str(source_path), str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0
