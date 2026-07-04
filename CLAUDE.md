# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

`adguardctl` is an async-first Python CLI for managing an [AdGuard Home](https://adguard.com/adguard-home/overview.html)
instance (DNS, filters, clients, rewrites, access lists, encryption, stats, query log).
Full design and endpoint coverage matrix live in [`docs/design.md`](docs/design.md).

## Commands

All dev tasks go through `just` (the justfile is the source of truth); dependencies are
managed with `uv` — add them only via `uv add` / `uv add --dev`, never by editing
`pyproject.toml` by hand.

```bash
just check          # CI gate: format-check + lint + type + unit tests. Run before claiming done.
just test           # unit tests only (respx-mocked HTTP, coverage; -m "not slow")
just type           # ty check (primary type checker)
just lint           # ruff check
just format         # ruff format (write); `just format-check` for CI-style check
just spell          # codespell src tests

just run ARGS...    # run the CLI (e.g. `just run status --json`)
just dev ARGS...    # run against the local compose instance (localhost:3000, admin/test1234)

just compose-up          # start AdGuard Home + Unbound test stack
just test-integration    # integration tests (need the stack up; marked `integration`+`slow`)
just compose-down
```

Run a single test: `uv run pytest tests/unit/test_api.py::test_name`. Integration tests are
opt-in — they only run with `--slow` and a live compose stack (skipped otherwise).

Type-checking uses **`ty`** as the primary checker; **basedpyright** is a secondary aid run in
standard (not strict) mode. Ruff is `select = ["ALL"]` with a pragmatic ignore set in
`pyproject.toml` (mostly Typer/Pydantic-idiom exemptions). Unit coverage gate is **≥85%**.

## Architecture

Four layers, each depending only on the one below:

```
cli/ (Typer)  →  api.py (AdGuard facade + per-area classes)  →  client.py (httpx)  →  AdGuard Home /control
                        ↑ models.py (Pydantic v2)                     ↑ config.py (layered Settings)
                        render.py (Rich tables / JSON)
```

- **`client.AdGuardClient`** — single `httpx.AsyncClient`, base path `/control`, async context
  manager. Auth is HTTP Basic with automatic session-cookie login fallback (`POST /control/login`
  when Basic is rejected). Error mapping: non-2xx → `AdGuardError`, transport/timeout →
  `AdGuardConnectionError`, 401/403 after login retry → `AdGuardAuthError` (all in `exceptions.py`).
- **`api.AdGuard`** — facade composing one class per feature area (`SettingsAPI`, `DnsAPI`,
  `ClientsAPI`, …), each returning validated Pydantic models. Build it via
  `AdGuard.from_settings(Settings)`. `AdGuard.export()` fans out concurrently over the raw config
  endpoints (`EXPORT_ENDPOINTS`) and returns **full-fidelity raw JSON** (not the typed models) —
  a failed/absent endpoint maps to `None` rather than failing the whole export.
- **`models.py`** — Pydantic v2 with `extra="ignore"` for forward compatibility, so typed `--json`
  reads deliberately drop unknown fields (that's why `export` exists — to preserve them).
- **`config.load_settings`** — precedence (highest wins): **CLI flags > env (`AGH_*`) > TOML file**
  (`~/.config/adguardctl/config.toml`, `[profiles.*]` or bare top-level keys as implicit `default`).
- **`cli/`** — root app in `cli/app.py` (global options resolved into `AppState` on the typer
  context), one sub-app module per area. The shared `run_async` helper in `cli/_common.py` resolves
  settings, runs the coroutine against an `AdGuard`, and converts errors to exit codes
  (**2 = misconfiguration**, **1 = runtime/API error**). Output goes through `render.py`
  (`console`/`err_console`, `emit_json`, `kv_table`); the global `--json` flag switches every
  command to machine-readable output.

### Adding a new command area

1. Add the endpoint methods to a new `*API` class in `api.py` and register it as an attribute in
   `AdGuard.__init__`.
2. Add response `models.py` types (Pydantic v2, `extra="ignore"`).
3. Create `cli/<area>.py` with a `typer.Typer()` `app`; each command calls
   `run_async(ctx, lambda a: a.<area>.<method>(...))` and renders via `render.py`, honoring
   `get_state(ctx).as_json`.
4. Register it in `cli/app.py` with `app.add_typer(<area>.app, name="<area>")`.
5. Add unit tests (respx-mocked from a `tests/fixtures/*.json` file; Typer `CliRunner` for the
   command surface).

## Scope

DHCP (`/dhcp/*`) is intentionally excluded. DNS (`/dns_config`) and TLS (`/tls/configure`) *write*
operations are phase-2 (read-only for now) — see the `TODO(phase-2)` markers in `api.py`.
