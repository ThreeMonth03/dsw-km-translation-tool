"""Tests for GitHub-originated translation contribution handling."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from dsw_km_translation_tool.cli import (
    import_github_translations,
    report_github_translations,
)
from dsw_km_translation_tool.github_translation_contributions import (
    CONFLICT_DECISION,
    IMPORT_DECISION,
    build_github_translation_report,
    write_import_po,
)
from tests.infra.test_translation_repository_config import write_config

TEST_UUID = "11111111-1111-1111-1111-111111111111"


def test_github_translation_report_marks_safe_imports(workspace: Path) -> None:
    """Verify GitHub translations can be imported when Weblate did not change."""

    repo = initialize_translation_repo(workspace)
    base_ref = commit_translation(repo, "base", "舊翻譯")
    head_ref = commit_translation(repo, "github", "GitHub 新翻譯")
    latest_po = write_latest_po(workspace / "latest.po", "舊翻譯")

    report = build_github_translation_report(
        repo_root=repo,
        base_ref=base_ref,
        head_ref=head_ref,
        latest_po_path=latest_po,
    )

    assert report.has_translation_changes is True
    assert report.has_conflicts is False
    assert report.importable_entries == 1
    assert report.decisions[0].decision == IMPORT_DECISION
    assert report.decisions[0].github == "GitHub 新翻譯"


def test_github_translation_report_marks_conflicts(workspace: Path) -> None:
    """Verify conflicts require review instead of last-writer-wins import."""

    repo = initialize_translation_repo(workspace)
    base_ref = commit_translation(repo, "base", "舊翻譯")
    head_ref = commit_translation(repo, "github", "GitHub 新翻譯")
    latest_po = write_latest_po(workspace / "latest.po", "Weblate 新翻譯")

    report = build_github_translation_report(
        repo_root=repo,
        base_ref=base_ref,
        head_ref=head_ref,
        latest_po_path=latest_po,
    )

    assert report.has_conflicts is True
    assert report.importable_entries == 0
    assert report.conflict_entries == 1
    assert report.decisions[0].decision == CONFLICT_DECISION


def test_write_import_po_contains_only_importable_entries(workspace: Path) -> None:
    """Verify partial PO output contains safe GitHub translations."""

    repo = initialize_translation_repo(workspace)
    base_ref = commit_translation(repo, "base", "舊翻譯")
    head_ref = commit_translation(repo, "github", "GitHub 新翻譯")
    latest_po = write_latest_po(workspace / "latest.po", "舊翻譯")
    report = build_github_translation_report(
        repo_root=repo,
        base_ref=base_ref,
        head_ref=head_ref,
        latest_po_path=latest_po,
    )
    import_po = write_import_po(
        report=report,
        output_path=workspace / "github-import.po",
        language="zh_Hant",
    )

    text = import_po.read_text(encoding="utf-8")
    assert f"#: github:{TEST_UUID}:title" in text
    assert 'msgid "Source title"' in text
    assert 'msgstr "GitHub 新翻譯"' in text


def test_report_github_translations_cli_writes_outputs(
    monkeypatch,
    workspace: Path,
) -> None:
    """Verify the PR report CLI exposes safe GitHub Actions outputs."""

    repo = initialize_translation_repo(workspace)
    write_config(repo / "translation-config.yml")
    base_ref = commit_translation(repo, "base", "舊翻譯")
    head_ref = commit_translation(repo, "github", "GitHub 新翻譯")
    latest_po = write_latest_po(workspace / "latest.po", "舊翻譯")
    json_out = workspace / "report.json"
    details_out = workspace / "report.md"
    github_output = workspace / "github-output.txt"

    monkeypatch.setattr(
        report_github_translations,
        "pull_localize_po",
        lambda **_kwargs: SimpleNamespace(latest_po_path=latest_po),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dsw-km-report-github-translations",
            "--repo-root",
            str(repo),
            "--config",
            "translation-config.yml",
            "--base-ref",
            base_ref,
            "--head-ref",
            head_ref,
            "--json-out",
            str(json_out),
            "--details-out",
            str(details_out),
            "--github-output",
            str(github_output),
        ],
    )

    report_github_translations.main()

    assert '"importable_entries": 1' in json_out.read_text(encoding="utf-8")
    assert "GitHub Translation Contributions" in details_out.read_text(encoding="utf-8")
    outputs = github_output.read_text(encoding="utf-8")
    assert "has_translation_changes=true" in outputs
    assert "has_conflicts=false" in outputs
    assert "importable_entries=1" in outputs


def test_import_github_translations_cli_blocks_conflicts(
    monkeypatch,
    workspace: Path,
) -> None:
    """Verify post-merge import does not upload conflicting GitHub edits."""

    repo = initialize_translation_repo(workspace)
    write_config(repo / "translation-config.yml")
    base_ref = commit_translation(repo, "base", "舊翻譯")
    head_ref = commit_translation(repo, "github", "GitHub 新翻譯")
    latest_po = write_latest_po(workspace / "latest.po", "Weblate 新翻譯")
    github_output = workspace / "github-output.txt"

    monkeypatch.setattr(
        import_github_translations,
        "pull_localize_po",
        lambda **_kwargs: SimpleNamespace(latest_po_path=latest_po),
    )

    def fail_upload(**_kwargs) -> None:
        raise AssertionError("unexpected upload")

    monkeypatch.setattr(
        import_github_translations,
        "upload_translation_file",
        fail_upload,
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "dsw-km-import-github-translations",
            "--repo-root",
            str(repo),
            "--config",
            "translation-config.yml",
            "--base-ref",
            base_ref,
            "--head-ref",
            head_ref,
            "--json-out",
            str(workspace / "import.json"),
            "--details-out",
            str(workspace / "import.md"),
            "--github-output",
            str(github_output),
        ],
    )

    try:
        import_github_translations.main()
    except SystemExit as error:
        assert "has conflicts" in str(error)
    else:
        raise AssertionError("Expected conflict imports to fail")

    outputs = github_output.read_text(encoding="utf-8")
    assert "has_conflicts=true" in outputs
    assert "uploaded=false" in outputs


def initialize_translation_repo(workspace: Path) -> Path:
    """Create a small Git repository for translation contribution tests."""

    repo = workspace / "repo"
    repo.mkdir()
    run_git(repo, "init")
    run_git(repo, "config", "user.name", "Test User")
    run_git(repo, "config", "user.email", "test@example.invalid")
    return repo


def commit_translation(repo: Path, message: str, target: str) -> str:
    """Write one translation value and commit it."""

    translation_path = repo / "tree" / "node" / "translation.md"
    translation_path.parent.mkdir(parents=True, exist_ok=True)
    translation_path.write_text(render_translation_markdown(target), encoding="utf-8")
    run_git(repo, "add", "tree/node/translation.md")
    run_git(repo, "commit", "-m", message)
    return run_git(repo, "rev-parse", "HEAD").stdout.strip()


def render_translation_markdown(target: str) -> str:
    """Render a minimal translation markdown file."""

    return "\n".join(
        [
            "# Translation",
            "",
            f"- UUID: `{TEST_UUID}`",
            "- Event Type: `EditQuestionEvent`",
            "- Edit only the `Translation (zh_Hant)` blocks below.",
            "",
            "## title",
            "",
            "### Source (en)",
            "",
            "~~~text",
            "Source title",
            "~~~",
            "",
            "### Translation (zh_Hant)",
            "",
            "~~~text",
            target,
            "~~~",
            "",
        ]
    )


def write_latest_po(path: Path, target: str) -> Path:
    """Write a minimal Weblate PO fixture."""

    path.write_text(
        "\n".join(
            [
                'msgid ""',
                'msgstr ""',
                '"Language: zh_Hant\\n"',
                "",
                f"#: question:{TEST_UUID}:title",
                'msgid "Source title"',
                f'msgstr "{target}"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    return path


def run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a Git command in a test repository."""

    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    return result
