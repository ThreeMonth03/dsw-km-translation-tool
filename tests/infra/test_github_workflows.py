"""Tests for checked-in GitHub workflow policy and wiring."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

import yaml

from dsw_km_translation_tool.translation_repository_config import (
    load_translation_repository_config,
)
from dsw_km_translation_tool.translation_repository_scaffold import (
    render_translation_repository_scaffold,
)

EXPECTED_TOOLING_REPOSITORY = "ThreeMonth03/dsw-km-translation-tool"
EXPECTED_TOOLING_REF = "REPLACE_WITH_COMMIT_SHA"


def test_artifact_cleanup_is_pinned_and_does_not_run_pr_code(repo_root: Path) -> None:
    wrapper, wrapper_text = load_rendered_workflow(repo_root, "artifact_cleanup_template.yml")
    assert wrapper["on"] == {"pull_request": {"types": ["closed"], "branches": ["master"]}}
    assert "pull_request_target" not in wrapper_text
    job = wrapper["jobs"]["cleanup"]
    assert job["uses"].endswith("/cleanup_pr_artifacts.yml@" + EXPECTED_TOOLING_REF)
    assert job["with"]["tooling_ref"] == EXPECTED_TOOLING_REF
    assert job["if"] == (
        "github.event.pull_request.merged == true && "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    assert job["with"]["apply"] == "true"
    implementation = repo_root / ".github/workflows/cleanup_pr_artifacts.yml"
    reusable = load_workflow_yaml(implementation)
    assert reusable["permissions"] == {
        "contents": "read",
        "actions": "write",
        "pull-requests": "read",
    }
    text = implementation.read_text()
    assert "secrets." not in text
    assert "upload-artifact" not in text
    assert "github.head_ref" not in text
    checkout = reusable["jobs"]["cleanup"]["steps"][1]
    assert checkout["with"]["ref"] == "${{ inputs.tooling_ref }}"
    assert checkout["with"]["persist-credentials"] == "false"


def test_tool_artifact_cleanup_only_runs_after_merge(repo_root: Path) -> None:
    workflow = load_workflow_yaml(repo_root / ".github/workflows/artifact_cleanup.yml")
    assert workflow["on"] == {"pull_request": {"types": ["closed"], "branches": ["master"]}}
    job = workflow["jobs"]["cleanup"]
    assert job["if"] == (
        "github.event.pull_request.merged == true && "
        "github.event.pull_request.head.repo.full_name == github.repository"
    )
    assert job["with"]["tooling_ref"] == "${{ github.sha }}"
    assert job["with"]["apply"] == "true"


def test_contributor_guide_names_the_translation_workflow(repo_root: Path) -> None:
    """Keep the contributor-facing CI name aligned with the rendered workflow."""

    config = load_translation_repository_config(repo_root / "examples" / "translation-config.yml")
    files = {
        item.path: item.content
        for item in render_translation_repository_scaffold(tooling_repo=repo_root, config=config)
    }
    workflow = yaml.load(
        files[Path(".github/workflows/validate_translation_config.yml")],
        Loader=yaml.BaseLoader,
    )

    assert f"**{workflow['name']}**" in files[Path("docs/contributing.md")]


def test_native_locale_release_is_automatic_and_pinned(repo_root: Path) -> None:
    workflow, text = load_rendered_workflow(repo_root, "release_template.yml")
    assert workflow["on"]["workflow_run"]["types"] == ["completed"]
    assert workflow["on"]["workflow_run"]["branches"] == ["master"]
    assert set(workflow["on"]["workflow_run"]["workflows"]) == {
        "Localize Translation Auto Sync",
        "GitHub Translation Import",
        "KM Version Auto Update",
    }
    assert "workflow_dispatch" in workflow["on"]
    assert "push" not in workflow["on"]
    assert workflow["concurrency"]["group"] == "locale-release-master"
    assert "pull_request" not in workflow["on"]
    assert workflow["permissions"] == {"contents": "write"}
    assert text.count("persist-credentials: false") == 2
    assert "--tooling-repo tooling-repo" in text
    assert "dsw-km-prepare-locale-release" in text
    assert '--target "$RELEASE_COMMIT" --draft' in text
    assert "--draft=false --latest" in text
    assert "secrets." not in text
    assert "dsw-km-import-github-translations" not in text
    steps = workflow["jobs"]["release"]["steps"]
    native = next(
        i for i, step in enumerate(steps) if step.get("uses", "").endswith("/native-locale")
    )
    publish = next(
        i for i, step in enumerate(steps) if step.get("name") == "Publish GitHub release"
    )
    assert native < publish
    assert "continue-on-error" not in steps[native]
    alignment = next(
        i for i, step in enumerate(steps) if step.get("name") == "Verify Weblate alignment"
    )
    assert alignment < native
    assert "Tracking branch advanced during validation" in text
    command = steps[publish]["run"]
    assert '"$assets/$po_filename" "$assets/manifest.json" "$assets/SHA256SUMS"' in command
    assert "*" not in command
    assert '--notes-file "$RUNNER_TEMP/locale-release/release-notes.md"' in command


def load_workflow_yaml(path: Path) -> dict[str, object]:
    """Load one workflow file with a YAML loader that preserves `on`.

    Args:
        path: Workflow YAML path.

    Returns:
        Parsed workflow payload.
    """

    return yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)


def load_rendered_workflow(
    repo_root: Path,
    template_name: str,
) -> tuple[dict[str, object], str]:
    """Render one workflow template with the example repository config."""

    target_name = template_name.removesuffix("_template.yml") + ".yml"
    target_path = Path(".github") / "workflows" / target_name
    config = load_translation_repository_config(repo_root / "examples" / "translation-config.yml")
    files = render_translation_repository_scaffold(tooling_repo=repo_root, config=config)
    rendered = next(item.content for item in files if item.path == target_path)
    return yaml.load(rendered, Loader=yaml.BaseLoader), rendered


def assert_tooling_checkout_env(workflow: dict[str, object]) -> None:
    """Verify a workflow checks out the expected tooling repository ref."""

    assert workflow["env"]["TOOLING_REPOSITORY"] == EXPECTED_TOOLING_REPOSITORY
    assert workflow["env"]["TOOLING_REF"] == EXPECTED_TOOLING_REF


def test_localize_auto_sync_template_matches_writer_policy(
    repo_root: Path,
) -> None:
    """Verify the Localize auto-sync template matches the intended CI policy.

    Args:
        repo_root: Repository root fixture.
    """

    workflow, workflow_text = load_rendered_workflow(
        repo_root,
        "localize_auto_sync_template.yml",
    )

    assert workflow["on"]["schedule"][0]["cron"] == "0 1,13 * * *"
    assert "pull_request" not in workflow["on"]
    assert "workflow_dispatch" not in workflow["on"]
    assert workflow["permissions"]["contents"] == "write"
    assert set(workflow["concurrency"]) == {"group", "cancel-in-progress"}
    assert_tooling_checkout_env(workflow)
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert workflow["env"]["TRANSLATION_ROOT"] == "."
    assert "if" not in workflow["jobs"]["sync-writer"]
    assert "translation-state-master" in workflow_text
    assert "refs/remotes/base/$TRACKING_BRANCH" in workflow_text
    assert "tooling-repo/.venv/bin/dsw-km-sync-localize" in workflow_text
    assert "tooling-repo/src/" not in workflow_text
    assert "dsw-km-discover-versions" not in workflow_text
    assert "dsw-km-sync-latest-km" not in workflow_text
    assert "dsw-km-pull-localize-po" not in workflow_text
    assert "DSW_REGISTRY_TOKEN" not in workflow_text
    assert "--config" in workflow_text
    assert "--km-version" not in workflow_text
    assert "--skip-without-token" not in workflow_text
    assert "reviews/km_version_discovery.json" not in workflow_text
    assert "--restore-source-ref" in workflow_text
    assert "base/$TRACKING_BRANCH" in workflow_text
    assert "github.event.pull_request" not in workflow_text


def test_github_translation_import_template_is_guarded_writer(repo_root: Path) -> None:
    """Verify GitHub translation import writes Weblate only after merge."""

    workflow, workflow_text = load_rendered_workflow(
        repo_root,
        "github_translation_import_template.yml",
    )

    assert workflow["on"]["push"]["branches"] == ["master"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["on"]["workflow_dispatch"]["inputs"]["base_ref"]["default"] == "HEAD^"
    assert workflow["on"]["workflow_dispatch"]["inputs"]["head_ref"]["default"] == "HEAD"
    assert workflow["permissions"]["contents"] == "write"
    assert workflow["concurrency"]["group"] == "translation-state-master"
    assert set(workflow["concurrency"]) == {"group", "cancel-in-progress"}
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert_tooling_checkout_env(workflow)
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert "secrets.LOCALIZE_API_TOKEN" in workflow_text
    assert "tooling-repo/.venv/bin/dsw-km-import-github-translations" in workflow_text
    assert "tooling-repo/.venv/bin/dsw-km-sync-localize" in workflow_text
    assert (
        "steps.import-github-translations.outputs.has_translation_changes == 'true'"
        in workflow_text
    )
    assert "github-translation-import" in workflow_text
    assert "pull_request" not in workflow["on"]
    assert "DSW_REGISTRY_TOKEN" not in workflow_text
    assert "tooling-repo/src/" not in workflow_text


def test_localize_status_report_template_is_read_only(repo_root: Path) -> None:
    """Verify the status report template cannot write translations."""

    workflow, workflow_text = load_rendered_workflow(
        repo_root,
        "localize_status_report_template.yml",
    )

    assert workflow["on"]["schedule"][0]["cron"] == "30 1,13 * * *"
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert_tooling_checkout_env(workflow)
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert "KNOWN_FUZZY_REFERENCES" not in workflow["env"]
    assert "dsw-km-pull-localize-po" not in workflow_text
    assert '--repo-root "$GITHUB_WORKSPACE/translation-repo"' in workflow_text
    assert "tooling-repo/.venv/bin/dsw-km-report-localize-status" in workflow_text
    assert "tooling-repo/.venv/bin/dsw-km-report-weblate-checks" in workflow_text
    assert "secrets.LOCALIZE_API_TOKEN" in workflow_text
    assert "translation-repo/reviews/localize_status_report.json" in workflow_text
    assert "translation-repo/reviews/localize_status_report.md" in workflow_text
    assert "translation-repo/reviews/weblate_checks_report.json" in workflow_text
    assert "translation-repo/reviews/weblate_checks_report.md" in workflow_text
    assert "--details-out" in workflow_text
    assert "--known-" not in workflow_text
    assert "--allow-api-failure" in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert workflow_text.count("persist-credentials: false") == 2
    assert "dsw-km-sync-localize" not in workflow_text
    assert "tooling-repo/src/" not in workflow_text
    assert "contents: write" not in workflow_text


def test_localize_alignment_report_template_is_read_only(repo_root: Path) -> None:
    """Verify the alignment report template only checks repository consistency."""

    workflow, workflow_text = load_rendered_workflow(
        repo_root,
        "localize_alignment_report_template.yml",
    )

    assert workflow["on"]["schedule"][0]["cron"] == "45 1,13 * * *"
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert_tooling_checkout_env(workflow)
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert "tooling-repo/.venv/bin/dsw-km-report-alignment" in workflow_text
    assert "--fail-on-mismatch" in workflow_text
    assert "translation-repo/reviews/localize_alignment_report.json" in workflow_text
    assert "translation-repo/reviews/localize_alignment_artifacts/" in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert "dsw-km-pull-localize-po" not in workflow_text
    assert "dsw-km-sync-localize" not in workflow_text
    assert "tooling-repo/src/" not in workflow_text
    assert "contents: write" not in workflow_text


def test_km_version_auto_update_template_is_guarded_writer(repo_root: Path) -> None:
    """Verify the KM version auto-update template writes Git only after validation."""

    workflow, workflow_text = load_rendered_workflow(
        repo_root,
        "km_version_auto_update_template.yml",
    )

    assert workflow["on"]["schedule"][0]["cron"] == "15 2 * * *"
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "write"
    assert workflow["concurrency"]["group"] == "translation-state-master"
    assert set(workflow["concurrency"]) == {"group", "cancel-in-progress"}
    assert "github.actor != 'github-actions[bot]'" in workflow_text
    assert_tooling_checkout_env(workflow)
    assert workflow["env"]["TRACKING_BRANCH"] == "master"
    assert workflow["env"]["TRANSLATION_CONFIG"] == "translation-config.yml"
    assert "tooling-repo/.venv/bin/dsw-km-sync-latest-km" in workflow_text
    assert "--target-ref" in workflow_text
    assert '--report "$RUNNER_TEMP/km_auto_update_report.json"' in workflow_text
    assert '--details-out "$RUNNER_TEMP/km_auto_update_report.md"' in workflow_text
    assert "secrets.DSW_REGISTRY_TOKEN" in workflow_text
    assert "km-version-auto-update" in workflow_text
    assert "if-no-files-found: ignore" in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert "dsw-km-sync-localize" not in workflow_text
    assert "tooling-repo/src/" not in workflow_text


def test_validate_translation_config_template_is_read_only(repo_root: Path) -> None:
    """Verify the config validation template cannot write translations."""

    workflow, workflow_text = load_rendered_workflow(
        repo_root,
        "validate_translation_config_template.yml",
    )

    assert workflow["on"]["pull_request"]["branches"] == ["master"]
    assert workflow["on"]["push"]["branches"] == ["master"]
    assert "workflow_dispatch" in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert_tooling_checkout_env(workflow)
    assert "tooling-repo/.venv/bin/dsw-km-validate-config" in workflow_text
    assert "github.event.pull_request.head.repo.full_name" in workflow_text
    assert "github.event.pull_request.head.sha" in workflow_text
    assert "github.event.pull_request.base.repo.full_name" in workflow_text
    assert "github.event.pull_request.base.sha" in workflow_text
    assert "pull-request-base" in workflow_text
    assert 'git fetch "$GITHUB_WORKSPACE/pull-request-base" HEAD' in workflow_text
    assert 'git fetch "https://github.com/' not in workflow_text
    assert "refs/remotes/base/pr-base" in workflow_text
    assert "tooling-repo/.venv/bin/dsw-km-report-github-translations" in workflow_text
    assert '--base-ref "base/pr-base"' in workflow_text
    assert '--head-ref "HEAD"' in workflow_text
    assert '--github-output "$GITHUB_OUTPUT"' in workflow_text
    assert "actions/upload-artifact@v7" in workflow_text
    assert workflow_text.count("persist-credentials: false") == 3
    assert "tooling-repo/.venv/bin/dsw-km-scaffold check" in workflow_text
    assert "--summary" in workflow_text
    assert "dsw-km-sync-repository-shared-strings" not in workflow_text
    assert "git diff --exit-code" not in workflow_text
    assert "native-locale-${{ github.event.pull_request.head.sha || github.sha }}" in workflow_text
    assert "translation-repo/builds/final_translated.po" in workflow_text
    assert "dsw-km-sync-localize" not in workflow_text
    assert "dsw-km-sync-latest-km" not in workflow_text
    assert "tooling-repo/src/" not in workflow_text
    assert "DSW_REGISTRY_TOKEN" not in workflow_text
    assert "contents: write" not in workflow_text
    assert workflow["on"]["schedule"][0]["cron"] == "45 3 * * *"
    assert "uses: ./tooling-repo/.github/actions/native-locale" in workflow_text
    assert "secrets." not in workflow_text
    preview = next(
        step
        for step in workflow["jobs"]["validate-translation-config"]["steps"]
        if step.get("name") == "Upload native locale preview"
    )
    assert preview["if"] == (
        "steps.translation-changes.outputs.has_translation_changes == 'true' "
        "|| inputs.upload_review == true"
    )
    assert workflow["on"]["workflow_dispatch"]["inputs"]["upload_review"]["default"] == "false"
    assert "name: github-translation-report" not in workflow_text
    steps = workflow["jobs"]["validate-translation-config"]["steps"]
    rebuild = next(
        step for step in steps if step.get("name") == "Rebuild and validate native DSW locale"
    )
    assert rebuild["env"]["VALIDATE_PR_OUTPUTS"] == "${{ github.event_name == 'pull_request' }}"
    assert 'args+=(--base-ref "base/pr-base" --head-ref "HEAD")' in rebuild["run"]
    assert '"${args[@]}"' in rebuild["run"]
    native = next(step for step in steps if step.get("uses", "").endswith("/native-locale"))
    assert native["with"]["trusted-config"] == (
        "${{ github.event_name == 'pull_request' && "
        "format('{0}/pull-request-base/translation-config.yml', github.workspace) || '' }}"
    )


def test_native_locale_action_is_isolated_and_retains_failure_artifacts(
    repo_root: Path,
) -> None:
    action = load_workflow_yaml(repo_root / ".github/actions/native-locale/action.yml")
    review, failure = action["runs"]["steps"][-2:]
    assert action["inputs"]["upload-review"]["default"] == "false"
    assert review["if"] == "success() && inputs.upload-review == 'true'"
    assert review["with"]["retention-days"] == "7"
    assert failure["if"] == (
        "failure() && (steps.verify.outcome == 'failure' || steps.audit.outcome == 'failure')"
    )
    assert failure["with"]["retention-days"] == "3"
    assert "failure.png" in failure["with"]["path"]
    assert "/*.png" not in failure["with"]["path"]
    assert "continue-on-error" not in str(action)
    assert {step.get("id") for step in action["runs"]["steps"]} >= {"verify", "audit"}
    steps = action["runs"]["steps"]
    network = next(
        i for i, step in enumerate(steps) if step.get("name") == "Verify browser network isolation"
    )
    verify = next(i for i, step in enumerate(steps) if step.get("id") == "verify")
    assert network < verify
    assert steps[network]["run"] == ".venv/bin/python tests/native_locale/network_check.py"
    audit = next(step for step in steps if step.get("id") == "audit")
    assert audit["env"]["TRUSTED_CONFIG"] == "${{ inputs.trusted-config }}"
    assert 'args+=(--trusted-config "$TRUSTED_CONFIG")' in audit["run"]
    compose = load_workflow_yaml(repo_root / "tests/native_locale/compose.yml")
    for service in compose["services"].values():
        assert not service["image"].endswith(":latest")
        for port in service.get("ports", []):
            assert port.startswith("127.0.0.1:${DSW_TEST_")
    docs = (repo_root / "docs/km-update-runbook.md").read_text()
    assert "The sync writer has no manual trigger" in docs


def test_native_storage_builds_pinned_official_release_assets(repo_root: Path) -> None:
    compose = load_workflow_yaml(repo_root / "tests/native_locale/compose.yml")
    for name, target in (("minio", "minio"), ("bucket", "mc")):
        service = compose["services"][name]
        assert service["image"].startswith(f"dsw-ci-{target}:RELEASE.")
        assert service["platform"] == "linux/amd64"
        assert service["pull_policy"] == "build"
        assert service["build"] == {
            "context": "${DSW_TEST_STORAGE_CONTEXT:?}",
            "target": target,
        }
    dockerfile = (repo_root / "tests/native_locale/storage/Dockerfile").read_text()
    assert re.search(r"^FROM debian:bookworm-slim@sha256:[0-9a-f]{64} AS base$", dockerfile, re.M)
    assert len(re.findall(r"^ADD .*--checksum=sha256:[0-9a-f]{64}\s", dockerfile, re.M)) == 2
    for project in ("minio", "mc"):
        assert f"https://github.com/minio/{project}/releases/download/RELEASE." in dockerfile
    checker = (repo_root / "tests/native_locale/check.py").read_text()
    assert '"DSW_TEST_STORAGE_CONTEXT": str(COMPOSE.parent / "storage")' in checker


def test_report_and_preview_artifacts_have_explicit_retention(repo_root: Path) -> None:
    """Keep routine artifacts bounded without expiring human-review previews early."""

    expected = {
        "github-translation-import": "7",
        "km-version-auto-update": "7",
        "localize-alignment-report": "7",
        "localize-status-report": "7",
        "native-locale-${{ github.event.pull_request.head.sha || github.sha }}": "7",
    }
    config = load_translation_repository_config(repo_root / "examples/translation-config.yml")
    workflows = [
        yaml.load(item.content, Loader=yaml.BaseLoader)
        for item in render_translation_repository_scaffold(tooling_repo=repo_root, config=config)
        if item.path.parent == Path(".github/workflows")
    ]
    workflows.extend(
        load_workflow_yaml(path) for path in (repo_root / ".github/workflows").glob("*.yml")
    )
    actual = {}
    for workflow in workflows:
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                if step.get("uses", "").startswith("actions/upload-artifact@"):
                    settings = step["with"]
                    assert settings["retention-days"] == expected[settings["name"]]
                    actual[settings["name"]] = settings["retention-days"]
    assert actual == expected


def test_tooling_ci_and_release_run_native_acceptance(repo_root: Path) -> None:
    for filename in ("unittest.yml", "release.yml"):
        workflow = load_workflow_yaml(repo_root / ".github/workflows" / filename)
        assert any(
            step.get("uses") == "./.github/actions/native-locale"
            for job in workflow["jobs"].values()
            for step in job["steps"]
        )


def test_workflow_templates_render_non_default_tracking_branch(repo_root: Path) -> None:
    """Verify every branch placeholder follows repository configuration."""

    config = load_translation_repository_config(repo_root / "examples" / "translation-config.yml")
    config = replace(
        config,
        branches=replace(config.branches, tracking_branch="release"),
    )
    files = render_translation_repository_scaffold(tooling_repo=repo_root, config=config)
    workflows = {
        item.path.name: (yaml.load(item.content, Loader=yaml.BaseLoader), item.content)
        for item in files
        if item.path.parent == Path(".github/workflows")
    }

    validation, _ = workflows["validate_translation_config.yml"]
    assert validation["on"]["pull_request"]["branches"] == ["release"]
    assert validation["on"]["push"]["branches"] == ["release"]

    auto_sync, auto_sync_text = workflows["localize_auto_sync.yml"]
    assert "pull_request" not in auto_sync["on"]
    assert "translation-state-release" in auto_sync_text

    github_import, _ = workflows["github_translation_import.yml"]
    assert github_import["on"]["push"]["branches"] == ["release"]
    assert github_import["concurrency"]["group"] == "translation-state-release"

    for _, workflow_text in workflows.values():
        for token in ("TOOLING_REPOSITORY", "TOOLING_REF", "TRACKING_BRANCH"):
            assert f"{{{{{token}}}}}" not in workflow_text


def test_upstream_smoke_workflow_is_tooling_integration_check(repo_root: Path) -> None:
    """Verify the tooling repo smoke workflow checks live upstream sources."""

    workflow_path = repo_root / ".github" / "workflows" / "upstream_smoke.yml"
    workflow = load_workflow_yaml(workflow_path)
    workflow_text = workflow_path.read_text(encoding="utf-8")

    assert workflow["on"]["schedule"][0]["cron"] == "20 3 * * *"
    assert "workflow_dispatch" not in workflow["on"]
    assert workflow["permissions"]["contents"] == "read"
    assert "actions/cache/restore@v5" in workflow_text
    assert "actions/cache/save@v5" in workflow_text
    assert ".cache/upstream-smoke/sources/knowledge-models" in workflow_text
    assert "make upstream-smoke" in workflow_text
    assert "secrets.DSW_REGISTRY_TOKEN" in workflow_text
    assert "actions/upload-artifact" not in workflow_text
    assert "GITHUB_STEP_SUMMARY" in workflow_text
    assert "git push" not in workflow_text
    assert "contents: write" not in workflow_text


def test_routine_report_uploads_require_manual_opt_in(repo_root: Path) -> None:
    for template in (
        "localize_status_report_template.yml",
        "localize_alignment_report_template.yml",
        "km_version_auto_update_template.yml",
    ):
        workflow, text = load_rendered_workflow(repo_root, template)
        assert workflow["on"]["workflow_dispatch"]["inputs"]["upload_report"]["default"] == "false"
        assert "GITHUB_STEP_SUMMARY" in text
        uploads = [
            step
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if step.get("uses", "").startswith("actions/upload-artifact@")
        ]
        assert len(uploads) == 1
        assert uploads[0]["if"] == "always() && inputs.upload_report == true"


def test_workflow_run_blocks_do_not_interpolate_repository_config(
    repo_root: Path,
) -> None:
    """Repository-config values must reach shells through quoted variables."""

    template_names = (
        "github_translation_import_template.yml",
        "km_version_auto_update_template.yml",
        "localize_alignment_report_template.yml",
        "localize_auto_sync_template.yml",
        "localize_status_report_template.yml",
        "validate_translation_config_template.yml",
    )
    expression_prefix = "$" + "{{ env."
    for template_name in template_names:
        workflow, _ = load_rendered_workflow(repo_root, template_name)
        run_blocks = [
            step["run"]
            for job in workflow["jobs"].values()
            for step in job["steps"]
            if "run" in step
        ]
        assert run_blocks
        assert all(expression_prefix not in run_block for run_block in run_blocks)
