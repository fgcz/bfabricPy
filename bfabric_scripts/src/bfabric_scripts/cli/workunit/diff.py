from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar

from rich.console import Console
from rich.markup import escape
from rich.table import Table

from bfabric import Bfabric
from bfabric.entities import Workunit
from bfabric.entities.core.uri import EntityUri
from bfabric.utils.cli_integration import use_client

if TYPE_CHECKING:
    from collections.abc import Iterable

    from bfabric.entities import Resource

_MISSING = "—"

KeyT = TypeVar("KeyT", str, tuple[str, str])


def _text(value: object) -> str:
    """Coerce a raw entity field value to a display string (``None`` -> empty)."""
    return "" if value is None else str(value)


@dataclass(frozen=True)
class DiffRow:
    """A single comparison row: a key and its value on each side (``None`` = absent on that side)."""

    key: tuple[str, ...]
    left: str | None
    right: str | None

    @property
    def differs(self) -> bool:
        return self.left != self.right


def diff_rows(left: dict[KeyT, str], right: dict[KeyT, str]) -> list[DiffRow]:
    """Compare two dicts, one row per key in the sorted union of both key sets."""
    rows: list[DiffRow] = []
    for key in sorted(set(left) | set(right)):
        key_tuple = key if isinstance(key, tuple) else (key,)
        rows.append(DiffRow(key=tuple(str(k) for k in key_tuple), left=left.get(key), right=right.get(key)))
    return rows


def _resolve_workunit(reference: str, *, client: Bfabric) -> Workunit:
    """Resolve a workunit reference (entity URI or numeric ID) to a ``Workunit``."""
    try:
        uri = EntityUri(reference)
    except ValueError:
        uri = None

    if uri is not None:
        if uri.components.entity_type != "workunit":
            raise ValueError(f"Not a workunit URI: {reference}")
        workunit = client.reader.read_uri(uri, expected_type=Workunit)
    elif reference.isdigit():
        workunit = client.reader.read_id(Workunit, int(reference))
    else:
        raise ValueError(f"Not a workunit URI or numeric ID: {reference}")

    if workunit is None:
        raise ValueError(f"Workunit not found: {reference}")
    return workunit


def _fields(workunit: Workunit) -> dict[str, str]:
    """Scalar fields worth comparing between two workunits."""
    application = workunit.application
    container = workunit.container
    input_dataset = workunit.input_dataset
    return {
        "name": _text(workunit.get("name")),
        "status": _text(workunit.get("status")),
        "application": f"A{application.id} {_text(application.get('name'))}".strip(),
        "container": f"{container.classname} {container.id}",
        "input dataset": str(input_dataset.id) if input_dataset is not None else _MISSING,
    }


def _parameters(workunit: Workunit) -> dict[tuple[str, str], str]:
    """Parameters keyed by ``(context, key)`` so identically-named params in different contexts stay distinct."""
    return {(_text(parameter.get("context")), parameter.key): parameter.value for parameter in workunit.parameters}


def _resource_map(resources: Iterable[Resource]) -> dict[str, str]:
    """Map each resource name to its checksum (``""`` when unknown) for presence/content comparison."""
    result: dict[str, str] = {}
    for resource in resources:
        name = _text(resource.get("name")) or f"resource {resource.id}"
        result[name] = _text(resource.get("filechecksum"))
    return result


def render_section(
    console: Console,
    title: str,
    key_headers: list[str],
    rows: list[DiffRow],
    labels: tuple[str, str],
    only_diff: bool,
) -> None:
    """Render one comparison section as a rich table, styling and marking rows that differ."""
    shown = [row for row in rows if row.differs] if only_diff else rows
    console.print(f"[bold]{title}[/bold]")
    if not shown:
        console.print("  (no differences)" if rows else "  (empty)")
        console.print()
        return

    table = Table(show_header=True, header_style="bold")
    for header in key_headers:
        table.add_column(header)
    table.add_column(labels[0])
    table.add_column(labels[1])
    table.add_column("")

    for row in shown:
        style = "yellow" if row.differs else None
        # Escape cell text: entity data (names, param values, checksums) may contain rich-markup
        # characters, which would otherwise misrender or raise MarkupError (e.g. a value of "[/]").
        table.add_row(
            *(escape(part) for part in row.key),
            escape(row.left) if row.left is not None else _MISSING,
            escape(row.right) if row.right is not None else _MISSING,
            "≠" if row.differs else "",
            style=style,
        )
    console.print(table)
    console.print()


@use_client
def cmd_workunit_diff(workunit1: str, workunit2: str, *, client: Bfabric, only_diff: bool = False) -> None:
    """Compare two workunits (name, parameters, resources, and key fields) side by side.

    :param workunit1: first workunit — an entity URI or a numeric ID
    :param workunit2: second workunit — an entity URI or a numeric ID
    :param only_diff: show only fields/parameters/resources that differ
    """
    wu1 = _resolve_workunit(workunit1, client=client)
    wu2 = _resolve_workunit(workunit2, client=client)

    labels = (f"WU{wu1.id}", f"WU{wu2.id}")
    console = Console()
    console.print(f"[bold]Workunit diff: {labels[0]} vs {labels[1]}[/bold]\n")

    render_section(console, "Fields", ["Field"], diff_rows(_fields(wu1), _fields(wu2)), labels, only_diff)
    render_section(
        console, "Parameters", ["Context", "Key"], diff_rows(_parameters(wu1), _parameters(wu2)), labels, only_diff
    )
    render_section(
        console,
        "Output resources",
        ["Resource"],
        diff_rows(_resource_map(wu1.resources), _resource_map(wu2.resources)),
        labels,
        only_diff,
    )
    render_section(
        console,
        "Input resources",
        ["Resource"],
        diff_rows(_resource_map(wu1.input_resources), _resource_map(wu2.input_resources)),
        labels,
        only_diff,
    )
