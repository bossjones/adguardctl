"""`adguardctl dns` — DNS settings (read + upstream test + cache clear)."""

from __future__ import annotations

import typer

from adguardctl.render import console, emit_json, kv_table, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="DNS settings and diagnostics.")


@app.command()
def show(ctx: typer.Context) -> None:
    """Show DNS configuration (upstreams, cache, DNSSEC, ...)."""
    info = run_async(ctx, lambda a: a.dns.info())
    if get_state(ctx).as_json:
        emit_json(info)
    else:
        kv_table("DNS configuration", info)


@app.command(name="test-upstream")
def check_upstream(
    ctx: typer.Context,
    upstream: list[str] = typer.Argument(..., help="Upstream DNS server(s) to test."),
) -> None:
    """Test one or more upstream DNS servers."""
    results = run_async(ctx, lambda a: a.dns.test_upstreams(upstream_dns=upstream))
    if get_state(ctx).as_json:
        emit_json(results)
    else:
        for server, result in results.items():
            console.print(f"{server}: {result or '[green]OK[/green]'}")


@app.command(name="cache-clear")
def cache_clear(ctx: typer.Context) -> None:
    """Clear the DNS cache."""
    run_async(ctx, lambda a: a.dns.cache_clear())
    success("DNS cache cleared.")
