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
            _ = subprocess.run(["ssh", host, "mkdir", "-p", parent_path], check=True)
        else:
            parent_path = Path(target).parent
            parent_path.mkdir(parents=True, exist_ok=True)

    cmd = ["scp", source, target]
    logger.info(shlex.join(cmd))
    _ = subprocess.run(cmd, check=True)


def _is_remote(path: str | Path) -> bool:
    """True if ``path`` is an scp remote spec (``[user@]host:path``) rather than a local path.

    Mirrors scp/rsync's own heuristic: a colon only introduces a host if it appears before the first
    path separator, so a colon inside a local path (e.g. ``./weird:name``) stays local. A single
    leading character before the colon is a Windows drive letter (``C:\\...``), not a hostname.
    """
    s = str(path)
    colon = s.find(":")
    if colon == -1:
        return False
    first_sep = min((i for i in (s.find("/"), s.find("\\")) if i != -1), default=len(s))
    if colon > first_sep:
        return False
    return colon != 1
