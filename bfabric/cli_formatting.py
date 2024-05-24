from rich.highlighter import RegexHighlighter
from rich.theme import Theme


class HostnameHighlighter(RegexHighlighter):
    """Highlights hostnames in URLs."""

    base_style = "bfabric."
    highlights = [r"https://(?P<hostname>[^.]+)"]


DEFAULT_THEME = Theme({"bfabric.hostname": "bold red"})
