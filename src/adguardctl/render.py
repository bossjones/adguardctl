"""Output helpers: rich tables by default, machine-readable JSON on demand."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

console = Console()
err_console = Console(stderr=True)


def _to_serializable(data: Any) -> Any:
    """Convert models (or lists of them) to plain JSON-serializable data."""
    if isinstance(data, BaseModel):
        return data.model_dump(mode="json")
    if isinstance(data, list):
        return [_to_serializable(item) for item in data]
    if isinstance(data, dict):
        return {key: _to_serializable(value) for key, value in data.items()}
    return data


def emit_json(data: Any) -> None:
    """Print ``data`` as indented JSON to stdout."""
    console.print_json(json.dumps(_to_serializable(data)))


def kv_table(title: str, model: BaseModel) -> None:
    """Render a single model as a two-column key/value table."""
    table = Table(title=title, show_header=False, title_justify="left")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value", overflow="fold")
    for key, value in model.model_dump(mode="json").items():
        table.add_row(key, _format_value(value))
    console.print(table)


def list_table(
    title: str,
    rows: Sequence[BaseModel],
    columns: list[tuple[str, str]],
    *,
    empty_message: str = "No entries.",
) -> None:
    """Render a list of models as a table.

    Args:
        title: Table title.
        rows: The model instances to render.
        columns: ``(header, attribute_name)`` pairs.
        empty_message: Message shown when ``rows`` is empty.
    """
    if not rows:
        console.print(f"[dim]{empty_message}[/dim]")
        return
    table = Table(title=title, title_justify="left")
    for header, _ in columns:
        table.add_column(header)
    for row in rows:
        table.add_row(*[_format_value(getattr(row, attr)) for _, attr in columns])
    console.print(table)


def bullet_list(title: str, items: list[str], *, empty_message: str = "None.") -> None:
    """Render a simple bulleted list of strings."""
    console.print(f"[bold]{title}[/bold]")
    if not items:
        console.print(f"  [dim]{empty_message}[/dim]")
        return
    for item in items:
        console.print(f"  • {item}")


def success(message: str) -> None:
    """Print a success message."""
    console.print(f"[green]✓[/green] {message}")


def _format_value(value: Any) -> str:
    if isinstance(value, bool):
        return "[green]yes[/green]" if value else "[red]no[/red]"
    if isinstance(value, list):
        return ", ".join(str(item) for item in value) if value else "-"
    if value is None or value == "":
        return "-"
    return str(value)
