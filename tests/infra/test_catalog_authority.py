"""The upstream catalog remains usable when the context KM has different sources."""

from __future__ import annotations

import json
import shutil
import sys

import pytest

from dsw_km_translation_tool.alignment_status import build_alignment_status_report
from dsw_km_translation_tool.cli import report_localize_status
from dsw_km_translation_tool.github_translation_contributions import build_github_translation_report
from dsw_km_translation_tool.km_latest_sync import sync_latest_km_version
from dsw_km_translation_tool.locale_release import prepare_locale_release
from dsw_km_translation_tool.localize_sync import pull_localize_po
from dsw_km_translation_tool.native_locale import validate_native_locale
from dsw_km_translation_tool.po import PoCatalogParser
from dsw_km_translation_tool.translation_repository_build import (
    build_translation_repository,
)
from dsw_km_translation_tool.translation_repository_config import (
    load_translation_repository_config,
    version_paths,
)
from tests.infra.test_km_latest_sync import registry_payload
from tests.infra.test_locale_release import _commit
from tests.infra.test_translation_repository_config import write_config


@pytest.fixture
def catalog_repository(workspace, po_path, model_path):
    """A current Weblate snapshot with changed, fuzzy and catalog-only sources."""
    config_file = workspace / "translation-config.yml"
    write_config(config_file)
    paths = version_paths(load_translation_repository_config(config_file))
    km = workspace / paths.source_km_path
    km.parent.mkdir(parents=True)
    shutil.copyfile(model_path, km)
    entry = next(e for e in PoCatalogParser(str(po_path)).parse_entries() if e.msgid == "10 years")
    payload = (
        'msgid ""\nmsgstr ""\n'
        '"Project-Id-Version: Common DSW Knowledge Model 2.7.0\\n"\n'
        '"Language: zh_Hant\\n"\n'
        f'\n#: {entry.comment}\n#, fuzzy\nmsgid "11 years"\nmsgstr ""\n"十"\n"年"\n'
        "\n#: phase/ffffffff-ffff-4fff-8fff-ffffffffffff/title\n"
        'msgid "New upstream phase"\nmsgstr ""\n'
    ).encode()
    source = workspace / paths.source_po_path
    source.parent.mkdir(parents=True)
    source.write_bytes(payload)
    return workspace, config_file, paths, payload


def test_cross_version_export_is_lossless_and_editable(catalog_repository, workflow):
    root, config, paths, payload = catalog_repository
    model_bytes = (root / paths.source_km_path).read_bytes()
    result = build_translation_repository(repo_root=root, preserve_existing_translations=False)
    assert result.final_po_path.read_bytes() == payload
    assert result.source_km_path.read_bytes() == model_bytes
    entries = PoCatalogParser(str(result.source_po_path)).parse_entries()
    scan = workflow.tree_repository.scan(str(result.tree_dir))
    assert set(scan.translations) == {(entry.uuid, entry.field) for entry in entries}
    for entry in entries:
        state = scan.folders_by_uuid[entry.uuid].fields[entry.field]
        assert (state.source_text, state.target_text) == (entry.msgid, entry.msgstr)
    unknown = scan.folders_by_uuid["ffffffff-ffff-4fff-8fff-ffffffffffff"]
    assert "New upstream phase" in unknown.path
    assert unknown.event_type is None
    assert "/" not in unknown.path
    assert unknown.path.startswith("0002 ")  # Keep known KM roots ahead of catalog-only roots.
    report = validate_native_locale(
        po_path=result.final_po_path,
        km_path=result.source_km_path,
        target_language="zh_Hant",
    )
    assert report.total_messages == 2
    assert report.translated_messages == 0  # A fuzzy draft is not an accepted translation.
    assert report.model_report["missingEntities"] == 1
    assert report.model_report["mismatches"] >= 1
    alignment = build_alignment_status_report(
        repo_root=root, config_path=config, downloader=lambda _: payload
    )
    assert alignment.aligned and not alignment.failed
    assert alignment.to_dict()["status"] == "aligned"


def test_locale_release_does_not_require_matching_source_text(catalog_repository, tmp_path):
    root, config, _, payload = catalog_repository
    tool = tmp_path / "tool"
    tool.mkdir()
    (tool / "readme.md").write_text("Test tooling\n")
    tool_sha = _commit(tool)
    config.write_text(config.read_text().replace("ref: master", f"ref: {tool_sha}"))
    build_translation_repository(repo_root=root, preserve_existing_translations=False)
    _commit(root)
    manifest = prepare_locale_release(
        repo_root=root, tooling_repo=tool, tag="locale-zh_Hant-r1", output_dir=tmp_path / "release"
    )
    assert manifest["context_knowledge_model"]["package_id"] == "dsw:root:2.7.0"
    assert manifest["po"]["messages"] == 2
    assert manifest["po"]["translated"] == 0
    asset = tmp_path / "release/assets" / manifest["po"]["filename"]
    assert asset.read_bytes() == payload


def test_upstream_removals_and_empty_translations_replace_previous_tree(
    catalog_repository, workflow
):
    root, config, paths, _ = catalog_repository
    build_translation_repository(repo_root=root, preserve_existing_translations=False)
    replacement = (
        'msgid ""\nmsgstr ""\n"Language: zh_Hant\\n"\n'
        "\n#: phase/ffffffff-ffff-4fff-8fff-ffffffffffff/title\n"
        'msgid "Changed upstream phase"\nmsgstr ""\n'
    ).encode()
    pull_localize_po(config_path=config, repo_root=root, downloader=lambda _: replacement)
    result = build_translation_repository(repo_root=root, preserve_existing_translations=False)
    assert result.final_po_path.read_bytes() == replacement
    scan = workflow.tree_repository.scan(str(result.tree_dir))
    assert len(scan.translations) == 1
    assert scan.translations[("ffffffff-ffff-4fff-8fff-ffffffffffff", "title")] == ""
    assert len(list((root / paths.translation_tree_dir).rglob("translation.md"))) == 1


def test_live_status_needs_no_model(catalog_repository, monkeypatch, capsys):
    root, _, paths, payload = catalog_repository
    (root / paths.source_km_path).unlink()
    monkeypatch.setattr("dsw_km_translation_tool.localize_sync._download_url", lambda _: payload)
    output = root / "status.json"
    monkeypatch.setattr(
        sys, "argv", ["status", "--repo-root", str(root), "--json-out", str(output)]
    )
    report_localize_status.main()
    report = json.loads(output.read_text())
    assert report["message_blocks"] == 2
    assert report["empty_blocks"] == report["fuzzy_blocks"] == 1
    assert "waiting" not in capsys.readouterr().out


def test_current_registry_model_does_not_consult_weblate(catalog_repository):
    root, config, _, _ = catalog_repository

    def unavailable(_):
        raise AssertionError("A current KM must not depend on Weblate availability")

    result = sync_latest_km_version(
        repo_root=root,
        tooling_repo=root,
        config_path=config,
        registry_token="",
        downloader=lambda _: registry_payload("2.7.0"),
        localize_downloader=unavailable,
    )
    assert result.status == "current"


def test_official_mirror_accepts_upstream_removals_and_format_changes(catalog_repository):
    root, config, paths, _ = catalog_repository
    build_translation_repository(repo_root=root, preserve_existing_translations=False)
    base = _commit(root)
    payload = (
        'msgid ""\nmsgstr ""\n"Language: zh_Hant\\n"\n'
        "\n#: phase/ffffffff-ffff-4fff-8fff-ffffffffffff/title\n"
        'msgid "**Important phase**"\nmsgstr "官方無粗體譯文"\n'
    ).encode()
    source = root / paths.source_po_path
    pull_localize_po(config_path=config, repo_root=root, downloader=lambda _: payload)
    build_translation_repository(repo_root=root, preserve_existing_translations=False)
    head = _commit(root)
    report = build_github_translation_report(
        repo_root=root, base_ref=base, head_ref=head, latest_po_path=source
    )
    assert report.has_translation_changes
    assert report.already_imported_entries == report.changed_entries
    assert report.importable_entries == 0
    assert not report.has_conflicts
    assert not report.has_format_errors
    assert not report.has_shared_block_errors

    document = next((root / paths.translation_tree_dir).rglob("translation.md"))
    document.write_text(document.read_text().replace("官方無粗體譯文", "人工無粗體譯文"))
    edited = _commit(root)
    report = build_github_translation_report(
        repo_root=root, base_ref=head, head_ref=edited, latest_po_path=source
    )
    assert report.has_format_errors
    assert report.importable_entries == 0
