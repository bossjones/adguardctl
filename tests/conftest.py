"""Shared pytest fixtures for adguardctl tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from adguardctl import config
from adguardctl.api import AdGuard
from adguardctl.client import AdGuardClient

BASE = "http://adguard.local:3000/control"

FIXTURES = Path(__file__).parent / "fixtures"

_ENV_VARS = (
    "AGH_HOST",
    "AGH_PORT",
    "AGH_USERNAME",
    "AGH_PASSWORD",
    "AGH_TLS",
    "AGH_VERIFY_SSL",
    "AGH_BASE_PATH",
    "AGH_TIMEOUT",
    "AGH_PROFILE",
)


@pytest.fixture(autouse=True)
def _isolate_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Keep tests hermetic: never read the developer's real config or AGH_* env."""
    monkeypatch.setattr(config, "DEFAULT_CONFIG_PATH", tmp_path / "no-config.toml")
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)


@pytest.fixture
def base_url() -> str:
    """Return the control-API base URL used in tests."""
    return BASE


@pytest.fixture
def load_fixture() -> Any:
    """Return a loader for JSON fixtures under ``tests/fixtures``."""

    def _load(name: str) -> Any:
        return json.loads((FIXTURES / name).read_text())

    return _load


@pytest.fixture
def adguard() -> AdGuard:
    """Return an :class:`AdGuard` facade pointed at the test base URL."""
    return AdGuard(AdGuardClient("adguard.local"))
