"""`adguardctl access` — access lists / allowlists (read + mutate)."""

from __future__ import annotations

import typer

from adguardctl.api import AdGuard
from adguardctl.models import AccessList
from adguardctl.render import bullet_list, emit_json, success

from ._common import get_state, run_async

app = typer.Typer(
    no_args_is_help=True, help="Manage access lists (allow/disallow/block)."
)


@app.command()
def show(ctx: typer.Context) -> None:
    """Show allowed/disallowed clients and blocked hosts."""
    access = run_async(ctx, lambda a: a.access.list())
    if get_state(ctx).as_json:
        emit_json(access)
        return
    bullet_list("Allowed clients", access.allowed_clients)
    bullet_list("Disallowed clients", access.disallowed_clients)
    bullet_list("Blocked hosts", access.blocked_hosts)


@app.command(name="block-host")
def block_host(
    ctx: typer.Context,
    host: str = typer.Argument(..., help="Hostname to block."),
) -> None:
    """Add a hostname to the blocked-hosts list."""

    async def _mutate(a: AdGuard) -> AccessList:
        access = await a.access.list()
        if host not in access.blocked_hosts:
            access.blocked_hosts.append(host)
            await a.access.set(access)
        return access

    run_async(ctx, _mutate)
    success(f"Host '{host}' blocked.")


@app.command(name="unblock-host")
def unblock_host(
    ctx: typer.Context,
    host: str = typer.Argument(..., help="Hostname to unblock."),
) -> None:
    """Remove a hostname from the blocked-hosts list."""

    async def _mutate(a: AdGuard) -> AccessList:
        access = await a.access.list()
        if host in access.blocked_hosts:
            access.blocked_hosts.remove(host)
            await a.access.set(access)
        return access

    run_async(ctx, _mutate)
    success(f"Host '{host}' unblocked.")
