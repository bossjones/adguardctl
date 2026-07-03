"""Coverage for the remaining read/write CLI commands."""

from __future__ import annotations

from typing import Any

import httpx
import respx
from typer.testing import CliRunner

from adguardctl.cli.app import app

BASE = "http://adguard.local:3000/control"
runner = CliRunner()


def invoke(*args: str) -> Any:
    return runner.invoke(app, ["--host", "adguard.local", *args])


@respx.mock
def test_settings_show(load_fixture: Any) -> None:
    respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(200, json=load_fixture("status.json")),
    )
    assert invoke("settings", "show").exit_code == 0


@respx.mock
def test_settings_safebrowsing_and_parental() -> None:
    respx.post(f"{BASE}/safebrowsing/enable").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/parental/disable").mock(return_value=httpx.Response(200))
    assert invoke("settings", "safebrowsing", "on").exit_code == 0
    assert invoke("settings", "parental", "off").exit_code == 0


@respx.mock
def test_settings_safesearch_and_stats_config(load_fixture: Any) -> None:
    respx.get(f"{BASE}/safesearch/status").mock(
        return_value=httpx.Response(200, json=load_fixture("safesearch_status.json")),
    )
    respx.get(f"{BASE}/stats/config").mock(
        return_value=httpx.Response(200, json={"enabled": True, "interval": 90}),
    )
    assert invoke("settings", "safesearch").exit_code == 0
    assert invoke("settings", "stats-config").exit_code == 0


@respx.mock
def test_dns_commands(load_fixture: Any) -> None:
    respx.get(f"{BASE}/dns_info").mock(
        return_value=httpx.Response(200, json=load_fixture("dns_info.json")),
    )
    respx.post(f"{BASE}/cache_clear").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/test_upstream_dns").mock(
        return_value=httpx.Response(200, json={"127.0.0.1:5335": ""}),
    )
    assert invoke("dns", "show").exit_code == 0
    assert invoke("dns", "cache-clear").exit_code == 0
    assert invoke("dns", "test-upstream", "127.0.0.1:5335").exit_code == 0


@respx.mock
def test_encryption_show(load_fixture: Any) -> None:
    respx.get(f"{BASE}/tls/status").mock(
        return_value=httpx.Response(200, json=load_fixture("tls_status.json")),
    )
    assert invoke("encryption", "show").exit_code == 0


@respx.mock
def test_filters_commands(load_fixture: Any) -> None:
    respx.get(f"{BASE}/filtering/status").mock(
        return_value=httpx.Response(200, json=load_fixture("filtering_status.json")),
    )
    respx.post(f"{BASE}/filtering/add_url").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/filtering/remove_url").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/filtering/refresh").mock(
        return_value=httpx.Response(200, json={"updated": 1}),
    )
    assert invoke("filters", "show").exit_code == 0
    assert invoke("filters", "add", "L", "https://x/y.txt").exit_code == 0
    assert invoke("filters", "remove", "https://x/y.txt").exit_code == 0
    assert invoke("filters", "refresh").exit_code == 0


@respx.mock
def test_rules_show_and_set(load_fixture: Any) -> None:
    respx.get(f"{BASE}/filtering/status").mock(
        return_value=httpx.Response(200, json=load_fixture("filtering_status.json")),
    )
    set_route = respx.post(f"{BASE}/filtering/set_rules").mock(
        return_value=httpx.Response(200)
    )
    assert invoke("rules", "show").exit_code == 0
    result = invoke("rules", "set", "-r", "||a.example^", "-r", "||b.example^")
    assert result.exit_code == 0
    import json  # noqa: PLC0415

    assert json.loads(set_route.calls.last.request.content)["rules"] == [
        "||a.example^",
        "||b.example^",
    ]


@respx.mock
def test_querylog_config_and_clear() -> None:
    respx.get(f"{BASE}/querylog/config").mock(
        return_value=httpx.Response(200, json={"enabled": True, "interval": 90}),
    )
    respx.post(f"{BASE}/querylog_clear").mock(return_value=httpx.Response(200))
    assert invoke("querylog", "config").exit_code == 0
    assert invoke("querylog", "clear").exit_code == 0


@respx.mock
def test_querylog_show_table(
    load_fixture: Any,
    monkeypatch: Any,
) -> None:
    monkeypatch.setenv("COLUMNS", "220")  # avoid table wrapping in the assertion
    respx.get(f"{BASE}/querylog").mock(
        return_value=httpx.Response(200, json=load_fixture("querylog.json")),
    )
    result = invoke("querylog", "show")
    assert result.exit_code == 0
    assert "ads.example.com" in result.stdout


@respx.mock
def test_clients_add_and_delete() -> None:
    respx.post(f"{BASE}/clients/add").mock(return_value=httpx.Response(200))
    respx.post(f"{BASE}/clients/delete").mock(return_value=httpx.Response(200))
    assert invoke("clients", "add", "tv", "10.0.0.7").exit_code == 0
    assert invoke("clients", "delete", "tv").exit_code == 0


@respx.mock
def test_access_show_and_unblock(load_fixture: Any) -> None:
    respx.get(f"{BASE}/access/list").mock(
        return_value=httpx.Response(200, json=load_fixture("access_list.json")),
    )
    respx.post(f"{BASE}/access/set").mock(return_value=httpx.Response(200))
    assert invoke("access", "show").exit_code == 0
    assert invoke("access", "unblock-host", "bad.example.com").exit_code == 0


@respx.mock
def test_rewrites_delete() -> None:
    respx.post(f"{BASE}/rewrite/delete").mock(return_value=httpx.Response(200))
    assert invoke("rewrites", "delete", "a.local", "1.1.1.1").exit_code == 0


@respx.mock
def test_stats_reset() -> None:
    respx.post(f"{BASE}/stats_reset").mock(return_value=httpx.Response(200))
    assert invoke("stats", "reset").exit_code == 0
