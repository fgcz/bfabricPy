from __future__ import annotations

import functools
import inspect
import os
import sys
import traceback
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, NoReturn, TypeVar, cast

from loguru import logger
from rich.highlighter import RegexHighlighter
from rich.theme import Theme

from bfabric.config import DEFAULT_CONFIG_FILE

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")


def use_client(fn: Callable[..., T], setup_logging: bool = True) -> Callable[..., T]:
    """Decorator that injects a Bfabric client into a function.

    The client is automatically created using default configuration if not provided.
    If setup_logging is True, logging is set up using setup_script_logging.

    The decorator removes the 'client' parameter from the function signature and injects
    two optional keyword parameters into every decorated command:
    - config_env: override the config environment (e.g. 'TEST'); falls back to
      BFABRICPY_CONFIG_ENV env var or the default_config in the config file
    - config_file: override the config file path (default: ~/.bfabricpy.yml)
    """
    from bfabric import Bfabric

    sig = inspect.signature(fn)
    params = [param for name, param in sig.parameters.items() if name != "client"]

    _config_env_help = (
        "Override the config environment (e.g. 'TEST'). "
        "Falls back to BFABRICPY_CONFIG_ENV env var or the config file default."
    )
    _config_file_help = "Override the config file path (default: ~/.bfabricpy.yml)."
    try:
        import cyclopts  # pyright: ignore[reportMissingImports]

        parameter = cyclopts.Parameter  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
        config_env_annotation = Annotated[str | None, parameter(help=_config_env_help)]
        config_file_annotation = Annotated[Path | None, parameter(help=_config_file_help)]
    except ImportError:
        config_env_annotation = str | None
        config_file_annotation = Path | None

    kw_only = inspect.Parameter.KEYWORD_ONLY
    env_default = os.environ.get("BFABRICPY_CONFIG_ENV")
    params += [
        inspect.Parameter("config_env", kw_only, default=env_default, annotation=config_env_annotation),
        inspect.Parameter("config_file", kw_only, default=None, annotation=config_file_annotation),
    ]
    new_sig = sig.replace(parameters=params)

    @functools.wraps(fn)
    def wrapper(*args: object, **kwargs: object) -> T:
        if setup_logging:
            setup_script_logging()
        config_env = cast("str | None", kwargs.pop("config_env", None))
        config_file = cast("Path | None", kwargs.pop("config_file", None))
        if "client" in kwargs:
            client = cast("Bfabric", kwargs.pop("client"))
        else:
            try:
                client = Bfabric.connect(
                    config_file_path=config_file or DEFAULT_CONFIG_FILE,
                    config_file_env=config_env or "default",
                )
            except (ValueError, RuntimeError) as e:
                _report_and_exit(e)
        try:
            return fn(*args, client=client, **kwargs)  # type: ignore[arg-type]
        except RuntimeError as e:
            _report_and_exit(e)

    wrapper.__signature__ = new_sig  # type: ignore[reportAttributeAccessIssue]
    return wrapper


def _report_and_exit(error: Exception) -> NoReturn:
    """Reports ``error`` as a single stderr line and exits 1, keeping the traceback for DEBUG runs."""
    # Not logger.opt(exception=...): the DEBUG sink runs with loguru's default diagnose=True, which
    # annotates each frame with its locals — including whole environments passed to subprocesses.
    logger.debug(f"Traceback of the error reported below:\n{traceback.format_exc()}")
    print(f"Error: {error}", file=sys.stderr)
    sys.exit(1)


DEFAULT_THEME = Theme({"bfabric.hostname": "bold red"})


class HostnameHighlighter(RegexHighlighter):
    """Highlights hostnames in URLs."""

    base_style = "bfabric."
    highlights = [r"https://(?P<hostname>[^.]+)"]


_logging_configured = False
"""Whether this process configured its sinks. Process-local rather than an env var, which children
inherit — that made a subprocess skip setup and fall back to loguru's default DEBUG handler."""


def setup_script_logging(debug: bool = False) -> None:
    """Sets up the logging for the command line scripts."""
    global _logging_configured  # noqa: PLW0603 -- a one-shot guard is process-wide state by definition
    if _logging_configured:
        return

    packages = ["bfabric", "bfabric_scripts", "bfabric_app_runner", "__main__"]
    env_level = os.environ.get("BFABRICPY_LOG_LEVEL", "").upper()
    valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}

    if debug or env_level == "DEBUG":
        level = "DEBUG"
    elif env_level in ("OFF", "0"):
        level = "OFF"
    elif env_level in valid_levels:
        level = env_level
    else:
        level = "INFO"

    logger.remove()

    if level == "OFF":
        for package in packages:
            logger.disable(package)
    elif level == "DEBUG":
        for package in packages:
            _ = logger.add(sys.stderr, filter=package, level="DEBUG")
    else:
        for package in packages:
            _ = logger.add(sys.stderr, filter=package, level=level, format="{level} {message}")

    _logging_configured = True
