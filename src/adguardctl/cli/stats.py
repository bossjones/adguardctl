"""`adguardctl stats` — statistics reading and reset."""

from __future__ import annotations

import typer

from adguardctl.render import emit_json, kv_table, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="Statistics.")


@app.command()
def show(ctx: typer.Context) -> None:
    """Show dashboard statistics."""
    stats = run_async(ctx, lambda a: a.stats.get())
    if get_state(ctx).as_json:
        emit_json(stats)
    else:
        kv_table("Statistics", stats)


@app.command()
def reset(ctx: typer.Context) -> None:
    """Reset all statistics."""
    run_async(ctx, lambda a: a.stats.reset())
    success("Statistics reset.")
