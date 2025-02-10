import functools
import inspect
from typing import Any

from rich.highlighter import RegexHighlighter
from rich.theme import Theme

from bfabric import Bfabric
from bfabric.cli_formatting import setup_script_logging


def use_client(fn: Any, setup_logging: bool = True) -> Any:
    """Decorator that injects a Bfabric client into a function.

    The client is automatically created using default configuration if not provided.
    If setup_logging is True (default), logging is set up using setup_script_logging.
    """
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
        client = kwargs.pop("client") if "client" in kwargs else Bfabric.from_config()
        return fn(*args, **kwargs, client=client)

    # Update the signature of the wrapper
    wrapper.__signature__ = new_sig
    return wrapper


DEFAULT_THEME = Theme({"bfabric.hostname": "bold red"})


class HostnameHighlighter(RegexHighlighter):
    """Highlights hostnames in URLs."""

    base_style = "bfabric."
    highlights = [r"https://(?P<hostname>[^.]+)"]
