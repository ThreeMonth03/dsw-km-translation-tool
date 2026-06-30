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


def test_translation_auto_sync_workflow_matches_writer_policy(repo_root: Path) -> None:
    """Verify the in-repo auto-sync workflow matches the intended CI policy.

    Args:
        repo_root: Repository root fixture.
    """

    workflow_path = repo_root / ".github" / "workflows" / "translation_auto_sync.yml"
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["schedule"][0]["cron"] == "0 1,13 * * *"
    assert workflow["on"]["pull_request"]["branches"] == ["master"]
    assert workflow["permissions"]["contents"] == "write"
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow_text
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert "src/ci_sync_commit.py" in workflow_text
    assert "origin/master" in workflow_text
    assert "Skipping auto-sync commit for fork pull requests." in workflow_text
    assert "chore(sync): refresh translation artifacts" not in workflow_text


def test_external_translation_auto_sync_template_matches_writer_policy(
    repo_root: Path,
) -> None:
    """Verify the external auto-sync template matches the intended CI policy.

    Args:
        repo_root: Repository root fixture.
    """

    workflow_path = (
        repo_root / "examples" / "github-actions" / "translation_external_auto_sync_template.yml"
    )
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["schedule"][0]["cron"] == "0 1,13 * * *"
    assert workflow["on"]["pull_request"]["branches"] == ["translation/v2.7.0"]
    assert workflow["permissions"]["contents"] == "write"
    assert workflow["env"]["TOOLING_REPOSITORY"] == "ThreeMonth03/DSW_Translation_tool"
    assert workflow["env"]["TOOLING_REF"] == "master"
    assert workflow["env"]["KM_VERSION"] == "2.7.0"
    assert workflow["env"]["VERSION_BRANCH"] == "translation/v2.7.0"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert workflow["env"]["TRANSLATION_ROOT"] == "."
    assert "github.event.pull_request.head.repo.full_name == github.repository" in workflow_text
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert "tooling-repo/src/ci_sync_commit.py" in workflow_text
    assert "tooling-repo/src/discover_km_versions.py" in workflow_text
    assert "tooling-repo/src/pull_km_bundle.py" in workflow_text
    assert "tooling-repo/src/pull_localize_po.py" in workflow_text
    assert "DSW_REGISTRY_TOKEN" in workflow_text
    assert "--config" in workflow_text
    assert "--km-version" in workflow_text
    assert "--skip-without-token" in workflow_text
    assert "reviews/km_version_discovery.json" in workflow_text
    assert "--restore-source-ref" in workflow_text
    assert "origin/${{ env.VERSION_BRANCH }}" in workflow_text
    assert "Skipping auto-sync commit for fork pull requests." in workflow_text
