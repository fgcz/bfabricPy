from __future__ import annotations

import functools
import inspect
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, TypeVar, cast

from loguru import logger
from rich.highlighter import RegexHighlighter
from rich.theme import Theme

if TYPE_CHECKING:
    from collections.abc import Callable

T = TypeVar("T")

_DEFAULT_CONFIG_FILE = Path("~/.bfabricpy.yml")


def use_client(fn: Callable[..., T], setup_logging: bool = True) -> Callable[..., T]:
    """Decorator that injects a Bfabric client into a function.

    The client is automatically created using default configuration if not provided.
    If setup_logging is True (default), logging is set up using setup_script_logging.

    The decorator removes the 'client' parameter from the function signature and injects
    two optional keyword parameters into every decorated command:
    - config_env: override the config environment (e.g. 'TEST'); falls back to
      BFABRICPY_CONFIG_ENV env var or the default_config in the config file
    - config_file: override the config file path (default: ~/.bfabricpy.yml)
    """
    from bfabric import Bfabric

    # Get the original signature
    sig = inspect.signature(fn)

    # Create new parameters without the client parameter, then append config overrides
    params = [param for name, param in sig.parameters.items() if name != "client"]

    # Create a new signature without the client parameter, then append config overrides
    _config_env_help = (
        "Override the config environment (e.g. 'TEST'). "
        "Falls back to BFABRICPY_CONFIG_ENV env var or the config file default."
    )
    try:
        import cyclopts  # pyright: ignore[reportMissingImports]

        config_env_annotation = Annotated[
            str | None,
            cyclopts.Parameter(  # pyright: ignore[reportUnknownMemberType]
                help=_config_env_help,
            ),
        ]
        config_file_annotation = Annotated[
            Path | None,
            cyclopts.Parameter(  # pyright: ignore[reportUnknownMemberType]
                help="Override the config file path (default: ~/.bfabricpy.yml)."
            ),
        ]
    except ImportError:
        config_env_annotation = str | None
        config_file_annotation = Path | None

    params += [
        inspect.Parameter(
            "config_env",
            inspect.Parameter.KEYWORD_ONLY,
            default=os.environ.get("BFABRICPY_CONFIG_ENV"),
            annotation=config_env_annotation,
        ),
        inspect.Parameter(
            "config_file",
            inspect.Parameter.KEYWORD_ONLY,
            default=None,
            annotation=config_file_annotation,
        ),
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
            client = Bfabric.connect(
                config_file_path=config_file or _DEFAULT_CONFIG_FILE,
                config_file_env=config_env or "default",
            )
        return fn(*args, client=client, **kwargs)  # type: ignore[arg-type]

    # Update the signature of the wrapper
    wrapper.__signature__ = new_sig  # type: ignore[reportAttributeAccessIssue]
    return wrapper


DEFAULT_THEME = Theme({"bfabric.hostname": "bold red"})


class HostnameHighlighter(RegexHighlighter):
    """Highlights hostnames in URLs."""

    base_style = "bfabric."
    highlights = [r"https://(?P<hostname>[^.]+)"]


def setup_script_logging(debug: bool = False) -> None:
    """Sets up the logging for the command line scripts."""
    setup_flag_key = "BFABRICPY_SCRIPT_LOGGING_SETUP"
    if os.environ.get(setup_flag_key, "0") == "1":
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

    os.environ[setup_flag_key] = "1"
