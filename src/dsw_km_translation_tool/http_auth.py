"""HTTP authentication helpers shared by download clients."""

from __future__ import annotations


def bearer_authorization_header(token: str) -> str:
    """Return a standard Authorization header value for an API token."""

    stripped = token.strip()
    if stripped.lower().startswith(("bearer ", "token ")):
        return stripped
    return f"Bearer {stripped}"


def token_authorization_header(token: str) -> str:
    """Return a Weblate-style token Authorization header value."""

    stripped = token.strip()
    if stripped.lower().startswith(("bearer ", "token ")):
        return stripped
    return f"Token {stripped}"
