"""Tests for `AdGuard.export()` and the `adguardctl export` command."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import respx
from typer.testing import CliRunner

from adguardctl.api import EXPORT_ENDPOINTS, AdGuard
from adguardctl.cli.app import app

BASE = "http://adguard.local:3000/control"
runner = CliRunner()


def _mock_all_endpoints() -> None:
    for uri in EXPORT_ENDPOINTS.values():
        respx.get(f"{BASE}/{uri}").mock(
            return_value=httpx.Response(200, json={"uri": uri}),
        )


@respx.mock
async def test_export_returns_all_areas(adguard: AdGuard) -> None:
    _mock_all_endpoints()
    result = await adguard.export()
    assert set(result) == set(EXPORT_ENDPOINTS)
    # Raw payloads preserved verbatim.
    assert result["dns_info"] == {"uri": "dns_info"}


@respx.mock
async def test_export_preserves_fields_models_would_drop(adguard: AdGuard) -> None:
    respx.get(f"{BASE}/dns_info").mock(
        return_value=httpx.Response(
            200,
            json={"upstream_dns": ["1.1.1.1"], "some_new_field": "kept"},
        ),
    )
    for uri in EXPORT_ENDPOINTS.values():
        if uri != "dns_info":
            respx.get(f"{BASE}/{uri}").mock(return_value=httpx.Response(200, json={}))
    result = await adguard.export()
    assert result["dns_info"]["some_new_field"] == "kept"


@respx.mock
async def test_export_maps_failed_endpoint_to_none(adguard: AdGuard) -> None:
    respx.get(f"{BASE}/tls/status").mock(return_value=httpx.Response(500))
    for uri in EXPORT_ENDPOINTS.values():
        if uri != "tls/status":
            respx.get(f"{BASE}/{uri}").mock(return_value=httpx.Response(200, json={}))
    result = await adguard.export()
    assert result["tls_status"] is None
    assert result["status"] == {}


@respx.mock
def test_cli_export_stdout_json() -> None:
    _mock_all_endpoints()
    result = runner.invoke(app, ["--host", "adguard.local", "export"])
    assert result.exit_code == 0
    parsed = json.loads(result.stdout)
    assert set(parsed) == set(EXPORT_ENDPOINTS)


@respx.mock
def test_cli_export_writes_file(tmp_path: Path) -> None:
    _mock_all_endpoints()
    out = tmp_path / "export.json"
    result = runner.invoke(
        app, ["--host", "adguard.local", "export", "--output", str(out)]
    )
    assert result.exit_code == 0
    data: dict[str, Any] = json.loads(out.read_text())
    assert data["clients"] == {"uri": "clients"}
