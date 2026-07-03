"""Async HTTP client for the AdGuard Home control API.

The client wraps a single :class:`httpx.AsyncClient`, targets the ``/control``
base path, and maps transport/HTTP failures onto the :mod:`adguardctl`
exception hierarchy. It supports both HTTP Basic auth and session-cookie login
(``POST /control/login``), transparently falling back to cookie login when an
endpoint answers ``401``/``403`` to a Basic-auth request.

The request/error-mapping semantics intentionally mirror the reference
``python-adguardhome`` library while using ``httpx`` instead of ``aiohttp``.
"""

from __future__ import annotations

from types import TracebackType
from typing import TYPE_CHECKING, Any, Self

import httpx

from .exceptions import AdGuardAuthError, AdGuardConnectionError, AdGuardError

if TYPE_CHECKING:
    from collections.abc import Mapping

_AUTH_STATUSES = frozenset({httpx.codes.UNAUTHORIZED, httpx.codes.FORBIDDEN})


class AdGuardClient:
    """Async client for a single AdGuard Home instance."""

    def __init__(  # noqa: PLR0913
        self,
        host: str,
        *,
        port: int = 3000,
        username: str | None = None,
        password: str | None = None,
        tls: bool = False,
        verify_ssl: bool = True,
        base_path: str = "/control",
        request_timeout: float = 10.0,
        session: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            host: Hostname or IP of the AdGuard Home instance.
            port: API port (default 3000).
            username: Username for authentication, if enabled.
            password: Password for authentication, if enabled.
            tls: Use https when True.
            verify_ssl: Verify TLS certificates (set False for self-signed).
            base_path: API base path, usually ``/control``.
            request_timeout: Per-request timeout in seconds.
            session: Optional externally-managed ``httpx.AsyncClient``.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.tls = tls
        self.verify_ssl = verify_ssl
        self.request_timeout = request_timeout

        scheme = "https" if tls else "http"
        normalized = base_path.strip("/")
        self.base_url = f"{scheme}://{host}:{port}/{normalized}/"

        self._session = session
        self._close_session = False
        self._logged_in = False

    def _ensure_session(self) -> httpx.AsyncClient:
        """Return the session, lazily creating one we own if needed."""
        if self._session is None:
            self._session = httpx.AsyncClient(
                base_url=self.base_url,
                verify=self.verify_ssl,
                timeout=httpx.Timeout(self.request_timeout),
            )
            self._close_session = True
        return self._session

    def _basic_auth(self) -> httpx.BasicAuth | None:
        if self.username and self.password:
            return httpx.BasicAuth(self.username, self.password)
        return None

    async def _login(self) -> bool:
        """Attempt cookie-session login. Returns True on success."""
        if not (self.username and self.password):
            return False
        session = self._ensure_session()
        try:
            response = await session.post(
                "login",
                json={"name": self.username, "password": self.password},
            )
        except httpx.TimeoutException as exc:
            msg = "Timeout occurred while logging in to AdGuard Home."
            raise AdGuardConnectionError(msg) from exc
        except httpx.TransportError as exc:
            msg = "Error occurred while logging in to AdGuard Home."
            raise AdGuardConnectionError(msg) from exc
        if response.status_code == httpx.codes.OK:
            self._logged_in = True
            return True
        return False

    async def request(
        self,
        uri: str,
        *,
        method: str = "GET",
        json_data: Any | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        """Perform a request and return the decoded response.

        Args:
            uri: Path relative to the control base path, e.g. ``"status"``.
            method: HTTP method.
            json_data: Body to send as JSON.
            params: Query parameters.

        Returns:
            Decoded JSON (dict or list) when the response is JSON, otherwise a
            ``{"message": <text>}`` dict.

        Raises:
            AdGuardAuthError: Authentication missing or rejected.
            AdGuardConnectionError: Transport failure or timeout.
            AdGuardError: Any other non-2xx response.
        """
        response = await self._send(
            uri, method=method, json_data=json_data, params=params
        )

        if response.status_code in _AUTH_STATUSES:
            # Basic auth (or no auth) was rejected; try cookie login then retry.
            if await self._login():
                response = await self._send(
                    uri, method=method, json_data=json_data, params=params
                )
            if response.status_code in _AUTH_STATUSES:
                msg = "Authentication failed for AdGuard Home (check credentials)."
                raise AdGuardAuthError(
                    msg,
                    status=response.status_code,
                    body=self._decode(response),
                )

        if response.is_error:
            raise AdGuardError(
                f"AdGuard Home returned HTTP {response.status_code} for {uri}",
                status=response.status_code,
                body=self._decode(response),
            )

        return self._decode(response)

    async def _send(
        self,
        uri: str,
        *,
        method: str,
        json_data: Any | None,
        params: Mapping[str, Any] | None,
    ) -> httpx.Response:
        session = self._ensure_session()
        try:
            return await session.request(
                method,
                uri,
                json=json_data,
                params=params,
                auth=self._basic_auth(),
                headers={"Accept": "application/json, text/plain, */*"},
            )
        except httpx.TimeoutException as exc:
            msg = "Timeout occurred while connecting to AdGuard Home."
            raise AdGuardConnectionError(msg) from exc
        except httpx.TransportError as exc:
            msg = "Error occurred while communicating with AdGuard Home."
            raise AdGuardConnectionError(msg) from exc

    @staticmethod
    def _decode(response: httpx.Response) -> Any:
        content_type = response.headers.get("Content-Type", "")
        if "application/json" in content_type:
            return response.json()
        return {"message": response.text}

    async def close(self) -> None:
        """Close the session if we created it."""
        if self._session is not None and self._close_session:
            await self._session.aclose()
            self._session = None

    async def __aenter__(self) -> Self:
        """Enter the async context, returning self."""
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc: BaseException | None,
        _tb: TracebackType | None,
    ) -> None:
        """Exit the async context, closing any owned session."""
        await self.close()
