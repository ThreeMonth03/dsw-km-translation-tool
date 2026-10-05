"""Prove malicious render resources never reach an unapproved local HTTP server."""

from __future__ import annotations

import threading
import time
from contextlib import ExitStack
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from playwright.sync_api import expect, sync_playwright

from dsw_km_translation_tool.browser_network import install_browser_network_policy


def main() -> None:
    hits: list[str] = []

    class Sink(BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def do_POST(self):
            hits.append(self.path)
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args):
            pass

    with ExitStack() as stack:
        sink = ThreadingHTTPServer(("127.0.0.1", 0), Sink)
        external = f"http://127.0.0.1:{sink.server_port}"

        class Client(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/redirect":
                    self.send_response(302)
                    self.send_header("Location", external + "/redirected")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<p>Allowed loopback page</p>")

            def do_POST(self):
                self.send_response(307 if self.path == "/post-redirect-307" else 302)
                self.send_header("Location", external + "/post-redirected")
                self.end_headers()

            def log_message(self, *_args):
                pass

        client = ThreadingHTTPServer(("127.0.0.1", 0), Client)
        for server in (sink, client):
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            stack.callback(server.server_close)
            stack.callback(thread.join, 2)
            stack.callback(server.shutdown)
        origin = f"http://127.0.0.1:{client.server_port}"
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            context = browser.new_context(service_workers="block")
            blocked = install_browser_network_policy(context, client=origin, api=origin)
            page = context.new_page()
            page.goto(origin)
            expect(page.locator("p")).to_have_text("Allowed loopback page")
            result = page.evaluate(
                """async external => {
                    const fetchBlocked = url => fetch(url).then(() => false, () => true);
                    const image = new Promise(resolve => {
                        const img = document.createElement('img');
                        img.onload = () => resolve(false);
                        img.onerror = () => resolve(true);
                        img.src = external + '/image';
                        document.body.append(img);
                    });
                    new WebSocket(external.replace('http:', 'ws:') + '/socket');
                    return await Promise.race([
                        Promise.all([
                            fetchBlocked(external + '/fetch'), fetchBlocked('/redirect'), image,
                            fetch('/post-redirect', {method: 'POST'}).then(() => false, () => true),
                            fetch('/post-redirect-307', {method: 'POST', body: 'test'}).then(() => false, () => true),
                        ]),
                        new Promise((_, reject) => setTimeout(() => reject('Network regression timed out'), 5000)),
                    ]);
                }""",
                external,
            )
            assert result == [True, True, True, True, True], result
            deadline = time.monotonic() + 3
            while not blocked["websocket"] and time.monotonic() < deadline:
                page.wait_for_timeout(100)
            # CSP may block an external request before it reaches a route.
            assert blocked["http"] >= 1 and blocked["websocket"] == 1, blocked
            assert not hits, f"Blocked resource reached the sink: {hits}"
            assert not context.service_workers
            browser.close()
    print("Browser isolation passed: images, fetch, redirects and WebSockets blocked.")


if __name__ == "__main__":
    main()
