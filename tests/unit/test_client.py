"""Unit tests for :mod:`adguardctl.client`."""

from __future__ import annotations

import httpx
import pytest
import respx

from adguardctl.client import AdGuardClient
from adguardctl.exceptions import (
    AdGuardAuthError,
    AdGuardConnectionError,
    AdGuardError,
)

BASE = "http://adguard.local:3000/control"


def test_base_url_http() -> None:
    client = AdGuardClient("adguard.local")
    assert client.base_url == "http://adguard.local:3000/control/"


def test_base_url_https_and_port() -> None:
    client = AdGuardClient("adguard.local", port=443, tls=True)
    assert client.base_url == "https://adguard.local:443/control/"


@respx.mock
async def test_get_json_returns_dict() -> None:
    respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(200, json={"protection_enabled": True}),
    )
    async with AdGuardClient("adguard.local") as client:
        result = await client.request("status")
    assert result == {"protection_enabled": True}


@respx.mock
async def test_non_json_wrapped_in_message() -> None:
    respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(
            200, text="OK", headers={"Content-Type": "text/plain"}
        ),
    )
    async with AdGuardClient("adguard.local") as client:
        result = await client.request("status")
    assert result == {"message": "OK"}


@respx.mock
async def test_post_json_body() -> None:
    route = respx.post(f"{BASE}/protection").mock(
        return_value=httpx.Response(200, text="")
    )
    async with AdGuardClient("adguard.local") as client:
        await client.request("protection", method="POST", json_data={"enabled": True})
    assert route.called
    assert route.calls.last.request.content == b'{"enabled":true}'


@respx.mock
async def test_4xx_raises_adguard_error() -> None:
    respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(400, json={"message": "bad"}),
    )
    async with AdGuardClient("adguard.local") as client:
        with pytest.raises(AdGuardError) as excinfo:
            await client.request("status")
    assert excinfo.value.status == 400
    assert excinfo.value.body == {"message": "bad"}


@respx.mock
async def test_timeout_raises_connection_error() -> None:
    respx.get(f"{BASE}/status").mock(side_effect=httpx.ConnectTimeout("boom"))
    async with AdGuardClient("adguard.local") as client:
        with pytest.raises(AdGuardConnectionError):
            await client.request("status")


@respx.mock
async def test_transport_error_raises_connection_error() -> None:
    respx.get(f"{BASE}/status").mock(side_effect=httpx.ConnectError("nope"))
    async with AdGuardClient("adguard.local") as client:
        with pytest.raises(AdGuardConnectionError):
            await client.request("status")


@respx.mock
async def test_basic_auth_header_sent() -> None:
    route = respx.get(f"{BASE}/status").mock(
        return_value=httpx.Response(200, json={"ok": True}),
    )
    async with AdGuardClient(
        "adguard.local", username="admin", password="pw"
    ) as client:
        await client.request("status")
    assert route.calls.last.request.headers["Authorization"].startswith("Basic ")


@respx.mock
async def test_cookie_login_fallback_on_401() -> None:
    # First status call 401s; login succeeds; retried status returns 200.
    status_route = respx.get(f"{BASE}/status")
    status_route.side_effect = [
        httpx.Response(401),
        httpx.Response(200, json={"protection_enabled": True}),
    ]
    login_route = respx.post(f"{BASE}/login").mock(return_value=httpx.Response(200))
    async with AdGuardClient(
        "adguard.local", username="admin", password="pw"
    ) as client:
        result = await client.request("status")
    assert login_route.called
    assert result == {"protection_enabled": True}


@respx.mock
async def test_auth_error_when_login_fails() -> None:
    respx.get(f"{BASE}/status").mock(return_value=httpx.Response(403))
    respx.post(f"{BASE}/login").mock(return_value=httpx.Response(403))
    async with AdGuardClient(
        "adguard.local", username="admin", password="bad"
    ) as client:
        with pytest.raises(AdGuardAuthError):
            await client.request("status")
