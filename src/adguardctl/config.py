"""Layered configuration for adguardctl.

Connection settings are resolved with the following precedence (highest wins):

1. CLI flags (``--host``, ``--username``, ...)
2. Environment variables (``AGH_HOST``, ``AGH_USERNAME``, ...)
3. A TOML config file (default ``~/.config/adguardctl/config.toml``)

The TOML file supports named profiles::

    default_profile = "home"

    [profiles.home]
    host = "adguard.local"
    port = 80
    username = "admin"
    password = "secret"

    [profiles.work]
    host = "10.0.0.2"

A file with bare top-level keys (no ``[profiles.*]`` tables) is treated as the
implicit ``default`` profile.
"""

from __future__ import annotations

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "adguardctl" / "config.toml"

_ENV_PREFIX = "AGH_"
# Maps a Settings field to its environment variable (without prefix handling).
_ENV_FIELDS: dict[str, str] = {
    "host": "AGH_HOST",
    "port": "AGH_PORT",
    "username": "AGH_USERNAME",
    "password": "AGH_PASSWORD",
    "tls": "AGH_TLS",
    "verify_ssl": "AGH_VERIFY_SSL",
    "base_path": "AGH_BASE_PATH",
    "request_timeout": "AGH_TIMEOUT",
}
_BOOL_FIELDS = frozenset({"tls", "verify_ssl"})
_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})


class Settings(BaseModel):
    """Resolved connection settings for a single AdGuard Home instance."""

    host: str
    port: int = 3000
    username: str | None = None
    password: str | None = None
    tls: bool = False
    verify_ssl: bool = True
    base_path: str = "/control"
    request_timeout: float = Field(default=10.0, gt=0)


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in _TRUE_VALUES


def _coerce(field: str, value: Any) -> Any:
    """Coerce a raw (string) value for a field to its expected type."""
    if isinstance(value, str) and field in _BOOL_FIELDS:
        return _parse_bool(value)
    return value


def _read_toml(config_path: Path) -> dict[str, Any]:
    if not config_path.is_file():
        return {}
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def _select_profile(
    data: dict[str, Any],
    profile: str | None,
) -> tuple[str, dict[str, Any]]:
    """Return ``(profile_name, profile_data)`` from parsed TOML."""
    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        # No profile tables: bare top-level keys are the implicit default.
        base = {k: v for k, v in data.items() if k != "default_profile"}
        return "default", base

    name = profile or os.environ.get("AGH_PROFILE") or data.get("default_profile")
    if name is None:
        # Fall back to the sole profile if there is exactly one, else "default".
        name = next(iter(profiles)) if len(profiles) == 1 else "default"
    return str(name), dict(profiles.get(name, {}))


def _read_env() -> dict[str, Any]:
    env: dict[str, Any] = {}
    for field, var in _ENV_FIELDS.items():
        raw = os.environ.get(var)
        if raw is not None and raw != "":
            env[field] = _coerce(field, raw)
    return env


def load_settings(
    *,
    profile: str | None = None,
    config_path: Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> Settings:
    """Resolve :class:`Settings` from TOML, environment, and CLI overrides.

    Args:
        profile: Profile name to select from the TOML file.
        config_path: Path to the TOML file (defaults to the user config path).
        overrides: CLI flag values; ``None`` entries are ignored.

    Returns:
        A validated :class:`Settings` instance.
    """
    path = config_path or DEFAULT_CONFIG_PATH
    toml_data = _read_toml(path)
    _, profile_data = _select_profile(toml_data, profile)

    layer_toml = {k: _coerce(k, v) for k, v in profile_data.items() if k in _ENV_FIELDS}
    layer_env = _read_env()
    layer_flags = {
        k: v for k, v in (overrides or {}).items() if k in _ENV_FIELDS and v is not None
    }

    merged: dict[str, Any] = {**layer_toml, **layer_env, **layer_flags}
    return Settings(**merged)
