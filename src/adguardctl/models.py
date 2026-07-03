"""Pydantic models mirroring AdGuard Home control-API shapes.

Every model uses ``extra="ignore"`` so that new/unknown fields returned by
newer AdGuard Home versions do not break parsing. Only the fields adguardctl
reads or writes are declared explicitly.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    """Base model that tolerates unknown fields from the API."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# --- General settings / status -------------------------------------------------


class ServerStatus(_Model):
    """Response of ``GET /status``."""

    version: str = ""
    protection_enabled: bool = False
    running: bool = False
    dns_addresses: list[str] = Field(default_factory=list)
    dns_port: int = 0
    http_port: int = 0
    language: str = ""
    dhcp_available: bool = False
    protection_disabled_duration: int = 0


class ToggleStatus(_Model):
    """Generic ``{"enabled": bool}`` response (safebrowsing/parental)."""

    enabled: bool = False


class SafeSearchConfig(_Model):
    """Safe-search settings (``GET/PUT /safesearch/*``)."""

    enabled: bool = False
    bing: bool = False
    duckduckgo: bool = False
    ecosia: bool = False
    google: bool = False
    pixabay: bool = False
    yandex: bool = False
    youtube: bool = False


# --- Stats ---------------------------------------------------------------------


class StatsConfig(_Model):
    """Response of ``GET /stats/config``."""

    enabled: bool = True
    interval: int = 0
    ignored: list[str] = Field(default_factory=list)


class Stats(_Model):
    """Dashboard statistics (``GET /stats``)."""

    num_dns_queries: int = 0
    num_blocked_filtering: int = 0
    num_replaced_safebrowsing: int = 0
    num_replaced_safesearch: int = 0
    num_replaced_parental: int = 0
    avg_processing_time: float = 0.0
    top_queried_domains: list[dict[str, int]] = Field(default_factory=list)
    top_blocked_domains: list[dict[str, int]] = Field(default_factory=list)
    top_clients: list[dict[str, int]] = Field(default_factory=list)


# --- DNS -----------------------------------------------------------------------


class DNSConfig(_Model):
    """Subset of ``GET /dns_info`` / ``POST /dns_config``."""

    upstream_dns: list[str] = Field(default_factory=list)
    bootstrap_dns: list[str] = Field(default_factory=list)
    fallback_dns: list[str] = Field(default_factory=list)
    upstream_mode: str = ""
    ratelimit: int = 0
    dnssec_enabled: bool = False
    disable_ipv6: bool = False
    cache_size: int = 0
    cache_ttl_min: int = 0
    cache_ttl_max: int = 0
    blocking_mode: str = ""


# --- Encryption / TLS ----------------------------------------------------------


class TlsConfig(_Model):
    """Subset of ``GET /tls/status`` / ``POST /tls/{configure,validate}``."""

    enabled: bool = False
    server_name: str = ""
    force_https: bool = False
    port_https: int = 0
    port_dns_over_tls: int = 0
    port_dns_over_quic: int = 0
    valid_cert: bool = False
    valid_chain: bool = False
    valid_key: bool = False
    valid_pair: bool = False
    subject: str = ""
    issuer: str = ""
    not_before: str = ""
    not_after: str = ""
    dns_names: list[str] = Field(default_factory=list)
    warning_validation: str = ""


# --- Clients -------------------------------------------------------------------


class Client(_Model):
    """A persistent client (``/clients``)."""

    name: str
    ids: list[str] = Field(default_factory=list)
    use_global_settings: bool = True
    filtering_enabled: bool = False
    parental_enabled: bool = False
    safebrowsing_enabled: bool = False
    use_global_blocked_services: bool = True
    blocked_services: list[str] = Field(default_factory=list)
    upstreams: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    ignore_querylog: bool = False
    ignore_statistics: bool = False


class AutoClient(_Model):
    """A runtime-discovered client (``auto_clients``)."""

    name: str = ""
    ip: str = Field(default="", alias="ip")
    source: str = ""


class ClientsResponse(_Model):
    """Response of ``GET /clients``."""

    clients: list[Client] = Field(default_factory=list)
    auto_clients: list[AutoClient] = Field(default_factory=list)
    supported_tags: list[str] = Field(default_factory=list)


# --- Rewrites ------------------------------------------------------------------


class RewriteEntry(_Model):
    """A DNS rewrite rule (``/rewrite/*``)."""

    domain: str
    answer: str
    enabled: bool = True


# --- Access / allowlists -------------------------------------------------------


class AccessList(_Model):
    """Response/body of ``GET/POST /access/{list,set}``."""

    allowed_clients: list[str] = Field(default_factory=list)
    disallowed_clients: list[str] = Field(default_factory=list)
    blocked_hosts: list[str] = Field(default_factory=list)


# --- Filters / custom rules ----------------------------------------------------


class Filter(_Model):
    """A filter-list subscription (``filters``/``whitelist_filters``)."""

    id: int = 0
    enabled: bool = False
    name: str = ""
    url: str = ""
    rules_count: int = 0
    last_updated: str = ""


class FilterStatus(_Model):
    """Response of ``GET /filtering/status``."""

    enabled: bool = False
    interval: int = 0
    filters: list[Filter] = Field(default_factory=list)
    whitelist_filters: list[Filter] = Field(default_factory=list)
    user_rules: list[str] = Field(default_factory=list)


# --- Query log -----------------------------------------------------------------


class DnsQuestion(_Model):
    """The question section of a query-log item."""

    host: str = Field(default="", alias="name")
    type: str = ""
    class_: str = Field(default="", alias="class")


class QueryLogItem(_Model):
    """A single query-log entry."""

    time: str = ""
    question: DnsQuestion = Field(default_factory=DnsQuestion)
    client: str = ""
    elapsed_ms: str = Field(default="", alias="elapsedMs")
    status: str = ""
    reason: str = ""
    cached: bool = False
    upstream: str = ""


class QueryLog(_Model):
    """Response of ``GET /querylog``."""

    oldest: str = ""
    data: list[QueryLogItem] = Field(default_factory=list)


class QueryLogConfig(_Model):
    """Response of ``GET /querylog/config``."""

    enabled: bool = True
    interval: int = 0
    anonymize_client_ip: bool = False
    ignored: list[str] = Field(default_factory=list)
