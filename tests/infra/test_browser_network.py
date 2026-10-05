"""Exact-origin isolation is installed before render requests are sent."""

from types import SimpleNamespace

import pytest

from dsw_km_translation_tool.browser_network import install_browser_network_policy


class Context:
    def route(self, pattern, handler):
        assert pattern == "**/*"
        self.http = handler

    def route_web_socket(self, pattern, handler):
        assert pattern == "**/*"
        self.websocket = handler

    def grant_permissions(self, permissions, *, origin):
        self.permission = (permissions, origin)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080.evil.test/path",
        "http://127.0.0.1:8081/path",
        "http://localhost:8080/path",
        "https://127.0.0.1:8080/path",
        "file:///etc/passwd",
        "http://user:password@127.0.0.1:8080/path",
        "http://169.254.169.254/latest/meta-data/",
    ],
)
def test_external_or_lookalike_origins_never_fetch(url):
    context = Context()
    install_browser_network_policy(
        context, client="http://127.0.0.1:8080", api="http://127.0.0.1:3000"
    )
    aborted = []
    route = SimpleNamespace(
        request=SimpleNamespace(url=url),
        abort=aborted.append,
        fetch=lambda **_: pytest.fail("network"),
    )
    context.http(route)
    assert aborted == ["blockedbyclient"]


def test_redirect_does_not_follow_external_destination():
    context = Context()
    install_browser_network_policy(
        context, client="http://127.0.0.1:8080", api="http://127.0.0.1:3000"
    )
    fetched, aborted = [], []
    response = SimpleNamespace(
        headers={"location": "http://127.0.0.1:9000/secret"}, dispose=lambda: None
    )
    route = SimpleNamespace(
        request=SimpleNamespace(url="http://127.0.0.1:8080/redirect", method="GET"),
        abort=aborted.append,
        fetch=lambda **kwargs: fetched.append(kwargs) or response,
    )
    context.http(route)
    assert fetched == [{"max_redirects": 0, "timeout": 30000}]
    assert aborted == ["blockedbyclient"]


def test_csp_allows_service_origins_not_only_base_paths():
    context = Context()
    install_browser_network_policy(
        context,
        client="http://127.0.0.1:8080/wizard",
        api="http://127.0.0.1:3000/wizard-api",
    )
    fulfilled = []
    response = SimpleNamespace(headers={"content-type": "text/html"}, dispose=lambda: None)
    route = SimpleNamespace(
        request=SimpleNamespace(url="http://127.0.0.1:8080/wizard/login", method="GET"),
        fetch=lambda **_: response,
        fulfill=lambda **kwargs: fulfilled.append(kwargs),
    )
    context.http(route)
    policy = fulfilled[0]["headers"]["content-security-policy"]
    assert "connect-src http://127.0.0.1:3000 http://127.0.0.1:8080;" in policy
    assert "/wizard" not in policy
    assert context.permission == (["local-network-access"], "http://127.0.0.1:8080")


def test_uploads_preserve_browser_multipart_body():
    context = Context()
    install_browser_network_policy(
        context,
        client="http://127.0.0.1:8080/wizard",
        api="http://127.0.0.1:3000/wizard-api",
    )
    continued = []
    context.http(
        SimpleNamespace(
            request=SimpleNamespace(url="http://127.0.0.1:3000/wizard-api/locales", method="POST"),
            continue_=lambda: continued.append(True),
            fetch=lambda **_: pytest.fail("multipart replay"),
        )
    )
    assert continued == [True]


@pytest.mark.parametrize(
    "url", ["https://dsw.example", "http://localhost:8080", "http://127.0.0.1"]
)
def test_policy_cannot_authorize_production_or_implicit_ports(url):
    with pytest.raises(ValueError, match="explicit loopback"):
        install_browser_network_policy(Context(), client=url, api="http://127.0.0.1:3000")
