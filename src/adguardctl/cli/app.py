"""Root typer application for adguardctl."""

from __future__ import annotations

from pathlib import Path

import typer

from adguardctl import __version__
from adguardctl.render import console, emit_json, kv_table

from . import (
    access,
    clients,
    dns,
    encryption,
    filters,
    querylog,
    rewrites,
    rules,
    settings,
    stats,
)
from ._common import AppState, get_state, run_async
from .export import export_command

app = typer.Typer(
    no_args_is_help=True,
    help="Async CLI for managing an AdGuard Home instance.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

app.add_typer(settings.app, name="settings")
app.add_typer(dns.app, name="dns")
app.add_typer(encryption.app, name="encryption")
app.add_typer(clients.app, name="clients")
app.add_typer(rewrites.app, name="rewrites")
app.add_typer(access.app, name="access")
app.add_typer(filters.app, name="filters")
app.add_typer(rules.app, name="rules")
app.add_typer(querylog.app, name="querylog")
app.add_typer(stats.app, name="stats")

app.command(name="export")(export_command)


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"adguardctl {__version__}")
        raise typer.Exit


@app.callback()
def main_callback(  # noqa: PLR0913
    ctx: typer.Context,
    host: str = typer.Option(
        None, "--host", "-H", help="AdGuard Home host.", envvar="AGH_HOST"
    ),
    port: int = typer.Option(None, "--port", "-p", help="API port.", envvar="AGH_PORT"),
    username: str = typer.Option(
        None, "--username", "-u", help="Username.", envvar="AGH_USERNAME"
    ),
    password: str = typer.Option(
        None, "--password", help="Password.", envvar="AGH_PASSWORD"
    ),
    tls: bool = typer.Option(None, "--tls/--no-tls", help="Use https."),
    insecure: bool = typer.Option(
        False, "--insecure", help="Do not verify TLS certificates."
    ),
    timeout: float = typer.Option(None, "--timeout", help="Request timeout (seconds)."),
    profile: str = typer.Option(
        None, "--profile", help="Config profile name.", envvar="AGH_PROFILE"
    ),
    config_path: Path = typer.Option(
        None, "--config", help="Path to the config TOML file."
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit machine-readable JSON instead of tables."
    ),
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show version.",
    ),
) -> None:
    """Resolve global options into shared CLI state."""
    overrides: dict[str, object] = {
        "host": host,
        "port": port,
        "username": username,
        "password": password,
        "tls": tls,
        "verify_ssl": (False if insecure else None),
        "request_timeout": timeout,
    }
    ctx.obj = AppState(
        profile=profile,
        config_path=config_path,
        overrides=overrides,
        as_json=json_output,
    )


@app.command()
def status(ctx: typer.Context) -> None:
    """Show a quick server status summary (alias for `settings show`)."""
    result = run_async(ctx, lambda a: a.settings.status())
    if get_state(ctx).as_json:
        emit_json(result)
    else:
        kv_table("AdGuard Home status", result)


def main() -> None:
    """Console-script entry point."""
    app()


if __name__ == "__main__":
    main()
