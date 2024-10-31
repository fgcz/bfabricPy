import os
import sys

from loguru import logger
from rich.highlighter import RegexHighlighter
from rich.theme import Theme


class HostnameHighlighter(RegexHighlighter):
    """Highlights hostnames in URLs."""

    base_style = "bfabric."
    highlights = [r"https://(?P<hostname>[^.]+)"]


DEFAULT_THEME = Theme({"bfabric.hostname": "bold red"})


def setup_script_logging(debug: bool = False) -> None:
    """Sets up the logging for the command line scripts."""
    setup_flag_key = "BFABRICPY_SCRIPT_LOGGING_SETUP"
    if os.environ.get(setup_flag_key, "0") == "1":
        return
    logger.remove()
    if not (debug or os.environ.get("BFABRICPY_DEBUG")):
        logger.add(sys.stderr, filter="bfabric", level="INFO", format="{level} {message}")
        logger.add(sys.stderr, filter="bfabric_scripts", level="INFO", format="{level} {message}")
        logger.add(sys.stderr, filter="__main__", level="INFO", format="{level} {message}")
    else:
        logger.add(sys.stderr, filter="bfabric", level="DEBUG")
        logger.add(sys.stderr, filter="bfabric_scripts", level="DEBUG")
        logger.add(sys.stderr, filter="__main__", level="DEBUG")
    os.environ[setup_flag_key] = "1"
