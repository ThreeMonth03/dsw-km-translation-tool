"""Tests for KM translation repository configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from dsw_km_translation_tool.repository_ci_sync import build_repository_ci_sync_config
from dsw_km_translation_tool.translation_repository_config import (
    TranslationRepositoryConfigError,
    load_translation_repository_config,
    tracking_branch,
    version_paths,
)
from tests.helpers import run_cli_command


def write_config(
    path: Path,
    *,
    version: str = "2.7.0",
) -> None:
    """Write a minimal valid translation config for tests."""

    path.write_text(
        f"""schema_version: 3

knowledge_model:
  organization_id: dsw
  km_id: root
  version: {version}

translation:
  source_language: en
  target_language: zh_Hant
  target_language_label: zh-Hant

branches:
  tracking_branch: translation/latest

tooling:
  repository: ThreeMonth03/dsw-km-translation-tool
  ref: master

localize:
  download_url: https://localize.ds-wizard.org/download/knowledge-models/common-dsw-knowledge-model/zh_Hant/
  repository: https://github.com/ds-wizard/dsw-root-locales.git

registry:
  api_url: https://api.registry.ds-wizard.org
""",
        encoding="utf-8",
    )


def test_config_loader_normalizes_version_and_paths(workspace: Path) -> None:
    """Verify that KM repository config derives the tracking branch and workspace paths."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path, version="v2.7.0")

    config = load_translation_repository_config(config_path)

    assert config.knowledge_model.version == "2.7.0"
    assert config.registry.api_url == "https://api.registry.ds-wizard.org"
    assert tracking_branch(config) == "translation/latest"

    paths = version_paths(config)
    assert paths.package_id == "dsw:root:2.7.0"
    assert paths.source_km_path == Path("sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km")
    assert paths.source_po_path == Path("sources/localize/zh_Hant/latest.po")
    assert paths.translation_tree_dir == Path("tree")
    assert paths.final_po_path == Path("builds/final_translated.po")
    assert paths.conflicts_report_path == Path("reviews/conflicts.json")


def test_config_loader_uses_default_registry_when_omitted(workspace: Path) -> None:
    """Verify registry config remains optional for existing translation repos."""

    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "\nregistry:\n  api_url: https://api.registry.ds-wizard.org\n",
            "\n",
        ),
        encoding="utf-8",
    )

    config = load_translation_repository_config(config_path)

    assert config.registry.api_url == "https://api.registry.ds-wizard.org"


@pytest.mark.parametrize("previous", [1, 2])
def test_config_rejects_previous_schema(workspace: Path, previous: int) -> None:
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "schema_version: 3", f"schema_version: {previous}"
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryConfigError, match=f"schema_version {previous}"):
        load_translation_repository_config(config_path)


@pytest.mark.parametrize(
    "section,field",
    [
        (None, "workflow"),
        ("knowledge_model", "upstream_repository"),
        ("knowledge_model", "upstream_ref"),
        ("knowledge_model", "upstream_bundle_path"),
        ("knowledge_model", "bundle_path"),
        ("translation", "catalog_path"),
        ("branches", "unknown"),
        ("tooling", "unknown"),
        ("localize", "unknown"),
        ("registry", "unknown"),
    ],
)
def test_config_rejects_inactive_or_unknown_fields(
    workspace: Path, section: str | None, field: str
) -> None:
    path = workspace / "translation-config.yml"
    write_config(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    target = payload if section is None else payload[section]
    target[field] = "unused"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(TranslationRepositoryConfigError, match="Unexpected configuration field"):
        load_translation_repository_config(path)


@pytest.mark.parametrize(
    "section,field",
    [
        ("knowledge_model", "organization_id"),
        ("knowledge_model", "km_id"),
        ("translation", "source_language"),
        ("translation", "target_language"),
    ],
)
def test_config_rejects_identifiers_that_escape_artifact_paths(
    workspace: Path, section: str, field: str
) -> None:
    path = workspace / "translation-config.yml"
    write_config(path)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload[section][field] = "../../outside"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(TranslationRepositoryConfigError, match="safe identifier"):
        load_translation_repository_config(path)


def test_config_rejects_untrusted_tooling_repository(workspace: Path) -> None:
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "ThreeMonth03/dsw-km-translation-tool", "attacker/evil-tooling"
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryConfigError, match="trusted repository"):
        load_translation_repository_config(config_path)


@pytest.mark.parametrize(
    "download_url",
    [
        "file:///tmp/runner-secret",
        "http://localize.ds-wizard.org/latest.po",
        "https://user:password@localize.ds-wizard.org/latest.po",
    ],
)
def test_config_rejects_unsafe_localize_download_url(workspace: Path, download_url: str) -> None:
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "https://localize.ds-wizard.org/download/knowledge-models/"
            "common-dsw-knowledge-model/zh_Hant/",
            download_url,
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryConfigError, match="must be an HTTPS URL"):
        load_translation_repository_config(config_path)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("tooling.ref", "main\ninjected: value"),
        ("branches.tracking_branch", "translation/latest; echo pwned"),
        ("branches.tracking_branch", "translation/../main"),
        ("tooling.ref", "$(printenv${IFS}DSW_REGISTRY_TOKEN)"),
    ],
)
def test_config_rejects_unsafe_workflow_refs(workspace: Path, field: str, value: str) -> None:
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    section, key = field.split(".")
    text = config_path.read_text(encoding="utf-8")
    old_value = "master" if section == "tooling" else "translation/latest"
    block_value = value.replace("\n", "\n    ")
    text = text.replace(f"  {key}: {old_value}", f"  {key}: |\n    {block_value}")
    config_path.write_text(text, encoding="utf-8")

    with pytest.raises(TranslationRepositoryConfigError, match="safe Git ref"):
        load_translation_repository_config(config_path)


@pytest.mark.parametrize(
    "field",
    [
        "translated_organization_id",
        "translated_km_id",
        "translated_name",
        "supplemental_directory",
        "package_identity_mappings",
    ],
)
def test_config_rejects_obsolete_translated_km_fields(workspace: Path, field: str) -> None:
    config_path = workspace / "translation-config.yml"
    write_config(config_path)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "  target_language_label: zh-Hant",
            f"  target_language_label: zh-Hant\n  {field}: obsolete",
        ),
        encoding="utf-8",
    )

    with pytest.raises(TranslationRepositoryConfigError, match="Unexpected configuration field"):
        load_translation_repository_config(config_path)


def test_validate_translation_config_cli_reports_summary(
    repo_root: Path,
    workspace: Path,
) -> None:
    """Verify the validation CLI used by downstream translation repos."""

    config_path = workspace / "translation-config.yml"
    summary_path = workspace / "summary.md"
    write_config(config_path)

    result = run_cli_command(
        repo_root,
        "dsw-km-validate-config",
        "--config",
        str(config_path),
        "--summary",
        str(summary_path),
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "KM translation config is valid." in result.stdout
    assert "Tracking branch: translation/latest" in result.stdout
    assert "Localize PO URL: https://localize.ds-wizard.org/download/" in result.stdout
    assert "Registry API: https://api.registry.ds-wizard.org" in result.stdout
    assert "## KM Translation Config" in summary_path.read_text(encoding="utf-8")


def test_repository_ci_sync_config_derives_tracking_branch_and_source_paths(
    workspace: Path,
) -> None:
    """Verify CI sync config can be derived from translation-config.yml."""

    host_repo = workspace / "translation-repo"
    tooling_repo = workspace / "tooling-repo"
    host_repo.mkdir()
    tooling_repo.mkdir()
    config_path = host_repo / "translation-config.yml"
    write_config(config_path)

    config = build_repository_ci_sync_config(
        host_repo_path=host_repo,
        tooling_repo_path=tooling_repo,
        config_path=Path("translation-config.yml"),
        mode="schedule",
    )

    assert config.translation_root == "."
    assert config.translation_root_arg == "."
    assert config.target_ref == "translation/latest"
    assert config.restore_source_ref == "origin/translation/latest"
    assert config.source_lang == "en"
    assert config.target_lang == "zh_Hant"
    assert config.source_po_path == Path("sources/localize/zh_Hant/latest.po")
    assert config.source_km_path == Path(
        "sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km"
    )
    assert config.original_po_path == host_repo / "sources/localize/zh_Hant/latest.po"
    assert config.original_model_path == (
        host_repo / "sources/knowledge-models/dsw-root-2.7.0/dsw-root-2.7.0.km"
    )
