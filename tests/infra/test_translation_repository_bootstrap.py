"""Tests for initializing dedicated translation repositories."""

from __future__ import annotations

from pathlib import Path

from dsw_km_translation_tool.translation_repository_bootstrap import (
    TranslationRepositoryBootstrapError,
    bootstrap_translation_repository,
)
from tests.helpers import run_cli_command
from tests.infra.test_translation_repository_config import write_config


def test_bootstrap_scaffolds_config_docs_and_workflows(
    repo_root: Path,
    workspace: Path,
) -> None:
    """Verify scaffold-only bootstrap copies managed repository files."""

    config_template = workspace / "template.yml"
    target_repo = workspace / "translation-repo"
    write_config(config_template)

    result = bootstrap_translation_repository(
        repo_root=target_repo,
        tooling_repo=repo_root,
        config_template_path=config_template,
        hydrate=False,
    )

    assert result.hydrated is False
    assert (target_repo / "translation-config.yml").exists()
    assert (target_repo / "README.md").exists()
    assert (target_repo / "docs" / "maintenance-runbook.md").exists()
    workflow = target_repo / ".github" / "workflows" / "localize_auto_sync.yml"
    assert workflow.exists()
    workflow_text = workflow.read_text(encoding="utf-8")
    assert "TOOLING_REPOSITORY: ThreeMonth03/dsw-km-translation-tool" in workflow_text
    assert "TRACKING_BRANCH: translation/latest" in workflow_text
    assert 'branches: ["translation/latest"]' in workflow_text
    assert result.written_files
    assert result.skipped_files == ()


def test_bootstrap_hydrates_tree_and_build_outputs(
    repo_root: Path,
    workspace: Path,
    po_path: Path,
    model_path: Path,
) -> None:
    """Verify bootstrap can hydrate a repo from injected KM and PO downloads."""

    config_template = workspace / "template.yml"
    target_repo = workspace / "translation-repo"
    write_config(config_template)

    result = bootstrap_translation_repository(
        repo_root=target_repo,
        tooling_repo=repo_root,
        config_template_path=config_template,
        registry_token="token",
        bundle_downloader=lambda _url, _token: model_path.read_bytes(),
        localize_downloader=lambda _url: po_path.read_bytes(),
    )

    assert result.hydrated is True
    assert result.km_version == "2.7.0"
    assert result.source_km_path == (
        target_repo / "sources" / "knowledge-models" / "dsw-root-2.7.0" / "dsw-root-2.7.0.km"
    )
    assert result.localize_po_path == target_repo / "sources" / "localize" / "zh_Hant" / "latest.po"
    assert (target_repo / "tree" / "_translation_tree.json").exists()
    assert (target_repo / "builds" / "final_translated.po").exists()
    assert (target_repo / "builds" / "final_translated.km").exists()
    assert (target_repo / "reviews" / "final_translated.diff").exists()


def test_bootstrap_requires_registry_token_for_hydration(
    repo_root: Path,
    workspace: Path,
) -> None:
    """Verify hydration fails clearly when no Registry token is available."""

    config_template = workspace / "template.yml"
    write_config(config_template)

    try:
        bootstrap_translation_repository(
            repo_root=workspace / "translation-repo",
            tooling_repo=repo_root,
            config_template_path=config_template,
            registry_token="",
        )
    except TranslationRepositoryBootstrapError as error:
        assert "DSW_REGISTRY_TOKEN" in str(error)
    else:
        raise AssertionError("Expected bootstrap to require a Registry token")


def test_init_translation_repo_cli_scaffold_only(
    repo_root: Path,
    workspace: Path,
) -> None:
    """Verify the packaged CLI can scaffold a repository without downloads."""

    config_template = workspace / "template.yml"
    target_repo = workspace / "translation-repo"
    write_config(config_template)

    result = run_cli_command(
        repo_root,
        "dsw-km-init-translation-repo",
        "--repo-root",
        str(target_repo),
        "--tooling-repo",
        str(repo_root),
        "--config-template",
        str(config_template),
        "--scaffold-only",
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "Hydrated   : no" in result.stdout
    assert (target_repo / ".github" / "workflows" / "validate_translation_config.yml").exists()
