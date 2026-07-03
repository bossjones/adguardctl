"""`adguardctl filters` — filter-list subscription management."""

from __future__ import annotations

import typer

from adguardctl.render import console, emit_json, list_table, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="Manage filter-list subscriptions.")

_COLUMNS = [
    ("ID", "id"),
    ("Name", "name"),
    ("URL", "url"),
    ("Rules", "rules_count"),
    ("Enabled", "enabled"),
]


@app.command()
def show(ctx: typer.Context) -> None:
    """Show filter lists (block and allow) and filtering state."""
    status = run_async(ctx, lambda a: a.filters.status())
    if get_state(ctx).as_json:
        emit_json(status)
        return
    list_table("Blocklists", status.filters, _COLUMNS, empty_message="No blocklists.")
    list_table(
        "Allowlists", status.whitelist_filters, _COLUMNS, empty_message="No allowlists."
    )


@app.command()
def add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Display name for the list."),
    url: str = typer.Argument(..., help="URL of the filter list."),
    allowlist: bool = typer.Option(
        False, help="Add to allowlists instead of blocklists."
    ),
) -> None:
    """Add a filter-list subscription."""
    run_async(ctx, lambda a: a.filters.add_url(name=name, url=url, whitelist=allowlist))
    success(f"Filter list '{name}' added.")


@app.command()
def remove(
    ctx: typer.Context,
    url: str = typer.Argument(..., help="URL of the filter list to remove."),
    allowlist: bool = typer.Option(False, help="Remove from allowlists instead."),
) -> None:
    """Remove a filter-list subscription."""
    run_async(ctx, lambda a: a.filters.remove_url(url=url, whitelist=allowlist))
    success("Filter list removed.")


@app.command()
def refresh(
    ctx: typer.Context,
    allowlist: bool = typer.Option(False, help="Refresh allowlists instead."),
) -> None:
    """Refresh filter lists from their sources."""
    updated = run_async(ctx, lambda a: a.filters.refresh(whitelist=allowlist))
    console.print(f"Updated {updated} list(s).")
