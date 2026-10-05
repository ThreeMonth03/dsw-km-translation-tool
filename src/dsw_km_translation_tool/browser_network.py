"""Confine disposable locale-review browsers to the DSW client and API."""

from __future__ import annotations

from urllib.parse import urljoin, urlsplit


def _origin(url: str) -> tuple[str, str, int | None] | None:
    try:
        parsed = urlsplit(url)
        if parsed.username is not None or parsed.password is not None:
            return None
        return parsed.scheme, parsed.hostname or "", parsed.port
    except ValueError:
        return None


def install_browser_network_policy(context, *, client: str, api: str) -> dict[str, int]:
    """Block external HTTP, redirects and WebSockets before creating any page.

    The caller must create the context with service_workers="block" so workers
    cannot bypass request interception. APIRequestContext calls remain explicit
    test operations and are not controlled by this browser route.
    """
    origins = {_origin(url) for url in (client, api)}
    blocked = {"http": 0, "websocket": 0}
    if any(
        origin is None or origin[:2] != ("http", "127.0.0.1") or not origin[2] for origin in origins
    ):
        raise ValueError("Locale review requires explicit loopback client and API ports")
    allowed = " ".join(f"http://127.0.0.1:{origin[2]}" for origin in sorted(origins))
    csp = (
        f"default-src {allowed} data: blob: 'unsafe-inline'; "
        f"connect-src {allowed}; frame-src {allowed}; form-action {allowed}; "
        "object-src 'none'; base-uri 'none'"
    )

    def handle(route):
        if _origin(route.request.url) not in origins:
            blocked["http"] += 1
            route.abort("blockedbyclient")
            return
        if route.request.method not in {"GET", "HEAD"}:
            # Browser multipart uploads include files that request replay cannot
            # recover. Preserve them; the document CSP also guards redirect egress.
            route.continue_()
            return
        # Do not let a trusted-origin redirect silently reach another service.
        response = route.fetch(max_redirects=0, timeout=30000)
        location = response.headers.get("location")
        if location and _origin(urljoin(route.request.url, location)) not in origins:
            blocked["http"] += 1
            route.abort("blockedbyclient")
        else:
            route.fulfill(
                response=response,
                headers={**response.headers, "content-security-policy": csp},
            )
        response.dispose()

    context.route("**/*", handle)

    def isolate_socket(socket):
        blocked["websocket"] += 1
        # A routed socket never connects upstream unless connect_to_server is
        # called. Discard frames locally instead of opening a runner connection.
        socket.on_message(lambda _message: None)

    context.route_web_socket("**/*", isolate_socket)
    # Fulfilled documents need Chromium's loopback permission for real browser
    # uploads. Scope it to the client origin; routes and CSP still restrict targets.
    client_origin = _origin(client)
    context.grant_permissions(
        ["local-network-access"], origin=f"http://127.0.0.1:{client_origin[2]}"
    )
    return blocked
