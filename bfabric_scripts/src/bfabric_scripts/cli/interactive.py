"""Interactive prompt helpers built on ``questionary``.

Prompts require a TTY; callers guard with :func:`is_interactive` and handle the ``None``
returned on cancel (or empty input, where noted).
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from typing import cast

import questionary


def is_interactive() -> bool:
    """Whether both stdin and stdout are attached to a terminal."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def select_choice(
    message: str,
    choices: Sequence[str],
    *,
    default: str | None = None,
    describe: Callable[[str], str] | None = None,
    search: bool = False,
) -> str | None:
    """Arrow-key menu over *choices*; returns the picked value or ``None`` on cancel.

    *default* must be one of *choices*. *describe* maps a value to its display label. *search*
    lets the user type to filter.
    """
    items: list[str | questionary.Choice]
    if describe is not None:
        items = [questionary.Choice(title=describe(choice), value=choice) for choice in choices]
    else:
        items = list(choices)
    return cast(
        "str | None",
        questionary.select(message, choices=items, default=default, use_search_filter=search, use_jk_keys=False).ask(),
    )


def select_or_input(message: str, choices: Sequence[str], *, default: str | None = None) -> str | None:
    """Autocomplete over *choices* that also accepts a value not in the list; ``None`` on cancel/empty."""
    items = list(choices)
    prompt = f"{message} (Tab to autocomplete)" if items else message
    answer = cast("str | None", questionary.autocomplete(prompt, choices=items, default=default or "").ask())
    return answer or None


def text_input(message: str, *, default: str = "") -> str | None:
    """Free-text prompt prefilled with *default*; ``None`` on cancel/empty."""
    answer = cast("str | None", questionary.text(message, default=default).ask())
    return answer or None


def confirm(message: str, *, default: bool = False) -> bool | None:
    """Yes/no prompt; ``True``/``False``, or ``None`` on cancel (distinct from a declined "no")."""
    return cast("bool | None", questionary.confirm(message, default=default).ask())
