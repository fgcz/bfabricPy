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
    logger.remove()
    if not debug:
        logger.add(sys.stderr, filter="bfabric", level="INFO", format="{level} {message}")
    else:
        logger.add(sys.stderr, filter="bfabric", level="DEBUG")
