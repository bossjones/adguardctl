"""Integration tests against a live AdGuard Home (see compose.yml).

Skipped by default. Run with::

    docker compose up -d
    uv run pytest -m integration --slow

They authenticate as admin/test1234 against http://localhost:3000.
"""

from __future__ import annotations

import httpx
import pytest

from adguardctl.api import AdGuard

pytestmark = [pytest.mark.integration, pytest.mark.slow]

HOST = "localhost"
PORT = 3000
USERNAME = "admin"
PASSWORD = "test1234"


def _reachable() -> bool:
    try:
        resp = httpx.get(f"http://{HOST}:{PORT}/control/status", timeout=2.0)
    except httpx.HTTPError:
        return False
    return resp.status_code in (200, 401, 403)


@pytest.fixture
def adguard() -> AdGuard:
    if not _reachable():
        pytest.skip("AdGuard Home not reachable on localhost:3000 (run compose up)")
    return AdGuard.from_host(HOST, port=PORT, username=USERNAME, password=PASSWORD)


async def test_status(adguard: AdGuard) -> None:
    async with adguard:
        status = await adguard.settings.status()
    assert status.version
    assert status.running is True


async def test_stats(adguard: AdGuard) -> None:
    async with adguard:
        stats = await adguard.stats.get()
    assert stats.num_dns_queries >= 0


async def test_rewrite_roundtrip(adguard: AdGuard) -> None:
    domain = "adguardctl-itest.local"
    answer = "10.99.99.99"
    async with adguard:
        await adguard.rewrites.add(domain, answer)
        rules = await adguard.rewrites.list()
        assert any(r.domain == domain and r.answer == answer for r in rules)
        await adguard.rewrites.delete(domain, answer)
        rules_after = await adguard.rewrites.list()
        assert not any(r.domain == domain for r in rules_after)


async def test_querylog_read(adguard: AdGuard) -> None:
    async with adguard:
        log = await adguard.querylog.get(response_status="all", limit=5)
    assert isinstance(log.data, list)


async def test_unbound_upstream_reachable(adguard: AdGuard) -> None:
    # Proves the AGH -> Unbound chain: AGH queries the upstream and reports its
    # result. Success is reported as "OK" (older versions used ""); anything else
    # is an error message.
    upstream = "172.28.0.53:5335"
    async with adguard:
        result = await adguard.dns.test_upstreams(upstream_dns=[upstream])
    assert result, "test_upstream_dns returned no result"
    assert all(v in ("", "OK") for v in result.values()), f"upstream errors: {result}"
