"""Reusable interactive prompt helpers built on ``questionary``.

These wrap the recurring CLI pattern where a value may be supplied on the command line,
selected from a menu, or (optionally) typed as a new value not in the list. Interactive
prompts require a TTY; call sites in non-interactive contexts (pipes, CI) either pass an
explicit value or handle the ``None`` returned by :func:`resolve_choice`.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence
from typing import cast

import questionary


def is_interactive() -> bool:
    """Whether we can drive an interactive prompt (both ends attached to a terminal)."""
    return sys.stdin.isatty() and sys.stdout.isatty()


def select_choice(
    message: str,
    choices: Sequence[str],
    *,
    default: str | None = None,
    describe: Callable[[str], str] | None = None,
    search: bool = False,
) -> str | None:
    """Show an arrow-key menu of *choices* and return the picked value.

    Returns ``None`` if the user cancels (Ctrl-C / Esc). *default* pre-selects an entry and
    must be one of *choices* (pass ``None`` otherwise). *describe* maps each value to the label
    shown in the menu (e.g. to append a host or auth method); the return value is still the
    plain choice, never its label. With *search*, the user can type to filter the list live
    (arrow keys still work on the filtered subset) -- handy for long lists.
    """
    items: list[str | questionary.Choice]
    if describe is not None:
        items = [questionary.Choice(title=describe(choice), value=choice) for choice in choices]
    else:
        items = list(choices)
    # questionary's ``ask()`` is typed ``Any``; the prompt only ever yields a choice or None.
    # With the search filter on, j/k must stop being navigation keys (they'd be swallowed as
    # filter input) -- questionary raises otherwise. Arrow keys keep working regardless.
    return cast(
        "str | None",
        questionary.select(
            message, choices=items, default=default, use_search_filter=search, use_jk_keys=not search
        ).ask(),
    )


def select_or_input(message: str, choices: Sequence[str], *, default: str | None = None) -> str | None:
    """Offer *choices* as autocomplete suggestions but let the user type a value not in the list.

    Returns the entered value, or ``None`` if the user cancels or submits an empty answer.
    """
    items = list(choices)
    # Autocomplete only reveals suggestions on Tab, which isn't discoverable -- hint it, but only
    # when there actually are suggestions to complete (a first-time prompt with no choices wouldn't).
    prompt = f"{message} (Tab to autocomplete)" if items else message
    # questionary's ``ask()`` is typed ``Any``; the autocomplete prompt yields the text or None.
    answer = cast("str | None", questionary.autocomplete(prompt, choices=items, default=default or "").ask())
    return answer or None


def text_input(message: str, *, default: str = "") -> str | None:
    """Prompt for a free-text value, prefilled with *default*.

    Returns the entered text, or ``None`` if the user cancels or submits an empty answer.
    """
    # questionary's ``ask()`` is typed ``Any``; the text prompt yields the entered string or None.
    answer = cast("str | None", questionary.text(message, default=default).ask())
    return answer or None


def resolve_choice(
    value: str | None,
    choices: Sequence[str],
    *,
    message: str,
    allow_new: bool = False,
    default: str | None = None,
    describe: Callable[[str], str] | None = None,
    search: bool = False,
) -> str | None:
    """Resolve a choice from an explicit *value* or, failing that, an interactive prompt.

    * *value* given -> return it verbatim (the caller validates membership if it needs to).
    * else, no TTY -> return ``None`` (the caller reports the non-interactive case).
    * else, *allow_new* -> :func:`select_or_input` (pick a suggestion or type a new value).
    * else -> :func:`select_choice` (menu; *describe* labels each entry, *search* enables
      type-to-filter).
    """
    if value is not None:
        return value
    if not is_interactive():
        return None
    if allow_new:
        return select_or_input(message, choices, default=default)
    return select_choice(message, choices, default=default, describe=describe, search=search)
