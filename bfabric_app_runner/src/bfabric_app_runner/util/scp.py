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

    # scp/ssh parse a leading "-" as an option, so an endpoint like "-oProxyCommand=..." would smuggle
    # arbitrary options (and thus local command execution) into the invocation. A real path or
    # ``[user@]host`` never starts with "-", so reject it rather than let it reach the command line.
    _reject_option_like(source, role="scp source")
    _reject_option_like(target, role="scp target")

    if mkdir:
        if target_remote:
            host, path = target.split(":", 1)
            # ssh joins its trailing args and runs them through the remote *shell*, so the remote path
            # must be quoted -- otherwise a path containing shell metacharacters would execute arbitrary
            # commands on the host.
            quoted_parent = shlex.quote(str(Path(path).parent))
            logger.debug(f"ssh {host} mkdir -p {quoted_parent}")
            _ = subprocess.run(["ssh", host, "mkdir", "-p", quoted_parent], check=True)
        else:
            parent_path = Path(target).parent
            parent_path.mkdir(parents=True, exist_ok=True)

    cmd = ["scp", source, target]
    logger.info(shlex.join(cmd))
    subprocess.run(cmd, check=True)


def _reject_option_like(value: str, *, role: str) -> None:
    """Reject an scp/ssh endpoint that would be misread as a command-line option (a leading ``-``)."""
    if value.startswith("-"):
        raise ValueError(f"{role} must not start with '-': {value!r}")


def _is_remote(path: str | Path) -> bool:
    return ":" in str(path)
