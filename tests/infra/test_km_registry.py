"""Tests for DSW Registry KM version discovery."""

from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread

from dsw_translation_tool.km_registry import (
    discover_km_versions,
    render_km_version_discovery_markdown,
    write_km_version_discovery_markdown,
    write_km_version_discovery_report,
)
from tests.infra.test_translation_repository_config import write_config


def test_discover_km_versions_reports_new_and_missing_versions(workspace: Path) -> None:
    """Verify Registry package listings are compared with configured versions."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path, supported_versions=["2.6.0", "2.7.0"])
    requested_urls: list[str] = []

    def downloader(url: str) -> bytes:
        requested_urls.append(url)
        return json.dumps(
            [
                {
                    "organizationId": "dsw",
                    "kmId": "root",
                    "version": "2.7.0",
                    "name": "Common DSW Knowledge Model",
                    "metamodelVersion": 19,
                    "createdAt": "2025-12-18T12:34:17.747925Z",
                    "organization": {"logo": "ignored"},
                },
                {
                    "organizationId": "dsw",
                    "kmId": "root",
                    "version": "2.8.0",
                    "name": "Common DSW Knowledge Model",
                    "createdAt": "2026-01-01T00:00:00Z",
                },
            ]
        ).encode("utf-8")

    result = discover_km_versions(config_path=config_path, downloader=downloader)

    assert requested_urls == [
        "https://api.registry.ds-wizard.org/knowledge-model-packages?organizationId=dsw&kmId=root"
    ]
    assert result.configured_versions == ("2.6.0", "2.7.0")
    assert result.registry_versions == ("2.7.0", "2.8.0")
    assert result.new_versions == ("2.8.0",)
    assert result.missing_versions == ("2.6.0",)
    assert result.latest_configured_version == "2.7.0"
    assert result.latest_registry_version == "2.8.0"
    assert result.packages[0].metamodel_version == 19


def test_write_km_version_discovery_report_is_stable_json(workspace: Path) -> None:
    """Verify discovery reports omit unrelated Registry payload fields."""

    config_path = workspace / "translation-config.yml"
    report_path = workspace / "reviews" / "km_version_discovery.json"
    write_config(config_path)
    result = discover_km_versions(
        config_path=config_path,
        downloader=lambda _url: json.dumps(
            [
                {
                    "organizationId": "dsw",
                    "kmId": "root",
                    "version": "2.7.0",
                    "name": "Common DSW Knowledge Model",
                    "organization": {"logo": "ignored"},
                }
            ]
        ).encode("utf-8"),
    )

    write_km_version_discovery_report(result=result, report_path=report_path)

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["configured_versions"] == ["2.7.0"]
    assert report["registry_versions"] == ["2.7.0"]
    assert report["new_versions"] == []
    assert "organization" not in report["packages"][0]


def test_render_km_version_discovery_markdown_reports_follow_up(workspace: Path) -> None:
    """Verify Markdown output highlights newly published KM versions."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    result = discover_km_versions(
        config_path=config_path,
        downloader=lambda _url: json.dumps(
            [
                {
                    "organizationId": "dsw",
                    "kmId": "root",
                    "version": "2.7.0",
                    "name": "Common DSW Knowledge Model",
                    "metamodelVersion": 19,
                    "createdAt": "2025-12-18T12:34:17.747925Z",
                },
                {
                    "organizationId": "dsw",
                    "kmId": "root",
                    "version": "2.8.0",
                    "name": "Common DSW Knowledge Model",
                },
            ]
        ).encode("utf-8"),
    )

    markdown = render_km_version_discovery_markdown(result)

    assert "## KM Version Monitor" in markdown
    assert "Status: **new version available**" in markdown
    assert "| New versions | `2.8.0` |" in markdown
    assert "Run the KM update runbook" in markdown
    assert "| 2.7.0 | Common DSW Knowledge Model | 19 |" in markdown


def test_write_km_version_discovery_markdown_appends_report(workspace: Path) -> None:
    """Verify Markdown report writing is suitable for GitHub step summaries."""

    config_path = workspace / "translation-config.yml"
    report_path = workspace / "reviews" / "km_version_discovery.md"
    write_config(config_path)
    result = discover_km_versions(
        config_path=config_path,
        downloader=lambda _url: json.dumps(
            [
                {
                    "organizationId": "dsw",
                    "kmId": "root",
                    "version": "2.7.0",
                    "name": "Common DSW Knowledge Model",
                }
            ]
        ).encode("utf-8"),
    )

    write_km_version_discovery_markdown(result=result, report_path=report_path)

    report = report_path.read_text(encoding="utf-8")
    assert "Status: **current**" in report
    assert "| New versions | (none) |" in report


def test_discover_km_versions_cli_writes_markdown_outputs(
    repo_root: Path,
    workspace: Path,
) -> None:
    """Verify the discovery CLI writes JSON, details, and summary reports."""

    config_path = workspace / "translation-config.yml"
    report_path = workspace / "reviews" / "km_version_discovery.json"
    details_path = workspace / "reviews" / "km_version_discovery.md"
    summary_path = workspace / "summary.md"
    registry_requests: list[str] = []
    registry_payload = json.dumps(
        [
            {
                "organizationId": "dsw",
                "kmId": "root",
                "version": "2.7.0",
                "name": "Common DSW Knowledge Model",
            }
        ]
    ).encode("utf-8")

    class RegistryHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            registry_requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(registry_payload)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    registry_server = ThreadingHTTPServer(("127.0.0.1", 0), RegistryHandler)
    registry_thread = Thread(target=registry_server.serve_forever, daemon=True)
    registry_thread.start()
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "api_url: https://api.registry.ds-wizard.org",
            f"api_url: http://127.0.0.1:{registry_server.server_port}",
        ),
        encoding="utf-8",
    )
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(repo_root / "src" / "discover_km_versions.py"),
                "--repo-root",
                str(workspace),
                "--config",
                str(config_path),
                "--report",
                str(report_path),
                "--details-out",
                str(details_path),
                "--summary",
                str(summary_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
    finally:
        registry_server.shutdown()
        registry_server.server_close()
        registry_thread.join(timeout=5)

    assert registry_requests == ["/knowledge-model-packages?organizationId=dsw&kmId=root"]
    assert "## KM Version Monitor" in result.stdout
    assert json.loads(report_path.read_text(encoding="utf-8"))["new_versions"] == []
    assert "Status: **current**" in details_path.read_text(encoding="utf-8")
    assert "Status: **current**" in summary_path.read_text(encoding="utf-8")
