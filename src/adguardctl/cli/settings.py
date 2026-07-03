"""`adguardctl settings` — protection, safe browsing, parental, safe search."""

from __future__ import annotations

from enum import Enum

import typer

from adguardctl.render import emit_json, kv_table, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="General settings and protection toggles.")


class Toggle(str, Enum):
    """On/off toggle for protection features."""

    on = "on"
    off = "off"


@app.command()
def show(ctx: typer.Context) -> None:
    """Show server status and protection state."""
    status = run_async(ctx, lambda a: a.settings.status())
    if get_state(ctx).as_json:
        emit_json(status)
    else:
        kv_table("AdGuard Home status", status)


@app.command()
def protection(
    ctx: typer.Context,
    action: Toggle,
    duration: int = typer.Option(
        None, help="When turning off, re-enable automatically after N seconds."
    ),
) -> None:
    """Enable or disable protection (optionally for a duration)."""
    enabled = action is Toggle.on
    run_async(
        ctx,
        lambda a: a.settings.set_protection(enabled=enabled, duration=duration),
    )
    success(f"Protection turned {action.value}.")


@app.command()
def safebrowsing(ctx: typer.Context, action: Toggle) -> None:
    """Enable or disable safe browsing."""
    run_async(ctx, lambda a: a.settings.set_safebrowsing(enabled=action is Toggle.on))
    success(f"Safe browsing turned {action.value}.")


@app.command()
def parental(ctx: typer.Context, action: Toggle) -> None:
    """Enable or disable parental control."""
    run_async(ctx, lambda a: a.settings.set_parental(enabled=action is Toggle.on))
    success(f"Parental control turned {action.value}.")


@app.command()
def safesearch(ctx: typer.Context) -> None:
    """Show safe-search settings."""
    config = run_async(ctx, lambda a: a.settings.safesearch())
    if get_state(ctx).as_json:
        emit_json(config)
    else:
        kv_table("Safe search", config)


@app.command(name="stats-config")
def stats_config(ctx: typer.Context) -> None:
    """Show statistics configuration."""
    config = run_async(ctx, lambda a: a.settings.stats_config())
    if get_state(ctx).as_json:
        emit_json(config)
    else:
        kv_table("Statistics config", config)
