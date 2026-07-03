"""`adguardctl rules` — user-defined custom filtering rules."""

from __future__ import annotations

import sys

import typer

from adguardctl.render import bullet_list, emit_json, success

from ._common import get_state, run_async

app = typer.Typer(no_args_is_help=True, help="Manage custom filtering rules.")


@app.command()
def show(ctx: typer.Context) -> None:
    """Show the current user-defined rules."""
    rules = run_async(ctx, lambda a: a.rules.get())
    if get_state(ctx).as_json:
        emit_json(rules)
    else:
        bullet_list("Custom rules", rules, empty_message="No custom rules.")


@app.command(name="set")
def set_rules(
    ctx: typer.Context,
    file: typer.FileText = typer.Option(
        None,
        "--file",
        "-f",
        help="Read rules from a file (one per line); use '-' for stdin.",
    ),
    rule: list[str] = typer.Option(
        None, "--rule", "-r", help="A rule to set (repeatable)."
    ),
) -> None:
    """Replace all custom rules from --file/stdin or repeated --rule options."""
    if file is not None:
        source = sys.stdin if file is sys.stdin else file
        rules = [line.strip() for line in source if line.strip()]
    else:
        rules = list(rule or [])
    run_async(ctx, lambda a: a.rules.set(rules))
    success(f"Set {len(rules)} custom rule(s).")
