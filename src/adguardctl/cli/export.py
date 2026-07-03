"""`adguardctl export` — dump the full raw config as JSON."""

from __future__ import annotations

import json
from pathlib import Path

import typer

from adguardctl.render import emit_json, success

from ._common import run_async


def export_command(
    ctx: typer.Context,
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Write the JSON export to this file instead of stdout.",
    ),
) -> None:
    """Export the full raw configuration (all areas) as JSON.

    Unlike the per-area commands, this preserves every field the API returns
    (nothing is dropped by the typed models), which makes it suitable for
    building a seed config.
    """
    data = run_async(ctx, lambda a: a.export())
    if output is not None:
        output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
        success(f"Wrote config export to {output}")
    else:
        emit_json(data)
