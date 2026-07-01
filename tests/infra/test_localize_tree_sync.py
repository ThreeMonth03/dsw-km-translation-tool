"""Tests for Localize/Weblate-to-tree refresh helpers."""

from __future__ import annotations

import shutil
from pathlib import Path

from dsw_translation_tool.ci_sync import CiSyncCommitConfig
from dsw_translation_tool.localize_tree_sync import refresh_tree_from_localize
from dsw_translation_tool.po import PoCatalogWriter
from dsw_translation_tool.workflow import TranslationWorkflowService
from tests.helpers import parse_po_entries, update_tree_field


def test_refresh_tree_from_localize_reexports_weblate_snapshot(
    repo_root: Path,
    po_path: Path,
    model_path: Path,
    workspace: Path,
) -> None:
    """Verify Localize refresh mirrors the latest PO into tree artifacts."""

    host_repo = workspace / "translation-repo"
    host_repo.mkdir()
    latest_po_path = host_repo / "sources" / "localize" / "zh_Hant" / "latest.po"
    source_km_path = (
        host_repo / "sources" / "knowledge-models" / "dsw-root-2.7.0" / "dsw-root-2.7.0.km"
    )
    latest_po_path.parent.mkdir(parents=True)
    source_km_path.parent.mkdir(parents=True)
    shutil.copy2(po_path, latest_po_path)
    shutil.copy2(model_path, source_km_path)

    entry = next(entry for entry in parse_po_entries(po_path) if entry.msgstr.strip())
    localize_text = "Localize Weblate tree refresh test"
    latest_po_path.write_text(
        PoCatalogWriter().rewrite_translations(
            original_po_path=str(po_path),
            translations_by_key={(entry.uuid, entry.field): localize_text},
        ),
        encoding="utf-8",
    )
    config = _build_refresh_config(
        host_repo=host_repo,
        tooling_repo=repo_root,
        latest_po_path=latest_po_path,
        source_km_path=source_km_path,
    )

    result = refresh_tree_from_localize(config=config, km_version="2.7.0")

    workflow = TranslationWorkflowService()
    scan_result = workflow.tree_repository.scan(str(host_repo / "tree"))
    assert result.version == "2.7.0"
    assert result.folder_count > 0
    assert result.root_count > 0
    assert result.shared_block_file_count > 0
    assert (host_repo / "tree" / "outline.md").exists()
    assert (host_repo / "tree" / "shared_blocks").is_dir()
    assert (host_repo / "tree" / "shared_blocks_outline.md").exists()
    assert not (host_repo / "tree" / "shared_blocks.md").exists()
    assert scan_result.translations[(entry.uuid, entry.field)] == localize_text


def test_refresh_tree_from_localize_overwrites_repo_tree_text(
    repo_root: Path,
    po_path: Path,
    model_path: Path,
    workspace: Path,
) -> None:
    """Verify Localize refresh treats Weblate as source of truth over Git text."""

    host_repo = workspace / "translation-repo"
    host_repo.mkdir()
    latest_po_path = host_repo / "sources" / "localize" / "zh_Hant" / "latest.po"
    source_km_path = (
        host_repo / "sources" / "knowledge-models" / "dsw-root-2.7.0" / "dsw-root-2.7.0.km"
    )
    latest_po_path.parent.mkdir(parents=True)
    source_km_path.parent.mkdir(parents=True)
    shutil.copy2(po_path, latest_po_path)
    shutil.copy2(model_path, source_km_path)

    entry = next(entry for entry in parse_po_entries(po_path) if entry.msgstr.strip())
    config = _build_refresh_config(
        host_repo=host_repo,
        tooling_repo=repo_root,
        latest_po_path=latest_po_path,
        source_km_path=source_km_path,
    )
    workflow = TranslationWorkflowService()
    refresh_tree_from_localize(config=config, km_version="2.7.0")
    scan_result = workflow.tree_repository.scan(str(host_repo / "tree"))
    update_tree_field(
        workflow=workflow,
        scan_result=scan_result,
        uuid=entry.uuid,
        field=entry.field,
        target_text="Git-only tree edit that should be replaced",
    )

    localize_text = "Localize wins over Git tree text"
    latest_po_path.write_text(
        PoCatalogWriter().rewrite_translations(
            original_po_path=str(po_path),
            translations_by_key={(entry.uuid, entry.field): localize_text},
        ),
        encoding="utf-8",
    )

    refresh_tree_from_localize(config=config, km_version="2.7.0")

    refreshed_scan = workflow.tree_repository.scan(str(host_repo / "tree"))
    assert refreshed_scan.translations[(entry.uuid, entry.field)] == localize_text


def _build_refresh_config(
    *,
    host_repo: Path,
    tooling_repo: Path,
    latest_po_path: Path,
    source_km_path: Path,
) -> CiSyncCommitConfig:
    """Build a refresh config with source paths relative to the host repo."""

    return CiSyncCommitConfig(
        host_repo_path=host_repo,
        tooling_repo_path=tooling_repo,
        translation_root=".",
        target_ref="master",
        mode="schedule",
        source_po_path=latest_po_path.relative_to(host_repo),
        source_km_path=source_km_path.relative_to(host_repo),
    )
