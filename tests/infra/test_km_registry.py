"""Tests for DSW Registry KM version discovery."""

from __future__ import annotations

import json
from pathlib import Path

from dsw_translation_tool.km_registry import (
    discover_km_versions,
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
