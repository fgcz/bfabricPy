import shlex
import shutil
import subprocess
from pathlib import Path
from shutil import SameFileError
from subprocess import CalledProcessError
from typing import assert_never

from bfabric_app_runner.inputs.resolve.resolved_inputs import ResolvedFile
from bfabric_app_runner.specs.inputs.file_spec import (
    FileSourceSsh,
    FileSourceLocal,
    FileSourceSshValue,
)
from bfabric_app_runner.util.scp import scp
from loguru import logger


def prepare_resolved_file(file: ResolvedFile, working_dir: Path, ssh_user: str | None) -> None:
    """Prepares the file specified by the spec."""
    output_path = working_dir / file.filename
    output_path.parent.mkdir(exist_ok=True, parents=True)

    if not file.link:
        success = _operation_copy_rsync(file, output_path, ssh_user)
        if not success:
            success = _operation_copy(file, output_path, ssh_user)
    else:
        success = _operation_link_symbolic(file, output_path)
    if not success:
        raise RuntimeError(f"Failed to copy file: {file}")


def _operation_copy_rsync(file: ResolvedFile, output_path: Path, ssh_user: str | None) -> bool:
    match file.source:
        case FileSourceLocal(local=local):
            source_str = str(Path(local).resolve())
        case FileSourceSsh(ssh=FileSourceSshValue(host=host, path=path)):
            source_str = f"{ssh_user}@{host}:{path}" if ssh_user else f"{host}:{path}"
        case _:
            assert_never(file.source)
    cmd = ["rsync", "-Pav", source_str, str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0


def _operation_copy(file: ResolvedFile, output_path: Path, ssh_user: str | None) -> bool:
    match file.source:
        case FileSourceLocal():
            return _operation_copy_cp(file, output_path)
        case FileSourceSsh():
            return _operation_copy_scp(file, output_path, ssh_user)
        case _:
            assert_never(file.source)


def _operation_copy_scp(file: ResolvedFile, output_path: Path, ssh_user: str | None) -> bool:
    try:
        source_str = f"{file.source.ssh.host}:{file.source.ssh.path}"
        scp(source=source_str, target=output_path, user=ssh_user)
    except CalledProcessError:
        return False
    return True


def _operation_copy_cp(file: ResolvedFile, output_path: Path) -> bool:
    cmd = [str(Path(file.source.local).resolve()), str(output_path)]
    logger.info(shlex.join(["cp", *cmd]))
    try:
        shutil.copyfile(*cmd)
    except (OSError, SameFileError):
        return False
    return True


def _operation_link_symbolic(file: ResolvedFile, output_path: Path) -> bool:
    # the link is created relative to the output file, so it should be more portable across apptainer images etc
    source_path = Path(file.source.local).resolve().relative_to(output_path.resolve().parent, walk_up=True)

    # if the file exists, and only if it is a link as well
    if output_path.is_symlink():
        # check if it points to the same file, in which case we don't need to do anything
        if output_path.resolve() == source_path.resolve():
            logger.info("Link already exists and points to the correct file")
            return True
        else:
            logger.info(f"rm {output_path}")
            output_path.unlink()
    elif output_path.exists():
        raise RuntimeError(f"Output path already exists and is not a symlink: {output_path}")
    cmd = ["ln", "-s", str(source_path), str(output_path)]
    logger.info(shlex.join(cmd))
    result = subprocess.run(cmd, check=False)
    return result.returncode == 0
