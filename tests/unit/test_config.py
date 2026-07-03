"""Unit tests for :mod:`adguardctl.config`."""

from __future__ import annotations

from pathlib import Path

import pytest

from adguardctl.config import Settings, load_settings

TOML_WITH_PROFILES = """
default_profile = "home"

[profiles.home]
host = "adguard.local"
port = 80
username = "admin"
password = "secret"
tls = false

[profiles.work]
host = "10.0.0.2"
port = 3000
"""

TOML_BARE = """
host = "bare.local"
port = 8080
"""


@pytest.fixture
def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in (
        "AGH_HOST",
        "AGH_PORT",
        "AGH_USERNAME",
        "AGH_PASSWORD",
        "AGH_TLS",
        "AGH_VERIFY_SSL",
        "AGH_BASE_PATH",
        "AGH_TIMEOUT",
        "AGH_PROFILE",
    ):
        monkeypatch.delenv(var, raising=False)


def _write(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(content)
    return path


@pytest.mark.usefixtures("_clear_env")
def test_toml_default_profile(tmp_path: Path) -> None:
    settings = load_settings(config_path=_write(tmp_path, TOML_WITH_PROFILES))
    assert settings.host == "adguard.local"
    assert settings.port == 80
    assert settings.username == "admin"


@pytest.mark.usefixtures("_clear_env")
def test_toml_explicit_profile(tmp_path: Path) -> None:
    settings = load_settings(
        profile="work",
        config_path=_write(tmp_path, TOML_WITH_PROFILES),
    )
    assert settings.host == "10.0.0.2"
    assert settings.port == 3000


@pytest.mark.usefixtures("_clear_env")
def test_bare_toml_is_default(tmp_path: Path) -> None:
    settings = load_settings(config_path=_write(tmp_path, TOML_BARE))
    assert settings.host == "bare.local"
    assert settings.port == 8080


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGH_HOST", "env.local")
    monkeypatch.setenv("AGH_PORT", "9999")
    monkeypatch.setenv("AGH_TLS", "true")
    settings = load_settings(config_path=_write(tmp_path, TOML_WITH_PROFILES))
    assert settings.host == "env.local"
    assert settings.port == 9999
    assert settings.tls is True


@pytest.mark.usefixtures("_clear_env")
def test_flags_override_env_and_toml(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGH_HOST", "env.local")
    settings = load_settings(
        config_path=_write(tmp_path, TOML_WITH_PROFILES),
        overrides={"host": "flag.local", "port": None},
    )
    assert settings.host == "flag.local"
    # port None override is ignored; env has no port, so TOML wins.
    assert settings.port == 80


@pytest.mark.usefixtures("_clear_env")
def test_env_profile_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("AGH_PROFILE", "work")
    settings = load_settings(config_path=_write(tmp_path, TOML_WITH_PROFILES))
    assert settings.host == "10.0.0.2"


@pytest.mark.usefixtures("_clear_env")
def test_missing_file_requires_host(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="host"):
        load_settings(config_path=tmp_path / "nope.toml")


@pytest.mark.usefixtures("_clear_env")
def test_defaults_applied(tmp_path: Path) -> None:
    settings = load_settings(config_path=_write(tmp_path, TOML_BARE))
    assert settings.tls is False
    assert settings.verify_ssl is True
    assert settings.base_path == "/control"
    assert settings.request_timeout == 10.0


def test_settings_rejects_zero_timeout() -> None:
    with pytest.raises(ValueError, match="request_timeout"):
        Settings(host="x", request_timeout=0)
