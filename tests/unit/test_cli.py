"""CLI tests using typer's CliRunner with respx-mocked HTTP."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
import respx
from typer.testing import CliRunner

from adguardctl.cli.app import app

BASE = "http://adguard.local:3000/control"
runner = CliRunner()


@pytest.fixture
def _no_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("AGH_HOST", "AGH_PORT", "AGH_USERNAME", "AGH_PASSWORD", "AGH_PROFILE"):
        monkeypatch.delenv(var, raising=False)


def invoke(*args: str) -> Any:
    return runner.invoke(app, ["--host", "adguard.local", *args])


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "adguardctl" in result.stdout


@respx.mock
def test_status_table(load_fixture: Any) -> None:
    respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(200, json=load_fixture("status.json")),
    )
    result = invoke("status")
    assert result.exit_code == 0
    assert "v0.107.50" in result.stdout


@respx.mock
def test_status_json(load_fixture: Any) -> None:
    respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(200, json=load_fixture("status.json")),
    )
    result = invoke("--json", "status")
    assert result.exit_code == 0
    assert json.loads(result.stdout)["version"] == "v0.107.50"


@respx.mock
def test_settings_protection_off_with_duration() -> None:
    route = respx.post(f"{BASE}/protection").mock(return_value=httpx.Response(200))
    result = invoke("settings", "protection", "off", "--duration", "30")
    assert result.exit_code == 0
    assert json.loads(route.calls.last.request.content) == {
        "enabled": False,
        "duration": 30000,
    }


@respx.mock
def test_rewrites_list_json() -> None:
    respx.get(f"{BASE}/rewrite/list").mock(
        return_value=httpx.Response(
            200, json=[{"domain": "a.local", "answer": "10.0.0.1", "enabled": True}]
        ),
    )
    result = invoke("--json", "rewrites", "list")
    assert result.exit_code == 0
    assert json.loads(result.stdout)[0]["domain"] == "a.local"


@respx.mock
def test_rewrites_add() -> None:
    route = respx.post(f"{BASE}/rewrite/add").mock(return_value=httpx.Response(200))
    result = invoke("rewrites", "add", "b.local", "10.0.0.2")
    assert result.exit_code == 0
    assert route.called


@respx.mock
def test_querylog_show_passes_filters() -> None:
    route = respx.get(f"{BASE}/querylog").mock(
        return_value=httpx.Response(200, json={"oldest": "", "data": []}),
    )
    result = invoke("querylog", "show", "-s", "blocked", "--search", "ads", "-n", "5")
    assert result.exit_code == 0
    params = route.calls.last.request.url.params
    assert params["response_status"] == "blocked"
    assert params["search"] == "ads"
    assert params["limit"] == "5"


@respx.mock
def test_clients_list_table(load_fixture: Any) -> None:
    respx.get(f"{BASE}/clients").mock(
        return_value=httpx.Response(200, json=load_fixture("clients.json")),
    )
    result = invoke("clients", "list")
    assert result.exit_code == 0
    assert "laptop" in result.stdout


@respx.mock
def test_access_block_host_roundtrip(load_fixture: Any) -> None:
    respx.get(f"{BASE}/access/list").mock(
        return_value=httpx.Response(200, json=load_fixture("access_list.json")),
    )
    set_route = respx.post(f"{BASE}/access/set").mock(return_value=httpx.Response(200))
    result = invoke("access", "block-host", "new.example.com")
    assert result.exit_code == 0
    assert (
        "new.example.com"
        in json.loads(set_route.calls.last.request.content)["blocked_hosts"]
    )


@respx.mock
def test_stats_show(load_fixture: Any) -> None:
    respx.get(f"{BASE}/stats").mock(
        return_value=httpx.Response(200, json=load_fixture("stats.json")),
    )
    result = invoke("stats", "show")
    assert result.exit_code == 0
    assert "1000" in result.stdout


@respx.mock
def test_connection_error_exit_code() -> None:
    respx.get(f"{BASE}/status").mock(side_effect=httpx.ConnectError("down"))
    result = invoke("status")
    assert result.exit_code == 1
    assert "Error" in result.output


@pytest.mark.usefixtures("_no_env")
def test_missing_host_exit_code() -> None:
    # No --host, no env, and a config path that does not exist.
    result = runner.invoke(app, ["--config", "/nonexistent/nope.toml", "status"])
    assert result.exit_code == 2
    assert "host" in result.output.lower()
