"""Tests for Localize/Weblate PO source pulls."""

from __future__ import annotations

from pathlib import Path

from dsw_translation_tool.localize_sync import pull_localize_po
from tests.infra.test_translation_repository_config import write_config


def test_pull_localize_po_initializes_base_and_latest(workspace: Path) -> None:
    """Verify the first pull writes both base and latest snapshots."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path)

    result = pull_localize_po(
        config_path=config_path,
        repo_root=workspace,
        downloader=lambda _url: b"new po",
    )

    assert result.changed is True
    assert result.initialized is True
    assert result.latest_po_path.read_bytes() == b"new po"
    assert result.base_po_path.read_bytes() == b"new po"


def test_pull_localize_po_uses_single_download_url_for_all_km_versions(workspace: Path) -> None:
    """Verify Localize pulls use the rolling project URL for any KM version."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path, supported_versions=["2.7.0", "2.8.0"])
    requested_urls: list[str] = []

    result = pull_localize_po(
        config_path=config_path,
        repo_root=workspace,
        km_version="2.8.0",
        downloader=lambda url: requested_urls.append(url) or b"new po",
    )

    expected_url = (
        "https://localize.ds-wizard.org/download/knowledge-models/"
        "common-dsw-knowledge-model/zh_Hant/"
    )
    assert requested_urls == [expected_url]
    assert result.url == expected_url


def test_pull_localize_po_updates_base_from_previous_latest(workspace: Path) -> None:
    """Verify changed pulls preserve the previous latest snapshot as base."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    latest_path = workspace / "sources/localize/zh_Hant/latest.po"
    base_path = workspace / "sources/localize/zh_Hant/base.po"
    latest_path.parent.mkdir(parents=True)
    latest_path.write_bytes(b"old latest")
    base_path.write_bytes(b"older base")

    result = pull_localize_po(
        config_path=config_path,
        repo_root=workspace,
        downloader=lambda _url: b"new latest",
    )

    assert result.changed is True
    assert result.initialized is False
    assert latest_path.read_bytes() == b"new latest"
    assert base_path.read_bytes() == b"old latest"


def test_pull_localize_po_leaves_snapshots_when_latest_is_unchanged(workspace: Path) -> None:
    """Verify unchanged pulls avoid touching base and latest snapshots."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    latest_path = workspace / "sources/localize/zh_Hant/latest.po"
    base_path = workspace / "sources/localize/zh_Hant/base.po"
    latest_path.parent.mkdir(parents=True)
    latest_path.write_bytes(b"same")
    base_path.write_bytes(b"base")

    result = pull_localize_po(
        config_path=config_path,
        repo_root=workspace,
        downloader=lambda _url: b"same",
    )

    assert result.changed is False
    assert result.initialized is False
    assert latest_path.read_bytes() == b"same"
    assert base_path.read_bytes() == b"base"
