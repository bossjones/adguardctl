"""`adguardctl encryption` — TLS/encryption status (read-only in v1)."""

from __future__ import annotations

import typer

from adguardctl.render import emit_json, kv_table

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="TLS/encryption status.")


@app.command()
def show(ctx: typer.Context) -> None:
    """Show TLS/encryption status and certificate validity."""
    status = run_async(ctx, lambda a: a.encryption.status())
    if get_state(ctx).as_json:
        emit_json(status)
    else:
        kv_table("Encryption", status)
