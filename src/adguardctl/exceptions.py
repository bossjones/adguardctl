"""Exception hierarchy for adguardctl.

Mirrors the error-mapping semantics of the reference ``python-adguardhome``
library, but adds a dedicated authentication error so the CLI can give a clear
message when credentials are missing or rejected.
"""

from __future__ import annotations

from typing import Any


class AdGuardError(Exception):
    """Base error for any failure talking to AdGuard Home.

    Args:
        message: Human-readable description of the failure.
        status: HTTP status code, when the failure came from an HTTP response.
        body: Parsed response body (dict) or raw text, when available.
    """

    def __init__(
        self,
        message: str,
        *,
        status: int | None = None,
        body: Any | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status = status
        self.body = body


class AdGuardConnectionError(AdGuardError):
    """Raised when the instance is unreachable or times out."""


class AdGuardAuthError(AdGuardError):
    """Raised when authentication is missing or rejected (401/403)."""
