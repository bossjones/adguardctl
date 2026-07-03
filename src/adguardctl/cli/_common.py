"""Shared CLI state and the async command runner."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, TypeVar

import typer
from pydantic import ValidationError

from adguardctl.api import AdGuard
from adguardctl.config import load_settings
from adguardctl.exceptions import AdGuardError
from adguardctl.render import err_console

T = TypeVar("T")


@dataclass
class AppState:
    """Global CLI state populated by the root callback."""

    profile: str | None = None
    config_path: Path | None = None
    overrides: dict[str, Any] = field(default_factory=dict)
    as_json: bool = False


def get_state(ctx: typer.Context) -> AppState:
    """Return the :class:`AppState` attached to the typer context."""
    if not isinstance(ctx.obj, AppState):
        ctx.obj = AppState()
    return ctx.obj


def run_async(
    ctx: typer.Context,
    func: Callable[[AdGuard], Awaitable[T]],
) -> T:
    """Resolve settings, run ``func`` against an :class:`AdGuard`, return its result.

    Connection/validation failures are converted into a friendly stderr message
    and a non-zero exit code.
    """
    state = get_state(ctx)

    async def _main() -> T:
        settings = load_settings(
            profile=state.profile,
            config_path=state.config_path,
            overrides=state.overrides,
        )
        async with AdGuard.from_settings(settings) as adguard:
            return await func(adguard)

    try:
        return asyncio.run(_main())
    except ValidationError as exc:
        err_console.print(
            "[red]Error:[/red] no AdGuard Home host configured "
            "(set --host, AGH_HOST, or a config profile)."
        )
        raise typer.Exit(code=2) from exc
    except AdGuardError as exc:
        err_console.print(f"[red]Error:[/red] {exc.message}")
        raise typer.Exit(code=1) from exc
