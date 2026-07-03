"""`adguardctl querylog` — read and manage the query log."""

from __future__ import annotations

from enum import Enum

import typer
from rich.table import Table

from adguardctl.models import QueryLog
from adguardctl.render import console, emit_json, kv_table, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="Read and manage the query log.")


class ResponseStatus(str, Enum):
    """Query-log response-status filter values."""

    all = "all"
    filtered = "filtered"
    blocked = "blocked"
    blocked_safebrowsing = "blocked_safebrowsing"
    blocked_parental = "blocked_parental"
    whitelisted = "whitelisted"
    rewritten = "rewritten"
    safe_search = "safe_search"
    processed = "processed"


@app.command()
def show(
    ctx: typer.Context,
    response_status: ResponseStatus = typer.Option(
        ResponseStatus.all, "--response-status", "-s", help="Filter by response status."
    ),
    search: str = typer.Option(None, "--search", help="Domain or client IP to search."),
    limit: int = typer.Option(50, "--limit", "-n", help="Max entries to return."),
    older_than: str = typer.Option(
        None, "--older-than", help="Return entries older than this timestamp."
    ),
) -> None:
    """Show query-log entries (most recent first)."""
    log = run_async(
        ctx,
        lambda a: a.querylog.get(
            response_status=response_status.value,
            search=search,
            limit=limit,
            older_than=older_than,
        ),
    )
    if get_state(ctx).as_json:
        emit_json(log)
    else:
        _render_log(log)


@app.command()
def config(ctx: typer.Context) -> None:
    """Show query-log configuration."""
    cfg = run_async(ctx, lambda a: a.querylog.config())
    if get_state(ctx).as_json:
        emit_json(cfg)
    else:
        kv_table("Query-log config", cfg)


@app.command()
def clear(ctx: typer.Context) -> None:
    """Clear the query log."""
    run_async(ctx, lambda a: a.querylog.clear())
    success("Query log cleared.")


def _render_log(log: QueryLog) -> None:
    if not log.data:
        console.print("[dim]No query-log entries.[/dim]")
        return
    table = Table(title="Query log", title_justify="left")
    for header in ("Time", "Client", "Domain", "Type", "Status", "Reason"):
        table.add_column(header, overflow="fold")
    for item in log.data:
        table.add_row(
            item.time,
            item.client,
            item.question.host,
            item.question.type,
            item.status,
            item.reason,
        )
    console.print(table)
