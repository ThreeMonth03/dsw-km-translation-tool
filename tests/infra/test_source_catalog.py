"""Source audits must not confuse upstream extraction gaps with translation work."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest
import yaml
from babel.messages.catalog import Catalog
from babel.messages.pofile import write_po

from dsw_km_translation_tool.cli.report_source_catalog import main
from dsw_km_translation_tool.locale_coverage import (
    LocaleCoverageError,
    compare_source_catalog,
    render_source_catalog,
)
from dsw_km_translation_tool.source_catalog import snapshot_upstream_pot
from tests.infra.test_translation_repository_config import write_config


@pytest.fixture
def catalogs(tmp_path):
    official = Catalog(locale="en", project="dsw:root:2.7.0", version="")
    official.version = ""
    upstream = Catalog(project="Common DSW Knowledge Model", version="2.7.0")
    official.add("Existing", locations=[("chapter/uuid/title", None)])
    upstream.add("Existing", locations=[("chapter:uuid:title", None)])
    return tmp_path, official, upstream


def compare(catalogs):
    root, official, upstream = catalogs
    paths = root / "official.pot", root / "upstream.pot"
    for path, catalog in zip(paths, (official, upstream), strict=True):
        with path.open("wb") as handle:
            write_po(handle, catalog)
    before = [path.read_bytes() for path in paths]
    report = compare_source_catalog(
        pot_path=paths[0],
        upstream_pot_path=paths[1],
        package_id="dsw:root:2.7.0",
        source_language="en",
    )
    assert [path.read_bytes() for path in paths] == before
    return report


def test_aligned_sources_ignore_references_and_translation_state(catalogs):
    catalogs[2].get("Existing").flags.add("fuzzy")
    assert compare(catalogs)["status"] == "aligned"


def test_missing_source_is_an_upstream_addition_not_an_empty_translation(catalogs):
    catalogs[1].add("Before Submitting the DMP", locations=[("phase/uuid/title", None)])
    report = compare(catalogs)
    assert report["status"] == "different"
    assert report["counts"] == {
        "official": 2,
        "upstream": 1,
        "shared": 1,
        "missing_upstream": 1,
        "upstream_only": 0,
    }
    assert report["missing_upstream"][0]["references"] == ["phase/uuid/title"]
    report["upstream_url"] = "https://github.com/example/locales/blob/commit/messages.pot"
    rendered = render_source_catalog(report)
    assert "Before Submitting the DMP" in rendered
    assert "not live Weblate units" in rendered
    assert "do not block" in rendered
    assert "Before Submitting" not in render_source_catalog(report, details=False)


def test_changed_source_or_context_requires_review(catalogs):
    catalogs[2].delete("Existing")
    catalogs[2].add("Existing", context="different")
    report = compare(catalogs)
    assert report["status"] == "different"
    assert report["counts"]["missing_upstream"] == report["counts"]["upstream_only"] == 1


@pytest.mark.parametrize(
    "project,version", [("other:root:2.8.0", ""), ("Other", "invalid"), ("", "")]
)
def test_upstream_identity_must_be_identifiable(catalogs, project, version):
    catalogs[2].project, catalogs[2].version = project, version
    with pytest.raises(LocaleCoverageError, match="version"):
        compare(catalogs)


def test_package_id_header_is_accepted(catalogs):
    catalogs[2].project, catalogs[2].version = "dsw:root:2.7.0", ""
    assert compare(catalogs)["status"] == "aligned"


def test_human_readable_header_does_not_require_the_context_version(catalogs):
    catalogs[2].version = "2.8.1"
    report = compare(catalogs)
    assert report["status"] == "aligned"
    assert report["upstream_package_id"] == "dsw:root:2.8.1"


def test_different_versions_still_report_catalog_differences(catalogs):
    catalogs[2].project, catalogs[2].version = "dsw:root:2.8.1", ""
    report = compare(catalogs)
    assert report["status"] == "aligned"
    assert report["upstream_package_id"] == "dsw:root:2.8.1"
    assert report["counts"]["shared"] == 1
    report["upstream_url"] = "https://github.com/example/locales"
    assert "do not block" in render_source_catalog(report)


def test_target_language_cannot_be_used_as_source(catalogs):
    catalogs[2].locale = "zh_Hant"
    with pytest.raises(LocaleCoverageError, match="Language"):
        compare(catalogs)


def test_empty_source_cannot_be_reported_as_all_new_strings(catalogs):
    catalogs[2].delete("Existing")
    with pytest.raises(LocaleCoverageError, match="no translatable"):
        compare(catalogs)


@pytest.mark.parametrize(
    "repository",
    [
        "file:///tmp/repo",
        "git@github.com:owner/repo.git",
        "https://token@github.com/owner/repo",
        "https://example.com/owner/repo",
        "https://github.com/owner/repo?token=secret",
        "https://github.com/owner/repo/tree/main",
        "--upload-pack=command",
    ],
)
def test_snapshot_rejects_untrusted_repository_urls(tmp_path, repository):
    with pytest.raises(LocaleCoverageError, match="public HTTPS GitHub"):
        snapshot_upstream_pot(repository, tmp_path / "upstream.pot")
    assert not list(tmp_path.iterdir())


def test_snapshot_records_immutable_revision_without_checkout_or_push(tmp_path, monkeypatch):
    commands = []
    commit = "a" * 40

    def run(command, **kwargs):
        commands.append(command)
        assert kwargs["env"]["GIT_TERMINAL_PROMPT"] == "0"
        assert kwargs["env"]["GIT_CONFIG_GLOBAL"] == "/dev/null"
        assert kwargs["env"]["GIT_CONFIG_COUNT"] == "0"
        assert "credential.helper=" in command
        assert "core.hooksPath=/dev/null" in command
        output = f"{commit}\n".encode() if "rev-parse" in command else b"POT bytes"
        return subprocess.CompletedProcess(command, 0, stdout=output)

    monkeypatch.setattr(subprocess, "run", run)
    path = tmp_path / "upstream.pot"
    revision, url = snapshot_upstream_pot("https://github.com/ds-wizard/dsw-root-locales.git", path)
    assert revision == commit
    assert url == f"https://github.com/ds-wizard/dsw-root-locales/blob/{commit}/messages.pot"
    assert path.read_bytes() == b"POT bytes"
    assert len(commands) == 3
    assert "--bare" in commands[0] and "--depth=1" in commands[0]
    assert commands[-1][-1] == f"{commit}:messages.pot"


def test_clone_error_does_not_leak_git_output(tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(128, "git", stderr=b"private diagnostic")

    monkeypatch.setattr(subprocess, "run", fail)
    with pytest.raises(LocaleCoverageError, match="Could not read") as error:
        snapshot_upstream_pot("https://github.com/owner/repo", tmp_path / "upstream.pot")
    assert "private diagnostic" not in str(error.value)


def test_cli_failure_is_not_reported_as_aligned(tmp_path, monkeypatch):
    write_config(tmp_path / "translation-config.yml")

    def fail(**kwargs):
        raise LocaleCoverageError("Upstream POT version does not match the configured KM")

    monkeypatch.setattr(
        "dsw_km_translation_tool.cli.report_source_catalog.audit_source_catalog", fail
    )
    out = tmp_path / "reports"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report",
            "--repo-root",
            str(tmp_path),
            "--official-pot",
            str(tmp_path / "official.pot"),
            "--out",
            str(out),
            "--summary",
            str(tmp_path / "summary.md"),
        ],
    )
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 1
    assert json.loads((out / "source-catalog.json").read_text())["status"] == "failed"
    assert "Audit failed" in (tmp_path / "summary.md").read_text()
    with pytest.raises(SystemExit) as error:
        main()
    assert error.value.code == 2


def test_cli_does_not_claim_coverage_without_an_upstream_repository(tmp_path, monkeypatch):
    config = tmp_path / "translation-config.yml"
    write_config(config)
    payload = yaml.safe_load(config.read_text())
    payload["localize"].pop("repository")
    config.write_text(yaml.safe_dump(payload))
    out = tmp_path / "report"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report",
            "--repo-root",
            str(tmp_path),
            "--official-pot",
            "unused.pot",
            "--out",
            str(out),
        ],
    )
    main()
    assert json.loads((out / "source-catalog.json").read_text())["status"] == "not-configured"


def test_cli_additions_are_reported_without_failing_or_mutating_sources(catalogs, monkeypatch):
    root = catalogs[0]
    catalogs[1].add("New source")
    report = compare(catalogs)
    report.update(upstream_commit="a" * 40, upstream_url="https://github.com/example/locales")
    write_config(root / "translation-config.yml")
    monkeypatch.setattr(
        "dsw_km_translation_tool.cli.report_source_catalog.audit_source_catalog",
        lambda **kw: report,
    )
    out = root / "report"
    original = {path: path.read_bytes() for path in root.iterdir()}
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "report",
            "--repo-root",
            str(root),
            "--official-pot",
            str(root / "official.pot"),
            "--out",
            str(out),
        ],
    )
    main()
    assert json.loads((out / "source-catalog.json").read_text())["status"] == "different"
    assert "New source" in (out / "source-catalog.md").read_text()
    assert all(path.read_bytes() == content for path, content in original.items())
