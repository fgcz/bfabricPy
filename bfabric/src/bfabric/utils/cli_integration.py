import functools
import inspect
import os
import sys
from typing import Any

from loguru import logger
from rich.highlighter import RegexHighlighter
from rich.theme import Theme


def use_client(fn: Any, setup_logging: bool = True) -> Any:
    """Decorator that injects a Bfabric client into a function.

    The client is automatically created using default configuration if not provided.
    If setup_logging is True (default), logging is set up using setup_script_logging.
    """
    from bfabric import Bfabric

    # Get the original signature
    sig = inspect.signature(fn)

    # Create new parameters without the client parameter
    params = [param for name, param in sig.parameters.items() if name != "client"]

    # Create a new signature without the client parameter
    new_sig = sig.replace(parameters=params)

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if setup_logging:
            setup_script_logging()
        client = kwargs.pop("client") if "client" in kwargs else Bfabric.connect()
        return fn(*args, **kwargs, client=client)

    # Update the signature of the wrapper
    wrapper.__signature__ = new_sig
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
    logger.remove()
    packages = ["bfabric", "bfabric_scripts", "bfabric_app_runner", "__main__"]
    if not (debug or os.environ.get("BFABRICPY_DEBUG")):
        for package in packages:
            logger.add(sys.stderr, filter=package, level="INFO", format="{level} {message}")
    else:
        for package in packages:
            logger.add(sys.stderr, filter=package, level="DEBUG")
    os.environ[setup_flag_key] = "1"
