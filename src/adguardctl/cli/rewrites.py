"""`adguardctl rewrites` — DNS rewrite management (CRUD)."""

from __future__ import annotations

import typer

from adguardctl.render import emit_json, list_table, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="Manage DNS rewrites.")


@app.command(name="list")
def list_rewrites(ctx: typer.Context) -> None:
    """List DNS rewrite rules."""
    rules = run_async(ctx, lambda a: a.rewrites.list())
    if get_state(ctx).as_json:
        emit_json(rules)
    else:
        list_table(
            "DNS rewrites",
            rules,
            [("Domain", "domain"), ("Answer", "answer"), ("Enabled", "enabled")],
            empty_message="No rewrites.",
        )


@app.command()
def add(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain (may contain wildcards)."),
    answer: str = typer.Argument(..., help="IP address or hostname to return."),
) -> None:
    """Add a DNS rewrite rule."""
    run_async(ctx, lambda a: a.rewrites.add(domain, answer))
    success(f"Rewrite '{domain} -> {answer}' added.")


@app.command()
def delete(
    ctx: typer.Context,
    domain: str = typer.Argument(..., help="Domain of the rule to delete."),
    answer: str = typer.Argument(..., help="Answer of the rule to delete."),
) -> None:
    """Delete a DNS rewrite rule."""
    run_async(ctx, lambda a: a.rewrites.delete(domain, answer))
    success(f"Rewrite '{domain} -> {answer}' deleted.")
