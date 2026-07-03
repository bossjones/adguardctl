"""Unit tests for :mod:`adguardctl.api` (all areas)."""

from __future__ import annotations

import json
from typing import Any

import httpx
import respx

from adguardctl.api import AdGuard
from adguardctl.models import (
    AccessList,
    Client,
    RewriteEntry,
    SafeSearchConfig,
    TlsConfig,
)

BASE = "http://adguard.local:3000/control"


# --- settings ------------------------------------------------------------------


@respx.mock
async def test_settings_status(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(200, json=load_fixture("status.json")),
    )
    status = await adguard.settings.status()
    assert status.version == "v0.107.50"
    assert status.protection_enabled is True


@respx.mock
async def test_settings_set_protection_with_duration(adguard: AdGuard) -> None:
    route = respx.post(f"{BASE}/protection").mock(return_value=httpx.Response(200))
    await adguard.settings.set_protection(enabled=False, duration=60)
    assert json.loads(route.calls.last.request.content) == {
        "enabled": False,
        "duration": 60000,
    }


@respx.mock
async def test_settings_safebrowsing_toggle(adguard: AdGuard) -> None:
    respx.get(f"{BASE}/safebrowsing/status").mock(
        return_value=httpx.Response(200, json={"enabled": True}),
    )
    enable = respx.post(f"{BASE}/safebrowsing/enable").mock(
        return_value=httpx.Response(200)
    )
    assert await adguard.settings.safebrowsing() is True
    await adguard.settings.set_safebrowsing(enabled=True)
    assert enable.called


@respx.mock
async def test_settings_parental_disable(adguard: AdGuard) -> None:
    route = respx.post(f"{BASE}/parental/disable").mock(
        return_value=httpx.Response(200)
    )
    await adguard.settings.set_parental(enabled=False)
    assert route.called


@respx.mock
async def test_settings_safesearch(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/safesearch/status").mock(
        return_value=httpx.Response(200, json=load_fixture("safesearch_status.json")),
    )
    put = respx.put(f"{BASE}/safesearch/settings").mock(
        return_value=httpx.Response(200)
    )
    config = await adguard.settings.safesearch()
    assert config.google is True
    await adguard.settings.set_safesearch(SafeSearchConfig(enabled=True, google=False))
    assert put.called


# --- dns -----------------------------------------------------------------------


@respx.mock
async def test_dns_info(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/dns_info").mock(
        return_value=httpx.Response(200, json=load_fixture("dns_info.json")),
    )
    info = await adguard.dns.info()
    assert info.upstream_dns == ["127.0.0.1:5335"]
    assert info.dnssec_enabled is True


@respx.mock
async def test_dns_cache_clear(adguard: AdGuard) -> None:
    route = respx.post(f"{BASE}/cache_clear").mock(return_value=httpx.Response(200))
    await adguard.dns.cache_clear()
    assert route.called


# --- encryption ----------------------------------------------------------------


@respx.mock
async def test_encryption_status(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/tls/status").mock(
        return_value=httpx.Response(200, json=load_fixture("tls_status.json")),
    )
    status = await adguard.encryption.status()
    assert status.enabled is True
    assert status.dns_names == ["adguard.local"]


@respx.mock
async def test_encryption_validate(adguard: AdGuard, load_fixture: Any) -> None:
    respx.post(f"{BASE}/tls/validate").mock(
        return_value=httpx.Response(200, json=load_fixture("tls_status.json")),
    )
    result = await adguard.encryption.validate(TlsConfig(enabled=True))
    assert result.valid_pair is True


# --- clients -------------------------------------------------------------------


@respx.mock
async def test_clients_list(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/clients").mock(
        return_value=httpx.Response(200, json=load_fixture("clients.json")),
    )
    resp = await adguard.clients.list()
    assert resp.clients[0].name == "laptop"
    assert resp.auto_clients[0].ip == "10.0.0.6"
    assert "device_laptop" in resp.supported_tags


@respx.mock
async def test_clients_add_update_delete(adguard: AdGuard) -> None:
    add = respx.post(f"{BASE}/clients/add").mock(return_value=httpx.Response(200))
    update = respx.post(f"{BASE}/clients/update").mock(return_value=httpx.Response(200))
    delete = respx.post(f"{BASE}/clients/delete").mock(return_value=httpx.Response(200))
    client = Client(name="tv", ids=["10.0.0.7"])
    await adguard.clients.add(client)
    await adguard.clients.update("tv", client)
    await adguard.clients.delete("tv")
    assert add.called
    assert json.loads(update.calls.last.request.content)["name"] == "tv"
    assert json.loads(delete.calls.last.request.content) == {"name": "tv"}


# --- rewrites ------------------------------------------------------------------


@respx.mock
async def test_rewrites_list_and_add(adguard: AdGuard) -> None:
    respx.get(f"{BASE}/rewrite/list").mock(
        return_value=httpx.Response(
            200, json=[{"domain": "a.local", "answer": "10.0.0.1"}]
        ),
    )
    add = respx.post(f"{BASE}/rewrite/add").mock(return_value=httpx.Response(200))
    rules = await adguard.rewrites.list()
    assert rules[0] == RewriteEntry(domain="a.local", answer="10.0.0.1")
    await adguard.rewrites.add("b.local", "10.0.0.2")
    assert json.loads(add.calls.last.request.content) == {
        "domain": "b.local",
        "answer": "10.0.0.2",
    }


@respx.mock
async def test_rewrites_update(adguard: AdGuard) -> None:
    route = respx.put(f"{BASE}/rewrite/update").mock(return_value=httpx.Response(200))
    await adguard.rewrites.update(
        RewriteEntry(domain="a.local", answer="1.1.1.1"),
        RewriteEntry(domain="a.local", answer="2.2.2.2"),
    )
    body = json.loads(route.calls.last.request.content)
    assert body["target"]["answer"] == "1.1.1.1"
    assert body["update"]["answer"] == "2.2.2.2"


# --- access --------------------------------------------------------------------


@respx.mock
async def test_access_list_and_set(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/access/list").mock(
        return_value=httpx.Response(200, json=load_fixture("access_list.json")),
    )
    set_route = respx.post(f"{BASE}/access/set").mock(return_value=httpx.Response(200))
    access = await adguard.access.list()
    assert access.blocked_hosts == ["bad.example.com"]
    await adguard.access.set(AccessList(allowed_clients=["10.0.0.5"]))
    assert set_route.called


# --- filters -------------------------------------------------------------------


@respx.mock
async def test_filters_status(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/filtering/status").mock(
        return_value=httpx.Response(200, json=load_fixture("filtering_status.json")),
    )
    status = await adguard.filters.status()
    assert status.enabled is True
    assert status.filters[0].rules_count == 5000


@respx.mock
async def test_filters_add_remove_refresh(adguard: AdGuard) -> None:
    add = respx.post(f"{BASE}/filtering/add_url").mock(return_value=httpx.Response(200))
    remove = respx.post(f"{BASE}/filtering/remove_url").mock(
        return_value=httpx.Response(200)
    )
    respx.post(f"{BASE}/filtering/refresh").mock(
        return_value=httpx.Response(200, json={"updated": 2}),
    )
    await adguard.filters.add_url(name="list", url="https://x/y.txt")
    await adguard.filters.remove_url(url="https://x/y.txt")
    updated = await adguard.filters.refresh()
    assert add.called
    assert remove.called
    assert updated == 2


# --- rules ---------------------------------------------------------------------


@respx.mock
async def test_rules_get_and_set(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/filtering/status").mock(
        return_value=httpx.Response(200, json=load_fixture("filtering_status.json")),
    )
    set_route = respx.post(f"{BASE}/filtering/set_rules").mock(
        return_value=httpx.Response(200)
    )
    rules = await adguard.rules.get()
    assert "||ads.example.com^" in rules
    await adguard.rules.set(["||new.example.com^"])
    assert json.loads(set_route.calls.last.request.content) == {
        "rules": ["||new.example.com^"]
    }


# --- querylog ------------------------------------------------------------------


@respx.mock
async def test_querylog_get_with_filters(adguard: AdGuard, load_fixture: Any) -> None:
    route = respx.get(f"{BASE}/querylog").mock(
        return_value=httpx.Response(200, json=load_fixture("querylog.json")),
    )
    log = await adguard.querylog.get(response_status="blocked", search="ads", limit=10)
    assert log.data[0].question.host == "ads.example.com"
    assert log.data[0].elapsed_ms == "1.23"
    request_url = route.calls.last.request.url
    assert request_url.params["response_status"] == "blocked"
    assert request_url.params["search"] == "ads"
    assert request_url.params["limit"] == "10"


@respx.mock
async def test_querylog_clear(adguard: AdGuard) -> None:
    route = respx.post(f"{BASE}/querylog_clear").mock(return_value=httpx.Response(200))
    await adguard.querylog.clear()
    assert route.called


# --- stats ---------------------------------------------------------------------


@respx.mock
async def test_stats_get_and_reset(adguard: AdGuard, load_fixture: Any) -> None:
    respx.get(f"{BASE}/stats").mock(
        return_value=httpx.Response(200, json=load_fixture("stats.json")),
    )
    reset = respx.post(f"{BASE}/stats_reset").mock(return_value=httpx.Response(200))
    stats = await adguard.stats.get()
    assert stats.num_dns_queries == 1000
    assert stats.num_blocked_filtering == 250
    await adguard.stats.reset()
    assert reset.called


# --- facade --------------------------------------------------------------------


async def test_from_settings_builds_client() -> None:
    from adguardctl.config import Settings  # noqa: PLC0415

    adguard = AdGuard.from_settings(Settings(host="h", port=8080))
    assert adguard._client.base_url == "http://h:8080/control/"
    await adguard.close()


@respx.mock
async def test_facade_context_manager() -> None:
    respx.get(f"{BASE}/stats").mock(return_value=httpx.Response(200, json={}))
    async with AdGuard.from_host("adguard.local") as adguard:
        stats = await adguard.stats.get()
    assert stats.num_dns_queries == 0
