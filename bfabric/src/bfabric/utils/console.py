from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from rich.highlighter import RegexHighlighter
from rich.theme import Theme

if TYPE_CHECKING:
    from collections.abc import Sequence

DEFAULT_THEME = Theme({"bfabric.hostname": "bold red"})


class HostnameHighlighter(RegexHighlighter):
    """Highlights hostnames in URLs."""

    base_style: ClassVar[str] = "bfabric."
    highlights: ClassVar[Sequence[str]] = [r"https://(?P<hostname>[^.]+)"]
