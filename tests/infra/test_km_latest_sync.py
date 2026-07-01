"""Tests for single-branch latest-KM synchronization helpers."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from dsw_translation_tool.km_latest_sync import (
    sync_latest_km_version,
    update_supported_versions_in_config,
)
from tests.infra.test_translation_repository_config import write_config


def registry_payload(*versions: str) -> bytes:
    """Build a minimal Registry package response."""

    return json.dumps(
        [
            {
                "organizationId": "dsw",
                "kmId": "root",
                "version": version,
                "name": "Common DSW Knowledge Model",
            }
            for version in versions
        ]
    ).encode("utf-8")


def test_sync_latest_km_noops_when_config_is_current(workspace: Path) -> None:
    """Verify latest-KM sync is a no-op when Registry and config agree."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path, supported_versions=["2.7.0"])

    result = sync_latest_km_version(
        repo_root=workspace,
        tooling_repo=workspace / "tooling",
        config_path=Path("translation-config.yml"),
        registry_token="",
        downloader=lambda _url: registry_payload("2.7.0"),
        skip_without_token=True,
    )

    assert result.changed is False
    assert result.configured_version == "2.7.0"
    assert result.registry_version == "2.7.0"
    assert result.skipped_reason is None


def test_sync_latest_km_skips_new_version_without_token(workspace: Path) -> None:
    """Verify new Registry versions can be safely skipped until a token is configured."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path, supported_versions=["2.7.0"])

    result = sync_latest_km_version(
        repo_root=workspace,
        tooling_repo=workspace / "tooling",
        config_path=Path("translation-config.yml"),
        registry_token="",
        downloader=lambda _url: registry_payload("2.7.0", "2.8.0"),
        skip_without_token=True,
    )

    assert result.changed is False
    assert result.configured_version == "2.7.0"
    assert result.registry_version == "2.8.0"
    assert result.skipped_reason == "missing-registry-token"


def test_update_supported_versions_in_config_adds_versions_once(workspace: Path) -> None:
    """Verify known KM versions are kept sorted and unique."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path, supported_versions=["2.7.0"])

    merged = update_supported_versions_in_config(config_path, ["2.8.0", "2.7.0", "v2.9.0"])

    assert merged == ("2.7.0", "2.8.0", "2.9.0")
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert payload["knowledge_model"]["supported_versions"] == ["2.7.0", "2.8.0", "2.9.0"]
