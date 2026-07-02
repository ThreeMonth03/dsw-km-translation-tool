"""Tests for checked-in GitHub workflow policy and wiring."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_workflow_yaml(path: Path) -> dict[str, object]:
    """Load one workflow file with a YAML loader that preserves `on`.

    Args:
        path: Workflow YAML path.

    Returns:
        Parsed workflow payload.
    """

    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def test_localize_auto_sync_template_matches_writer_policy(
    repo_root: Path,
) -> None:
    """Verify the Localize auto-sync template matches the intended CI policy.

    Args:
        repo_root: Repository root fixture.
    """

    workflow_path = repo_root / "examples" / "github-actions" / "localize_auto_sync_template.yml"
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["schedule"][0]["cron"] == "0 1,13 * * *"
    assert workflow["on"]["pull_request"]["branches"] == ["master"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "write"
    assert workflow["env"]["TOOLING_REPOSITORY"] == "ThreeMonth03/DSW_Translation_tool"
    assert workflow["env"]["TOOLING_REF"] == "master"
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert workflow["env"]["TRANSLATION_ROOT"] == "."
    assert "localize-translation-auto-sync" in workflow_text
    assert "github.event_name != 'pull_request'" in workflow_text
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow_text
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert "github.event_name == 'pull_request' && 'pull_request' || 'schedule'" in workflow_text
    assert "tooling-repo/src/sync_from_localize.py" in workflow_text
    assert "tooling-repo/src/discover_km_versions.py" not in workflow_text
    assert "tooling-repo/src/sync_latest_km.py" not in workflow_text
    assert "tooling-repo/src/pull_localize_po.py" not in workflow_text
    assert "DSW_REGISTRY_TOKEN" not in workflow_text
    assert "--config" in workflow_text
    assert "--km-version" not in workflow_text
    assert "--skip-without-token" not in workflow_text
    assert "reviews/km_version_discovery.json" not in workflow_text
    assert "--restore-source-ref" in workflow_text
    assert "origin/${{ env.TRACKING_BRANCH }}" in workflow_text
    assert "Skipping auto-sync commit for fork pull requests." in workflow_text


def test_localize_status_report_template_is_read_only(repo_root: Path) -> None:
    """Verify the status report template cannot write translations."""

    workflow_path = (
        repo_root / "examples" / "github-actions" / "localize_status_report_template.yml"
    )
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["schedule"][0]["cron"] == "30 1,13 * * *"
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["env"]["TOOLING_REPOSITORY"] == "ThreeMonth03/DSW_Translation_tool"
    assert workflow["env"]["TOOLING_REF"] == "master"
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TARGET_LANG"] == "zh_Hant"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert "KNOWN_FUZZY_REFERENCES" not in workflow["env"]
    assert "tooling-repo/src/pull_localize_po.py" in workflow_text
    assert "tooling-repo/src/report_localize_status.py" in workflow_text
    assert "tooling-repo/src/report_weblate_checks.py" in workflow_text
    assert "secrets.LOCALIZE_API_TOKEN" in workflow_text
    assert "translation-repo/reviews/localize_status_report.json" in workflow_text
    assert "translation-repo/reviews/localize_status_report.md" in workflow_text
    assert "translation-repo/reviews/weblate_checks_report.json" in workflow_text
    assert "translation-repo/reviews/weblate_checks_report.md" in workflow_text
    assert "--details-out" in workflow_text
    assert "--known-" not in workflow_text
    assert "--allow-api-failure" in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert "sync_from_localize.py" not in workflow_text
    assert "contents: write" not in workflow_text


def test_localize_alignment_report_template_is_read_only(repo_root: Path) -> None:
    """Verify the alignment report template only checks repository consistency."""

    workflow_path = (
        repo_root / "examples" / "github-actions" / "localize_alignment_report_template.yml"
    )
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["schedule"][0]["cron"] == "45 1,13 * * *"
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["env"]["TOOLING_REPOSITORY"] == "ThreeMonth03/DSW_Translation_tool"
    assert workflow["env"]["TOOLING_REF"] == "master"
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert "tooling-repo/src/report_alignment_status.py" in workflow_text
    assert "--fail-on-mismatch" in workflow_text
    assert "translation-repo/reviews/localize_alignment_report.json" in workflow_text
    assert "translation-repo/reviews/localize_alignment_artifacts/" in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert "pull_localize_po.py" not in workflow_text
    assert "sync_from_localize.py" not in workflow_text
    assert "contents: write" not in workflow_text


def test_km_version_auto_update_template_is_guarded_writer(repo_root: Path) -> None:
    """Verify the KM version auto-update template writes Git only after validation."""

    workflow_path = (
        repo_root / "examples" / "github-actions" / "km_version_auto_update_template.yml"
    )
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["schedule"][0]["cron"] == "15 2 * * *"
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "write"
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert workflow["env"]["TOOLING_REPOSITORY"] == "ThreeMonth03/DSW_Translation_tool"
    assert workflow["env"]["TOOLING_REF"] == "master"
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert "tooling-repo/src/sync_latest_km.py" in workflow_text
    assert "--target-ref" in workflow_text
    assert '--report "$RUNNER_TEMP/km_auto_update_report.json"' in workflow_text
    assert '--details-out "$RUNNER_TEMP/km_auto_update_report.md"' in workflow_text
    assert "secrets.DSW_REGISTRY_TOKEN" in workflow_text
    assert "km-version-auto-update" in workflow_text
    assert "if-no-files-found: ignore" in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert "sync_from_localize.py" not in workflow_text


def test_validate_translation_config_template_is_read_only(repo_root: Path) -> None:
    """Verify the config validation template cannot write translations."""

    workflow_path = (
        repo_root / "examples" / "github-actions" / "validate_translation_config_template.yml"
    )
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["pull_request"]["branches"] == ["master"]
    assert workflow["on"]["push"]["branches"] == ["master"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert workflow["env"]["TOOLING_REPOSITORY"] == "ThreeMonth03/DSW_Translation_tool"
    assert workflow["env"]["TOOLING_REF"] == "master"
    assert "tooling-repo/src/validate_translation_config.py" in workflow_text
    assert "--summary" in workflow_text
    assert "sync_from_localize.py" not in workflow_text
    assert "sync_latest_km.py" not in workflow_text
    assert "DSW_REGISTRY_TOKEN" not in workflow_text
    assert "contents: write" not in workflow_text
