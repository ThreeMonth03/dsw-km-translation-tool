"""Only evidenced version transitions may defer synchronization."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from dsw_km_translation_tool.alignment_status import build_alignment_status_report
from dsw_km_translation_tool.cli import (
    import_github_translations,
    report_localize_status,
    sync_from_localize,
)
from dsw_km_translation_tool.km_latest_sync import KmLatestSyncError, sync_latest_km_version
from dsw_km_translation_tool.locale_coverage import LocaleCoverageError
from dsw_km_translation_tool.localize_sync import pull_localize_po
from dsw_km_translation_tool.native_locale import NativeLocaleValidationError
from dsw_km_translation_tool.po_support.parser import PoCatalogError, PoCatalogParser
from dsw_km_translation_tool.source_readiness import SourceUpdatePending, check_po_source
from dsw_km_translation_tool.translation_repository_config import load_translation_repository_config
from tests.infra.test_alignment_status import prepare_translation_repo_fixture
from tests.infra.test_km_latest_sync import RecordingRunner, candidate_bundle, registry_payload
from tests.infra.test_translation_repository_config import write_config


def mock_pot(monkeypatch, pot: Path):
    calls = []

    def snapshot(repository, destination):
        calls.append(repository)
        shutil.copyfile(pot, destination)
        return "a" * 40, "https://github.com/ds-wizard/dsw-root-locales/blob/commit/messages.pot"

    monkeypatch.setattr("dsw_km_translation_tool.source_readiness.snapshot_upstream_pot", snapshot)
    return calls


@pytest.fixture
def future_sources(tmp_path, po_path, monkeypatch):
    entry = next(e for e in PoCatalogParser(str(po_path)).parse_entries() if e.msgid == "10 years")
    reference = f"{entry.prefix}/{entry.uuid}/{entry.field}"
    body = f'\n#: {reference}\nmsgid "11 years"\nmsgstr ""\n'
    po = tmp_path / "future.po"
    pot = tmp_path / "future.pot"
    # Weblate may keep the old PO version header after updating source messages.
    po.write_text(
        'msgid ""\nmsgstr ""\n"Project-Id-Version: Common DSW Knowledge Model 2.7.0\\n"\n'
        '"Language: zh_Hant\\n"\n' + body,
        encoding="utf-8",
    )
    pot.write_text(
        'msgid ""\nmsgstr ""\n"Project-Id-Version: dsw:root:2.8.1\\n"\n"Language: en\\n"\n' + body,
        encoding="utf-8",
    )
    config_path = tmp_path / "translation-config.yml"
    write_config(config_path)
    calls = mock_pot(monkeypatch, pot)
    return po, pot, load_translation_repository_config(config_path), calls


def test_matching_pair_does_not_depend_on_live_pot(future_sources, po_path, model_path):
    _, _, config, calls = future_sources
    check_po_source(config=config, po_path=po_path, km_path=model_path)
    assert calls == []


def test_wait_requires_real_source_evidence_not_stale_po_header(future_sources, model_path):
    po, _, config, calls = future_sources
    with pytest.raises(SourceUpdatePending) as caught:
        check_po_source(config=config, po_path=po, km_path=model_path)
    assert len(calls) == 1
    report = caught.value.report
    assert report.configured_package_id == "dsw:root:2.7.0"
    assert report.required_package_id == "dsw:root:2.8.1"
    assert report.status == "waiting-for-km"
    assert report.upstream_commit == "a" * 40
    assert "No translations were applied" in report.markdown()


@pytest.mark.parametrize(
    "old,new,error",
    [
        ("2.8.1", "2.7.0", NativeLocaleValidationError),
        ("11 years", "12 years", NativeLocaleValidationError),
        ("dsw:root", "other:root", LocaleCoverageError),
        ("Language: en", "Language: de", LocaleCoverageError),
    ],
)
def test_real_source_errors_are_not_waiting(future_sources, model_path, old, new, error):
    po, pot, config, _ = future_sources
    pot.write_text(pot.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
    with pytest.raises(error):
        check_po_source(config=config, po_path=po, km_path=model_path)


def test_invalid_po_does_not_consult_pot(future_sources, model_path):
    po, _, config, calls = future_sources
    po.write_text("<html>Unavailable</html>", encoding="utf-8")
    with pytest.raises(PoCatalogError):
        check_po_source(config=config, po_path=po, km_path=model_path)
    assert calls == []


def test_pot_download_failure_is_not_waiting(future_sources, model_path, monkeypatch):
    po, _, config, _ = future_sources

    def fail(*args):
        raise OSError("upstream unavailable")

    monkeypatch.setattr("dsw_km_translation_tool.source_readiness.snapshot_upstream_pot", fail)
    with pytest.raises(OSError):
        check_po_source(config=config, po_path=po, km_path=model_path)


def test_pending_pull_and_writer_preserve_all_active_files(
    future_sources, workspace, po_path, model_path, monkeypatch, capsys
):
    future, _, _, _ = future_sources
    config = workspace / "translation-config.yml"
    write_config(config)
    for source, relative in (
        (po_path, "sources/localize/zh_Hant/latest.po"),
        (model_path, "sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km"),
    ):
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    marker = workspace / "tree/existing.md"
    marker.parent.mkdir()
    marker.write_text("Keep these translations", encoding="utf-8")
    before = {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    with pytest.raises(SourceUpdatePending):
        pull_localize_po(
            config_path=config, repo_root=workspace, downloader=lambda _: future.read_bytes()
        )
    monkeypatch.setattr(
        "dsw_km_translation_tool.localize_sync._download_url", lambda _: future.read_bytes()
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "sync",
            "--host-repo",
            str(workspace),
            "--tooling-repo",
            str(workspace),
            "--mode",
            "schedule",
        ],
    )
    sync_from_localize.main()
    assert "waiting-for-km" in capsys.readouterr().out
    assert {
        p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()
    } == before


def test_waiting_alignment_still_checks_existing_artifacts(
    future_sources, workspace, po_path, model_path, workflow
):
    future, _, _, _ = future_sources
    root = prepare_translation_repo_fixture(
        workspace=workspace, po_path=po_path, model_path=model_path, workflow=workflow
    )
    kwargs = dict(
        repo_root=root,
        config_path=root / "translation-config.yml",
        downloader=lambda _: future.read_bytes(),
    )
    report = build_alignment_status_report(**kwargs)
    assert not report.aligned
    assert not report.failed
    assert report.checks[0].deferred
    assert report.to_dict()["status"] == "waiting-for-km"
    final = root / "builds/final_translated.po"
    final.write_bytes(final.read_bytes() + b"\n# Uncommitted output drift\n")
    assert build_alignment_status_report(**kwargs).failed


def test_live_status_counts_pending_catalog_without_replacing_snapshot(
    future_sources, workspace, po_path, model_path, monkeypatch, capsys
):
    future, _, _, _ = future_sources
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    for source, relative in (
        (model_path, "sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km"),
        (po_path, "sources/localize/zh_Hant/latest.po"),
    ):
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    report_path = workspace / "report.json"
    monkeypatch.setattr(report_localize_status, "_download_url", lambda _: future.read_bytes())
    monkeypatch.setattr(
        sys, "argv", ["status", "--repo-root", str(workspace), "--json-out", str(report_path)]
    )
    report_localize_status.main()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["source_readiness"]["required_package_id"] == "dsw:root:2.8.1"
    assert "waiting-for-km" in capsys.readouterr().out
    assert (workspace / "sources/localize/zh_Hant/latest.po").read_bytes() == po_path.read_bytes()


@pytest.mark.parametrize("registry_version", ["2.7.0", "2.8.0"])
def test_km_updater_waits_without_modifying_active_pair(
    future_sources, workspace, po_path, model_path, registry_version
):
    future, _, _, _ = future_sources
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    for source, relative in (
        (model_path, "sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km"),
        (po_path, "sources/localize/zh_Hant/latest.po"),
    ):
        target = workspace / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    before = {p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()}
    runner = RecordingRunner()
    with pytest.raises(SourceUpdatePending):
        sync_latest_km_version(
            repo_root=workspace,
            tooling_repo=workspace,
            config_path=config_path,
            registry_token="test-token",
            downloader=lambda _: registry_payload(registry_version),
            localize_downloader=lambda _: future.read_bytes(),
            runner=runner,
        )
    assert {
        p.relative_to(workspace): p.read_bytes() for p in workspace.rglob("*") if p.is_file()
    } == before
    assert not any(command.startswith("git push") for command in runner.command_names)


@pytest.mark.parametrize("wrong_identity", [False, True])
def test_invalid_candidate_pair_does_not_replace_active_config(
    future_sources, workspace, model_path, wrong_identity
):
    future, _, _, _ = future_sources
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    before = config_path.read_bytes()
    bundle = model_path.read_bytes() if wrong_identity else candidate_bundle(model_path, "2.8.1")
    with pytest.raises(KmLatestSyncError if wrong_identity else NativeLocaleValidationError):
        sync_latest_km_version(
            repo_root=workspace,
            tooling_repo=workspace,
            config_path=config_path,
            registry_token="test-token",
            downloader=lambda _: registry_payload("2.8.1"),
            bundle_downloader=lambda _url, _token: bundle,
            localize_downloader=lambda _: future.read_bytes(),
            runner=RecordingRunner(),
        )
    assert config_path.read_bytes() == before
    assert not (workspace / "sources").exists()


def test_matching_release_resumes_update_to_pot_version_not_registry_latest(
    future_sources, workspace, model_path
):
    future, _, _, _ = future_sources
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    bundle = candidate_bundle(model_path, "2.8.1").replace(b'"10 years"', b'"11 years"')
    result = sync_latest_km_version(
        repo_root=workspace,
        tooling_repo=workspace,
        config_path=config_path,
        registry_token="test-token",
        downloader=lambda _: registry_payload("2.9.0"),
        bundle_downloader=lambda _url, _token: bundle,
        localize_downloader=lambda _: future.read_bytes(),
        runner=RecordingRunner(),
    )
    assert result.changed
    assert load_translation_repository_config(config_path).knowledge_model.version == "2.8.1"
    assert (workspace / "sources/localize/zh_Hant/latest.po").read_bytes() == future.read_bytes()


def test_pending_import_never_uploads_to_weblate(
    future_sources, workspace, model_path, monkeypatch
):
    future, _, _, _ = future_sources
    write_config(workspace / "translation-config.yml")
    km = workspace / "sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km"
    km.parent.mkdir(parents=True)
    shutil.copyfile(model_path, km)
    monkeypatch.setattr(
        "dsw_km_translation_tool.localize_sync._download_url", lambda _: future.read_bytes()
    )
    monkeypatch.setattr(
        import_github_translations,
        "upload_translation_file",
        lambda **_: pytest.fail("Pending imports must not upload"),
    )
    report = workspace / "report.json"
    outputs = workspace / "outputs.txt"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "import",
            "--repo-root",
            str(workspace),
            "--base-ref",
            "HEAD~1",
            "--json-out",
            str(report),
            "--details-out",
            str(workspace / "report.md"),
            "--github-output",
            str(outputs),
        ],
    )
    import_github_translations.main()
    assert json.loads(report.read_text())["status"] == "waiting-for-km"
    assert "uploaded=false" in outputs.read_text()
