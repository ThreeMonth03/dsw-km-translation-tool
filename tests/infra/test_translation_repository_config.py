"""Tests for versioned KM translation repository configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from dsw_translation_tool.translation_repository_config import (
    TranslationRepositoryConfigError,
    load_translation_repository_config,
    sorted_versions,
    version_branch,
    version_paths,
)
from tests.helpers import run_cli_script


def write_config(path: Path, *, supported_versions: list[str] | None = None) -> None:
    """Write a minimal valid translation config for tests."""

    versions = supported_versions or ["2.7.0"]
    version_lines = "\n".join(f"    - {version}" for version in versions)
    path.write_text(
        f"""schema_version: 1

knowledge_model:
  organization_id: dsw
  km_id: root
  upstream_repository: https://github.com/ds-wizard/dsw-root-locales.git
  bundle_path: files/dsw_root_2.7.0.km
  supported_versions:
{version_lines}

translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant
  translated_organization_id: dsw
  translated_km_id: root-zh-hant
  translated_name: Common DSW Knowledge Model (zh-Hant)

branches:
  version_branch_prefix: translation/v

tooling:
  repository: ThreeMonth03/DSW_Translation_tool
  ref: master

localize:
  download_url: https://localize.ds-wizard.org/download/knowledge-models/common-dsw-knowledge-model/zh_Hant/
  repository: https://github.com/ds-wizard/dsw-root-locales.git

migration:
  mode: exact-only
  non_exact_policy: leave_empty_needs_translation
  protected_chapters:
    - "0003"
    - "0004"
    - "0005"
""",
        encoding="utf-8",
    )


def test_config_loader_normalizes_versions_and_paths(workspace: Path) -> None:
    """Verify that KM repository config derives branch and workspace paths."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path, supported_versions=["2.7.0", "2.6.10", "v2.6.9"])

    config = load_translation_repository_config(config_path)

    assert config.knowledge_model.supported_versions == ("2.6.9", "2.6.10", "2.7.0")
    assert config.migration.protected_chapters == ("0003", "0004", "0005")
    assert version_branch(config, "v2.7.0") == "translation/v2.7.0"

    paths = version_paths(config, "2.7.0")
    assert paths.package_id == "dsw:root:2.7.0"
    assert paths.source_km_path == Path("sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km")
    assert paths.localize_base_po_path == Path("sources/localize/zh_Hant/base.po")
    assert paths.localize_latest_po_path == Path("sources/localize/zh_Hant/latest.po")
    assert paths.translation_tree_dir == Path("tree")
    assert paths.final_po_path == Path("builds/final_translated.po")
    assert paths.conflicts_report_path == Path("reports/conflicts.json")


def test_version_sorting_handles_multi_digit_segments() -> None:
    """Verify semantic sorting for KM package versions."""

    assert sorted_versions(["2.6.9", "2.6.10", "2.5.0", "v2.7.0"]) == [
        "2.5.0",
        "2.6.9",
        "2.6.10",
        "2.7.0",
    ]


def test_config_loader_rejects_unsupported_migration_mode(workspace: Path) -> None:
    """Verify that only conservative exact migration is accepted."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace("mode: exact-only", "mode: fuzzy"),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryConfigError, match="exact-only"):
        load_translation_repository_config(config_path)


def test_validate_translation_config_cli_reports_summary(
    repo_root: Path,
    workspace: Path,
) -> None:
    """Verify the validation CLI used by downstream translation repos."""

    config_path = workspace / "translation-config.yml"
    summary_path = workspace / "summary.md"
    write_config(config_path)

    result = run_cli_script(
        repo_root,
        "src/validate_translation_config.py",
        "--config",
        str(config_path),
        "--summary",
        str(summary_path),
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "KM translation config is valid." in result.stdout
    assert "Latest branch: translation/v2.7.0" in result.stdout
    assert "Protected chapters: 0003, 0004, 0005" in result.stdout
    assert "## KM Translation Config" in summary_path.read_text(encoding="utf-8")
