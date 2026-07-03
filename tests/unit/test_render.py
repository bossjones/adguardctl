"""Tests for :mod:`adguardctl.render`."""

from __future__ import annotations

import json

from adguardctl.models import RewriteEntry, ServerStatus
from adguardctl.render import (
    bullet_list,
    console,
    emit_json,
    kv_table,
    list_table,
    success,
)


def test_emit_json_model(capsys) -> None:
    emit_json(ServerStatus(version="v1", protection_enabled=True))
    out = json.loads(capsys.readouterr().out)
    assert out["version"] == "v1"
    assert out["protection_enabled"] is True


def test_emit_json_list_of_models(capsys) -> None:
    emit_json([RewriteEntry(domain="a", answer="1.1.1.1")])
    out = json.loads(capsys.readouterr().out)
    assert out[0]["domain"] == "a"


def test_emit_json_nested_dict(capsys) -> None:
    emit_json({"wrap": [RewriteEntry(domain="a", answer="1.1.1.1")]})
    out = json.loads(capsys.readouterr().out)
    assert out["wrap"][0]["answer"] == "1.1.1.1"


def test_kv_table_renders_fields(capsys) -> None:
    kv_table("Title", ServerStatus(version="v9"))
    assert "version" in capsys.readouterr().out


def test_list_table_empty(capsys) -> None:
    list_table("T", [], [("Domain", "domain")], empty_message="nothing here")
    assert "nothing here" in capsys.readouterr().out


def test_list_table_rows(capsys) -> None:
    list_table(
        "T",
        [RewriteEntry(domain="a.local", answer="1.1.1.1", enabled=True)],
        [("Domain", "domain"), ("Answer", "answer"), ("On", "enabled")],
    )
    out = capsys.readouterr().out
    assert "a.local" in out


def test_bullet_list_populated_and_empty(capsys) -> None:
    bullet_list("Items", ["one", "two"])
    bullet_list("Empty", [], empty_message="none!")
    out = capsys.readouterr().out
    assert "one" in out
    assert "none!" in out


def test_success(capsys) -> None:
    success("done")
    assert "done" in capsys.readouterr().out


def test_console_is_console() -> None:
    from rich.console import Console  # noqa: PLC0415

    assert isinstance(console, Console)
