"""Regression tests for untrusted catalogs and pull-request input boundaries."""

from __future__ import annotations

import io
import json
import sys
from types import SimpleNamespace

import pytest

from dsw_km_translation_tool.bounded_download import read_bounded_response
from dsw_km_translation_tool.catalog_limits import (
    CatalogLimitError,
    validate_catalog_size,
)
from dsw_km_translation_tool.cli import (
    report_github_translations,
    report_source_catalog,
)
from dsw_km_translation_tool.github_translation_contributions import (
    build_github_translation_report,
)
from dsw_km_translation_tool.translation_repository_build import (
    TranslationRepositoryBuildError,
    validate_committed_locale,
)
from tests.infra.test_github_translation_contributions import (
    commit_shared_translation,
    commit_translation,
    initialize_translation_repo,
    run_git,
    write_latest_po,
)
from tests.infra.test_translation_repository_config import write_config


@pytest.mark.parametrize("headers", [{}, {"Content-Length": "4"}])
def test_streaming_limit_rejects_unknown_or_false_content_length(headers):
    response = SimpleNamespace(headers=headers, read1=io.BytesIO(b"123456").read1)
    with pytest.raises(CatalogLimitError, match="byte limit"):
        read_bounded_response(response, deadline=10, max_bytes=5, clock=lambda: 0)


def test_known_oversize_is_rejected_before_read():
    response = SimpleNamespace(headers={"Content-Length": "6"}, read1=lambda _: pytest.fail("read"))
    with pytest.raises(CatalogLimitError, match="byte limit"):
        read_bounded_response(response, deadline=10, max_bytes=5, clock=lambda: 0)


def test_slow_stream_stops_at_elapsed_budget():
    ticks = iter([0, 0, 0, 11])
    response = SimpleNamespace(headers={}, read1=io.BytesIO(b"x").read1)
    with pytest.raises(CatalogLimitError, match="elapsed-time"):
        read_bounded_response(response, deadline=10, clock=lambda: next(ticks))


@pytest.mark.parametrize(
    "payload",
    ["x" * (8 * 1024 * 1024 + 1), "x" * 65537, "中" * 21846, 'msgid "x"\n' * 20001],
)
def test_catalog_resource_limits_precede_parsing(payload):
    with pytest.raises(CatalogLimitError):
        validate_catalog_size(payload)


@pytest.mark.parametrize("tamper", ["remove", "metadata"])
def test_live_mirror_does_not_bypass_shared_block_structure(workspace, tamper):
    repo = initialize_translation_repo(workspace)
    commit_translation(repo, "tree", "既有翻譯")
    base = commit_shared_translation(repo, "canonical", "既有翻譯")
    path = repo / "tree/shared_blocks/shared-group/context.md"
    if tamper == "remove":
        path.unlink()
    else:
        text = path.read_text()
        path.write_text(text.replace(":title`", ":description`"))
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "alter shared structure")
    report = build_github_translation_report(
        repo_root=repo,
        base_ref=base,
        head_ref="HEAD",
        latest_po_path=write_latest_po(workspace / "latest.po", "既有翻譯"),
    )
    assert report.has_shared_block_errors


@pytest.mark.parametrize("tamper", ["url", "symlink"])
def test_pr_catalog_download_uses_accepted_configuration(workspace, monkeypatch, tamper):
    repo = initialize_translation_repo(workspace)
    config = repo / "translation-config.yml"
    write_config(config)
    base = commit_translation(repo, "accepted", "")
    malicious = config.read_text().replace("localize.ds-wizard.org", "attacker.example")
    if tamper == "url":
        config.write_text(malicious)
    else:
        alternate = repo / "alternate.yml"
        alternate.write_text(malicious)
        config.unlink()
        config.symlink_to(alternate.name)
        run_git(repo, "add", "alternate.yml")
    head = commit_translation(repo, "candidate", "譯文")
    latest = write_latest_po(workspace / "latest.po", "")

    def download(**kwargs):
        text = kwargs["config_path"].read_text()
        assert "attacker.example" not in text
        assert "localize.ds-wizard.org" in text
        return SimpleNamespace(latest_po_path=latest)

    monkeypatch.setattr(report_github_translations, "pull_localize_po", download)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report",
            "--repo-root",
            str(repo),
            "--base-ref",
            base,
            "--head-ref",
            head,
            "--json-out",
            str(workspace / "report.json"),
            "--details-out",
            str(workspace / "report.md"),
        ],
    )
    report_github_translations.main()
    assert json.loads((workspace / "report.json").read_text())["importable_entries"] == 1


def test_source_audit_uses_base_repository_not_pr_repository(tmp_path, monkeypatch):
    write_config(tmp_path / "translation-config.yml")
    trusted = tmp_path / "accepted.yml"
    trusted.write_bytes((tmp_path / "translation-config.yml").read_bytes())
    config = tmp_path / "translation-config.yml"
    config.write_text(
        config.read_text().replace("ds-wizard/dsw-root-locales.git", "attacker/large.git")
    )

    def audit(**kwargs):
        assert kwargs["repository"] == "https://github.com/ds-wizard/dsw-root-locales.git"
        raise OSError("bounded test stop")

    monkeypatch.setattr(report_source_catalog, "audit_source_catalog", audit)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report",
            "--repo-root",
            str(tmp_path),
            "--trusted-config",
            str(trusted),
            "--official-pot",
            "unused.pot",
            "--out",
            str(tmp_path / "reports"),
        ],
    )
    with pytest.raises(SystemExit) as error:
        report_source_catalog.main()
    assert error.value.code == 1


@pytest.mark.parametrize(
    "change,committed",
    [
        (True, "tampered\n"),
        (True, "rebuilt\n"),
        (True, "rebuilt\r\n"),
        (False, "old\n"),
    ],
)
def test_changed_generated_po_must_equal_rebuild(workspace, change, committed):
    repo = initialize_translation_repo(workspace)
    path = repo / "builds/final_translated.po"
    path.parent.mkdir()
    path.write_text("old\n")
    run_git(repo, "add", ".")
    run_git(repo, "commit", "-m", "base PO")
    base = run_git(repo, "rev-parse", "HEAD").stdout.strip()
    if change:
        path.write_text(committed)
        run_git(repo, "add", ".")
        run_git(repo, "commit", "-m", "candidate PO")
    path.write_text("rebuilt\n")
    if change and committed != "rebuilt\n":
        with pytest.raises(TranslationRepositoryBuildError, match="differs from its rebuild"):
            validate_committed_locale(
                repo_root=repo, final_po_path=path, base_ref=base, head_ref="HEAD"
            )
    else:
        validate_committed_locale(
            repo_root=repo, final_po_path=path, base_ref=base, head_ref="HEAD"
        )
