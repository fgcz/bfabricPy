from __future__ import annotations

import subprocess
from pathlib import Path

from loguru import logger


def scp(source: str | Path, target: str | Path, *, user: str | None = None) -> None:
    """Copies a file using scp from source to target.
    Make sure that either the source or target specifies a host, otherwise you should just use shutil.copyfile.
    If you copy to a folder, it is recommended to end the target with a slash (``/``).
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
    if user and source_remote:
        source = f"{user}@{source}"
    elif user and target_remote:
        target = f"{user}@{target}"

    # create output directory if necessary
    if target_remote:
        host, path = target.split(":", 1)
        parent_path = str(Path(path).parent) if not path.endswith("/") else path
        subprocess.run(["ssh", host, "mkdir", "-p", parent_path], check=True)
    else:
        parent_path = Path(target).parent if not target.endswith("/") else target
        parent_path.mkdir(parents=True, exist_ok=True)

    logger.info(f"scp {source} {target}")
    subprocess.run(["scp", source, target], check=True)


def _is_remote(path: str | Path) -> bool:
    return ":" in str(path)