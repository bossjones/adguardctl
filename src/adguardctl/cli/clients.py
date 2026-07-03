"""`adguardctl clients` — persistent client management (CRUD)."""

from __future__ import annotations

import typer

from adguardctl.models import Client
from adguardctl.render import emit_json, list_table, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="Manage persistent clients.")


@app.command(name="list")
def list_clients(ctx: typer.Context) -> None:
    """List persistent and auto-discovered clients."""
    resp = run_async(ctx, lambda a: a.clients.list())
    if get_state(ctx).as_json:
        emit_json(resp)
        return
    list_table(
        "Persistent clients",
        resp.clients,
        [("Name", "name"), ("IDs", "ids"), ("Tags", "tags")],
        empty_message="No persistent clients.",
    )
    list_table(
        "Auto clients",
        resp.auto_clients,
        [("Name", "name"), ("IP", "ip"), ("Source", "source")],
        empty_message="No auto clients.",
    )


@app.command()
def add(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Client name."),
    ids: list[str] = typer.Argument(
        ..., help="Client identifiers (IP/CIDR/MAC/ClientID)."
    ),
) -> None:
    """Add a persistent client."""
    client = Client(name=name, ids=ids)
    run_async(ctx, lambda a: a.clients.add(client))
    success(f"Client '{name}' added.")


@app.command()
def delete(
    ctx: typer.Context,
    name: str = typer.Argument(..., help="Client name to delete."),
) -> None:
    """Delete a persistent client."""
    run_async(ctx, lambda a: a.clients.delete(name))
    success(f"Client '{name}' deleted.")
