"""Typed async API over the AdGuard Home control endpoints.

Each area is a small class that takes an :class:`~adguardctl.client.AdGuardClient`
and returns validated Pydantic models. :class:`AdGuard` composes the areas and
acts as an async context manager, mirroring the reference library's ergonomics.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

from .client import AdGuardClient
from .models import (
    AccessList,
    Client,
    ClientsResponse,
    DNSConfig,
    Filter,  # noqa: F401  (re-exported for callers/tests)
    FilterStatus,
    QueryLog,
    QueryLogConfig,
    RewriteEntry,
    SafeSearchConfig,
    ServerStatus,
    Stats,
    StatsConfig,
    TlsConfig,
    ToggleStatus,
)

if TYPE_CHECKING:
    from .config import Settings

# Valid values for the (deprecated but still supported) querylog filter.
RESPONSE_STATUSES = (
    "all",
    "filtered",
    "blocked",
    "blocked_safebrowsing",
    "blocked_parental",
    "whitelisted",
    "rewritten",
    "safe_search",
    "processed",
)

# Raw config endpoints aggregated by ``AdGuard.export()`` (area key -> control URI).
EXPORT_ENDPOINTS: dict[str, str] = {
    "status": "status",
    "dns_info": "dns_info",
    "tls_status": "tls/status",
    "filtering_status": "filtering/status",
    "rewrites": "rewrite/list",
    "access": "access/list",
    "clients": "clients",
    "blocked_services": "blocked_services/get",
    "safesearch": "safesearch/status",
    "querylog_config": "querylog/config",
    "stats_config": "stats/config",
}


class SettingsAPI:
    """General settings: protection, safe browsing, parental, safe search, stats."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def status(self) -> ServerStatus:
        return ServerStatus.model_validate(await self._client.request("status"))

    async def set_protection(
        self, *, enabled: bool, duration: int | None = None
    ) -> None:
        body: dict[str, Any] = {"enabled": enabled}
        if duration is not None:
            body["duration"] = duration * 1000
        await self._client.request("protection", method="POST", json_data=body)

    async def safebrowsing(self) -> bool:
        data = await self._client.request("safebrowsing/status")
        return ToggleStatus.model_validate(data).enabled

    async def set_safebrowsing(self, *, enabled: bool) -> None:
        action = "enable" if enabled else "disable"
        await self._client.request(f"safebrowsing/{action}", method="POST")

    async def parental(self) -> bool:
        data = await self._client.request("parental/status")
        return ToggleStatus.model_validate(data).enabled

    async def set_parental(self, *, enabled: bool) -> None:
        action = "enable" if enabled else "disable"
        await self._client.request(f"parental/{action}", method="POST")

    async def safesearch(self) -> SafeSearchConfig:
        return SafeSearchConfig.model_validate(
            await self._client.request("safesearch/status")
        )

    async def set_safesearch(self, config: SafeSearchConfig) -> None:
        await self._client.request(
            "safesearch/settings", method="PUT", json_data=config.model_dump()
        )

    async def stats_config(self) -> StatsConfig:
        return StatsConfig.model_validate(await self._client.request("stats/config"))


class DnsAPI:
    """DNS settings (read + upstream test + cache clear; config write is phase-2)."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def info(self) -> DNSConfig:
        return DNSConfig.model_validate(await self._client.request("dns_info"))

    async def test_upstreams(
        self,
        *,
        upstream_dns: list[str],
        bootstrap_dns: list[str] | None = None,
    ) -> dict[str, str]:
        body: dict[str, Any] = {"upstream_dns": upstream_dns}
        if bootstrap_dns:
            body["bootstrap_dns"] = bootstrap_dns
        return await self._client.request(
            "test_upstream_dns", method="POST", json_data=body
        )

    async def cache_clear(self) -> None:
        await self._client.request("cache_clear", method="POST")

    # TODO(phase-2): implement set_config(DNSConfig) -> POST /dns_config.


class EncryptionAPI:
    """TLS/encryption (read + validate; configure write is phase-2)."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def status(self) -> TlsConfig:
        return TlsConfig.model_validate(await self._client.request("tls/status"))

    async def validate(self, config: TlsConfig) -> TlsConfig:
        data = await self._client.request(
            "tls/validate", method="POST", json_data=config.model_dump()
        )
        return TlsConfig.model_validate(data)

    # TODO(phase-2): implement configure(TlsConfig) -> POST /tls/configure.


class ClientsAPI:
    """Persistent client management (full CRUD)."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def list(self) -> ClientsResponse:
        return ClientsResponse.model_validate(await self._client.request("clients"))

    async def add(self, client: Client) -> None:
        await self._client.request(
            "clients/add", method="POST", json_data=client.model_dump()
        )

    async def update(self, name: str, data: Client) -> None:
        body = {"name": name, "data": data.model_dump()}
        await self._client.request("clients/update", method="POST", json_data=body)

    async def delete(self, name: str) -> None:
        await self._client.request(
            "clients/delete", method="POST", json_data={"name": name}
        )


class RewritesAPI:
    """DNS rewrite management (full CRUD)."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def list(self) -> Sequence[RewriteEntry]:
        data = await self._client.request("rewrite/list")
        return [RewriteEntry.model_validate(item) for item in data]

    async def add(self, domain: str, answer: str) -> None:
        body = {"domain": domain, "answer": answer}
        await self._client.request("rewrite/add", method="POST", json_data=body)

    async def delete(self, domain: str, answer: str) -> None:
        body = {"domain": domain, "answer": answer}
        await self._client.request("rewrite/delete", method="POST", json_data=body)

    async def update(self, target: RewriteEntry, new: RewriteEntry) -> None:
        body = {"target": target.model_dump(), "update": new.model_dump()}
        await self._client.request("rewrite/update", method="PUT", json_data=body)


class AccessAPI:
    """Access lists / allowlists (read + set)."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def list(self) -> AccessList:
        return AccessList.model_validate(await self._client.request("access/list"))

    async def set(self, access: AccessList) -> None:
        await self._client.request(
            "access/set", method="POST", json_data=access.model_dump()
        )


class FiltersAPI:
    """Filter-list subscriptions and global filtering config."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def status(self) -> FilterStatus:
        return FilterStatus.model_validate(
            await self._client.request("filtering/status")
        )

    async def set_config(self, *, enabled: bool, interval: int) -> None:
        body = {"enabled": enabled, "interval": interval}
        await self._client.request("filtering/config", method="POST", json_data=body)

    async def add_url(self, *, name: str, url: str, whitelist: bool = False) -> None:
        body = {"name": name, "url": url, "whitelist": whitelist}
        await self._client.request("filtering/add_url", method="POST", json_data=body)

    async def remove_url(self, *, url: str, whitelist: bool = False) -> None:
        body = {"url": url, "whitelist": whitelist}
        await self._client.request(
            "filtering/remove_url", method="POST", json_data=body
        )

    async def refresh(self, *, whitelist: bool = False) -> int:
        body = {"whitelist": whitelist}
        data = await self._client.request(
            "filtering/refresh", method="POST", json_data=body
        )
        return int(data.get("updated", 0)) if isinstance(data, dict) else 0


class RulesAPI:
    """User-defined custom filtering rules."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def get(self) -> list[str]:
        status = FilterStatus.model_validate(
            await self._client.request("filtering/status")
        )
        return status.user_rules

    async def set(self, rules: list[str]) -> None:
        await self._client.request(
            "filtering/set_rules", method="POST", json_data={"rules": rules}
        )


class QueryLogAPI:
    """Query-log reading and configuration."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def get(
        self,
        *,
        response_status: str = "all",
        search: str | None = None,
        limit: int | None = None,
        offset: int | None = None,
        older_than: str | None = None,
    ) -> QueryLog:
        params: dict[str, Any] = {"response_status": response_status}
        if search:
            params["search"] = search
        if limit is not None:
            params["limit"] = limit
        if offset is not None:
            params["offset"] = offset
        if older_than:
            params["older_than"] = older_than
        return QueryLog.model_validate(
            await self._client.request("querylog", params=params)
        )

    async def config(self) -> QueryLogConfig:
        return QueryLogConfig.model_validate(
            await self._client.request("querylog/config")
        )

    async def clear(self) -> None:
        await self._client.request("querylog_clear", method="POST")


class StatsAPI:
    """Statistics reading and reset."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client

    async def get(self) -> Stats:
        return Stats.model_validate(await self._client.request("stats"))

    async def reset(self) -> None:
        await self._client.request("stats_reset", method="POST")


class AdGuard:
    """Composed async API for a single AdGuard Home instance."""

    def __init__(self, client: AdGuardClient) -> None:
        self._client = client
        self.settings = SettingsAPI(client)
        self.dns = DnsAPI(client)
        self.encryption = EncryptionAPI(client)
        self.clients = ClientsAPI(client)
        self.rewrites = RewritesAPI(client)
        self.access = AccessAPI(client)
        self.filters = FiltersAPI(client)
        self.rules = RulesAPI(client)
        self.querylog = QueryLogAPI(client)
        self.stats = StatsAPI(client)

    @classmethod
    def from_settings(cls, settings: Settings) -> AdGuard:
        """Build an :class:`AdGuard` from resolved :class:`Settings`."""
        client = AdGuardClient(
            settings.host,
            port=settings.port,
            username=settings.username,
            password=settings.password,
            tls=settings.tls,
            verify_ssl=settings.verify_ssl,
            base_path=settings.base_path,
            request_timeout=settings.request_timeout,
        )
        return cls(client)

    @classmethod
    def from_host(cls, host: str, **kwargs: Any) -> AdGuard:
        """Build an :class:`AdGuard` directly from a host and client kwargs."""
        return cls(AdGuardClient(host, **kwargs))

    async def export(self) -> dict[str, Any]:
        """Pull the raw config from every area into one dict.

        Returns full-fidelity JSON (not the subset Pydantic models) keyed by
        area. Endpoints are fetched concurrently; any endpoint that errors or is
        absent on this AdGuard Home version maps to ``None`` instead of failing
        the whole export.
        """
        keys = list(EXPORT_ENDPOINTS)
        results = await asyncio.gather(
            *(self._client.request(uri) for uri in EXPORT_ENDPOINTS.values()),
            return_exceptions=True,
        )
        return {
            key: (None if isinstance(res, BaseException) else res)
            for key, res in zip(keys, results, strict=True)
        }

    async def close(self) -> None:
        await self._client.close()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        await self.close()
