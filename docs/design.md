# adguardctl — Specification

## Overview

`adguardctl` is an async-first Python CLI for managing an AdGuard Home instance.
It mirrors the web-UI feature areas (general settings, DNS, encryption, clients,
rewrites, allowlists/access, filters, custom rules, query log, statistics) and
reads the query log with filters. It lives at `tools/adguardctl` and will later
be extracted into a standalone repository.

- **Package manager:** uv (deps added only via `uv add` / `uv add --dev`)
- **HTTP:** httpx (async), own client — the PyPI `adguardhome` lib covers ~40% and
  is Basic-Auth-only, so we implement full coverage using it and the AdGuard Home
  OpenAPI spec as reference.
- **Models:** Pydantic v2 (`extra="ignore"` for forward compatibility)
- **CLI:** Typer; **output:** Rich tables, with a global `--json` flag
- **Lint:** Ruff (`select = ALL` with a pragmatic ignore set)
- **Types:** `ty` (primary), basedpyright (secondary, standard mode)
- **Tests:** pytest + pytest-asyncio (auto), respx (unit HTTP mocking),
  pytest-cov (≥85% gate), pytest-skip-slow (gates integration), pytest-retry

## Architecture

```
cli/ (typer)  →  api.py (AdGuard facade + area classes)  →  client.py (httpx)  →  AdGuard Home /control
                         ↑ models.py (Pydantic)                   ↑ config.py (layered settings)
                         render.py (rich tables / JSON)
```

- **`client.AdGuardClient`** — one `httpx.AsyncClient`, base path `/control`,
  timeout, error mapping (non-2xx → `AdGuardError`, transport/timeout →
  `AdGuardConnectionError`, 401/403 after login retry → `AdGuardAuthError`). Async
  context manager. Auth: HTTP Basic with automatic session-cookie login fallback.
- **`api`** — `AdGuard` facade composes one class per area, each returning
  validated Pydantic models. `AdGuard.from_settings(Settings)` builds the client.
- **`config`** — layered resolution: TOML profile → env (`AGH_*`) → CLI flags.
- **`cli`** — root app + one sub-app per area; a shared `run_async` helper resolves
  settings, runs the coroutine, and converts errors to friendly exit codes
  (2 = misconfiguration, 1 = runtime/API error).

## Config precedence

CLI flags > environment (`AGH_HOST`, `AGH_PORT`, `AGH_USERNAME`, `AGH_PASSWORD`,
`AGH_TLS`, `AGH_VERIFY_SSL`, `AGH_BASE_PATH`, `AGH_TIMEOUT`, `AGH_PROFILE`) >
`~/.config/adguardctl/config.toml` (named `[profiles.*]`, `default_profile`, or
bare top-level keys as the implicit `default`).

## Endpoint coverage (v1)

R = read, W = write, phase-2 = read now/write later, — = excluded.

| Area (`#hash`) | Endpoints | v1 |
|---|---|---|
| settings (`#settings`) | `GET /status`, `POST /protection`, `safebrowsing|parental/{status,enable,disable}`, `GET|PUT /safesearch/{status,settings}`, `GET /stats/config` | R+W |
| dns (`#dns`) | `GET /dns_info`, `POST /test_upstream_dns`, `POST /cache_clear` | R; `POST /dns_config` = phase-2 |
| encryption (`#encryption`) | `GET /tls/status`, `POST /tls/validate` | R; `POST /tls/configure` = phase-2 |
| clients (`#clients`) | `GET /clients`, `POST /clients/{add,update,delete}` | R+W |
| dhcp (`#dhcp`) | `/dhcp/*` | — excluded |
| rewrites (`#dns_rewrites`) | `GET /rewrite/list`, `POST /rewrite/{add,delete}`, `PUT /rewrite/update` | R+W |
| access (`#dns_allowlists`) | `GET /access/list`, `POST /access/set` | R+W |
| filters (`#filters`) | `GET /filtering/status`, `POST /filtering/{config,add_url,remove_url,refresh}` | R+W |
| rules (`#custom_rules`) | `POST /filtering/set_rules` (read from `filtering/status.user_rules`) | R+W |
| querylog (`#logs`) | `GET /querylog` (`response_status,search,limit,offset,older_than`), `GET /querylog/config`, `POST /querylog_clear` | R+W |
| stats | `GET /stats`, `POST /stats_reset` | R+W |

## Command tree

```
adguardctl [global opts] <command>
  status
  settings   show | protection on|off [--duration] | safebrowsing on|off | parental on|off | safesearch | stats-config
  dns        show | test-upstream <server...> | cache-clear
  encryption show
  clients    list | add <name> <ids...> | delete <name>
  rewrites   list | add <domain> <answer> | delete <domain> <answer>
  access     show | block-host <host> | unblock-host <host>
  filters    show | add <name> <url> [--allowlist] | remove <url> [--allowlist] | refresh [--allowlist]
  rules      show | set (--rule/-r ... | --file/-f)
  querylog   show [-s status] [--search] [-n limit] [--older-than] | config | clear
  stats      show | reset
  export     [--output PATH]
```

`export` (`AdGuard.export()` in `api.py`, endpoint map `EXPORT_ENDPOINTS`) fans out
concurrently over the raw config endpoints (`status`, `dns_info`, `tls/status`,
`filtering/status`, `rewrite/list`, `access/list`, `clients`,
`blocked_services/get`, `safesearch/status`, `querylog/config`, `stats/config`)
and returns full-fidelity JSON — a failed/absent endpoint maps to `null`. The
integration-test seed (`docker/adguardhome/AdGuardHome.yaml`) is produced by
running `export` against a live instance and sanitizing to "public config only"
(keep filter lists / DNS tuning / safe search / blocked hosts; drop clients,
internal rewrites, and access-list client IPs; keep test creds; pin
`schema_version: 28`).

Global options: `--host/-H`, `--port/-p`, `--username/-u`, `--password`,
`--tls/--no-tls`, `--insecure`, `--timeout`, `--profile`, `--config`, `--json`,
`--version`, `-h/--help`.

## Testing

- **Unit** (`tests/unit/`, default): respx-mocked httpx from `tests/fixtures/*.json`;
  typer `CliRunner` for command tests; ≥85% coverage gate.
- **Integration** (`tests/integration/`, marked `integration` + `slow`, opt-in):
  runs against `compose.yml`, which mirrors the real architecture — AdGuard Home
  (`adguard/adguardhome`, pre-seeded `admin/test1234`) forwarding to a recursive
  **Unbound** sidecar (built from `docker/unbound/`, hardened config mirroring
  `install.sh`, pinned at static IP `172.28.0.53:5335`). Tests cover read paths, a
  rewrite add/list/delete round-trip, and an end-to-end AGH→Unbound upstream check
  via `test_upstream_dns`. Skipped unless `--slow` is passed and the stack is up.

## justfile recipes

`help`, `sync`/`install`, `lock`, `run`, `dev`, `test`/`test-unit`,
`test-integration`, `cov`, `lint`, `format`, `format-check`, `type`, `spell`,
`check`/`ci`, `build`, `compose-up`, `compose-down`, `clean`, `version`.

## Out of scope / future

- DHCP management (`/dhcp/*`) — intentionally excluded.
- DNS (`/dns_config`) and TLS (`/tls/configure`) *write* operations — phase-2.
- Non-deprecated query-log `reason` filter (currently uses `response_status`).
