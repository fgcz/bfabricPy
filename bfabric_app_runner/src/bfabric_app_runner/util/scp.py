from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from loguru import logger


def scp(source: str | Path, target: str | Path, *, user: str | None = None, mkdir: bool = True) -> None:
    """Copies a file using scp from source to target.
    Make sure that either the source or target specifies a host, otherwise you should just use shutil.copyfile.
    Always specify the full path for the target, not just a directory.
    """
    source = str(source)
    target = str(target)
    source_remote = _is_remote(source)
    target_remote = _is_remote(target)
    if source_remote == target_remote:
        msg = (
            f"Either source or target should be remote, but not both. "
            f"source_remote={repr(source_remote)} == target_remote={repr(target_remote)}"
        )
        raise ValueError(msg)
    if target[-1] == "/":
        raise ValueError(f"Target should be a file, not a directory: {target}")
    if user and source_remote:
        source = f"{user}@{source}"
    elif user and target_remote:
        target = f"{user}@{target}"

    if mkdir:
        if target_remote:
            host, path = target.split(":", 1)
            parent_path = Path(path).parent
            logger.debug(f"ssh {host} mkdir -p {parent_path}")
            subprocess.run(["ssh", host, "mkdir", "-p", parent_path], check=True)
        else:
            parent_path = Path(target).parent
            parent_path.mkdir(parents=True, exist_ok=True)

    cmd = ["scp", source, target]
    logger.info(shlex.join(cmd))
    subprocess.run(cmd, check=True)


def _is_remote(path: str | Path) -> bool:
    return ":" in str(path)
