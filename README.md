# adguardctl

An async-first CLI for managing an [AdGuard Home](https://adguard.com/adguard-home/overview.html)
instance — inspect and configure DNS, filters, clients, rewrites, access lists,
encryption status, statistics, and the query log.

Built with [httpx](https://www.python-httpx.org/) (async),
[Pydantic v2](https://docs.pydantic.dev/), [Typer](https://typer.tiangolo.com/),
and [Rich](https://rich.readthedocs.io/). Managed with
[uv](https://docs.astral.sh/uv/), linted with Ruff, type-checked with `ty`.

## Quick start

```bash
uv sync

# point at your instance (flags, env vars, or a config file — see below)
uv run adguardctl --host adguard.local --port 80 -u admin --password '***' status

# machine-readable output
uv run adguardctl --json querylog show --response-status blocked --limit 20
```

## Configuration

Settings resolve with this precedence (highest wins):

1. **CLI flags** — `--host`, `--port`, `--username`, `--password`, `--tls/--no-tls`,
   `--insecure`, `--timeout`, `--profile`, `--config`, `--json`
2. **Environment** — `AGH_HOST`, `AGH_PORT`, `AGH_USERNAME`, `AGH_PASSWORD`,
   `AGH_TLS`, `AGH_VERIFY_SSL`, `AGH_BASE_PATH`, `AGH_TIMEOUT`, `AGH_PROFILE`
3. **Config file** — `~/.config/adguardctl/config.toml` (override with `--config`)

```toml
# ~/.config/adguardctl/config.toml
default_profile = "home"

[profiles.home]
host = "adguard.local"
port = 80
username = "admin"
password = "secret"

[profiles.work]
host = "10.0.0.2"
```

```bash
uv run adguardctl --profile work status
```

Authentication uses HTTP Basic and transparently falls back to session-cookie
login (`POST /control/login`) if Basic is rejected.

## Command groups

| Group | Purpose |
|-------|---------|
| `status` | Quick server/protection summary |
| `settings` | Protection, safe browsing, parental, safe search, stats config |
| `dns` | DNS settings (read), upstream test, cache clear |
| `encryption` | TLS/encryption status |
| `clients` | List/add/delete persistent clients |
| `rewrites` | List/add/delete DNS rewrites |
| `access` | Allowed/disallowed clients, blocked hosts |
| `filters` | Filter-list subscriptions (add/remove/refresh) |
| `rules` | Custom filtering rules (show/set) |
| `querylog` | Read the query log, view config, clear |
| `stats` | Show/reset statistics |
| `export` | Dump the full **raw** config (all areas) as JSON |

`export` preserves every field the API returns (the typed `--json` reads drop
unknown fields), which makes it suitable for building a seed config:

```bash
uv run adguardctl --profile home export --output homelab.json
```

The committed test seed (`docker/adguardhome/AdGuardHome.yaml`) was generated this
way from a live instance and then sanitized to public config only (filter lists,
DNS tuning, safe search) with test credentials `admin`/`test1234`.

Run `uv run adguardctl <group> --help` for details. DHCP is intentionally out of
scope; DNS/TLS *write* operations are planned for a later phase.

## Development

```bash
just             # list recipes
just test        # unit tests (mocked HTTP) with coverage
just check       # format check + lint + type + tests (CI gate)
just compose-up  # start AdGuard Home + Unbound sidecar (admin/test1234)
just test-integration
just compose-down
```

See [`docs/design.md`](docs/design.md) for the full design.
