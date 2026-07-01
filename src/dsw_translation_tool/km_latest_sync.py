"""Automation for keeping one translation branch on the latest KM version."""

from __future__ import annotations

import os
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

from .ci_sync import GITHUB_BOT_EMAIL, GITHUB_BOT_NAME
from .km_bundle_sync import pull_km_bundle
from .km_registry import Downloader, discover_km_versions
from .localize_sync import pull_localize_po
from .translation_repository_config import (
    TranslationRepositoryConfigError,
    load_translation_repository_config,
    sorted_versions,
    version_paths,
)


class CommandRunner(Protocol):
    """Protocol for command execution used by latest-KM synchronization."""

    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run one command and return its completed process."""


class KmLatestSyncError(RuntimeError):
    """Raised when latest-KM synchronization cannot complete."""


@dataclass(frozen=True)
class KmLatestSyncResult:
    """Summary of one latest-KM sync run."""

    configured_version: str
    registry_version: str | None
    changed: bool
    skipped_reason: str | None = None
    dry_run: bool = False


def sync_latest_km_version(
    *,
    repo_root: Path,
    tooling_repo: Path,
    config_path: Path,
    registry_token: str,
    skip_without_token: bool = False,
    dry_run: bool = False,
    downloader: Downloader | None = None,
    runner: CommandRunner | None = None,
) -> KmLatestSyncResult:
    """Update the current translation branch when the Registry has a newer KM."""

    host_repo = repo_root.resolve()
    tooling_root = tooling_repo.resolve()
    resolved_config_path = _resolve_repo_path(host_repo, config_path)
    config = load_translation_repository_config(resolved_config_path)
    configured_version = config.knowledge_model.supported_versions[-1]
    discovery = discover_km_versions(config_path=resolved_config_path, downloader=downloader)
    registry_version = discovery.latest_registry_version
    if registry_version is None or registry_version == configured_version:
        return KmLatestSyncResult(
            configured_version=configured_version,
            registry_version=registry_version,
            changed=False,
            dry_run=dry_run,
        )
    if registry_version in config.knowledge_model.supported_versions:
        return KmLatestSyncResult(
            configured_version=configured_version,
            registry_version=registry_version,
            changed=False,
            skipped_reason="configured-version-order-is-not-latest",
            dry_run=dry_run,
        )
    if not registry_token.strip():
        if skip_without_token:
            return KmLatestSyncResult(
                configured_version=configured_version,
                registry_version=registry_version,
                changed=False,
                skipped_reason="missing-registry-token",
                dry_run=dry_run,
            )
        raise KmLatestSyncError("A newer KM exists, but no DSW Registry token was provided.")
    if dry_run:
        return KmLatestSyncResult(
            configured_version=configured_version,
            registry_version=registry_version,
            changed=False,
            dry_run=True,
        )

    run = runner or default_command_runner
    _ensure_git_repo_is_clean(host_repo, run)
    branch = _git_current_branch(host_repo, run)
    update_supported_versions_in_config(resolved_config_path, [registry_version])
    config = load_translation_repository_config(resolved_config_path)
    pull_km_bundle(
        config_path=resolved_config_path,
        repo_root=host_repo,
        token=registry_token,
        km_version=registry_version,
    )
    pull_localize_po(
        config_path=resolved_config_path,
        repo_root=host_repo,
        km_version=registry_version,
    )
    _run_export_tree(
        repo_root=host_repo,
        tooling_repo=tooling_root,
        config_path=resolved_config_path,
        version=registry_version,
        runner=run,
    )
    _run_sync_merge_build_and_tests(
        repo_root=host_repo,
        tooling_repo=tooling_root,
        config_path=config_path,
        version=registry_version,
        runner=run,
    )
    _commit_and_push(
        repo_root=host_repo,
        branch=branch,
        message=f"chore(sync): update source KM to {registry_version}",
        runner=run,
    )
    return KmLatestSyncResult(
        configured_version=configured_version,
        registry_version=registry_version,
        changed=True,
        dry_run=False,
    )


def update_supported_versions_in_config(
    config_path: Path, versions: Sequence[str]
) -> tuple[str, ...]:
    """Add known KM versions to config in sorted order."""

    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TranslationRepositoryConfigError("translation-config.yml must contain a mapping")
    knowledge_model = payload.get("knowledge_model")
    if not isinstance(knowledge_model, dict):
        raise TranslationRepositoryConfigError("Expected mapping at `knowledge_model`")
    existing = knowledge_model.get("supported_versions")
    if not isinstance(existing, list):
        raise TranslationRepositoryConfigError("Expected string list at `supported_versions`")
    merged = tuple(dict.fromkeys(sorted_versions([*(str(item) for item in existing), *versions])))
    knowledge_model["supported_versions"] = list(merged)
    config_path.write_text(
        yaml.safe_dump(payload, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return merged


def default_command_runner(
    args: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run a subprocess command."""

    command_env = os.environ.copy()
    if env:
        command_env.update(env)
    return subprocess.run(
        list(args),
        cwd=str(cwd),
        env=command_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _run_export_tree(
    *,
    repo_root: Path,
    tooling_repo: Path,
    config_path: Path,
    version: str,
    runner: CommandRunner,
) -> None:
    config = load_translation_repository_config(config_path)
    paths = version_paths(config, version)
    _run_checked(
        runner,
        [
            str(_tooling_python(tooling_repo)),
            "src/po_json_tree.py",
            "--po",
            str(repo_root / paths.localize_latest_po_path),
            "--json",
            str(repo_root / paths.source_km_path),
            "--out-dir",
            str(repo_root / paths.translation_tree_dir),
            "--outline-out",
            str(repo_root / paths.translation_tree_dir / "outline.md"),
            "--shared-blocks-dir-out",
            str(repo_root / paths.translation_tree_dir / "shared_blocks"),
            "--source-lang",
            config.translation.source_language,
            "--target-lang",
            config.translation.target_language,
        ],
        cwd=tooling_repo,
        description=f"export translation tree for KM {version}",
        echo_output=True,
    )


def _run_sync_merge_build_and_tests(
    *,
    repo_root: Path,
    tooling_repo: Path,
    config_path: Path,
    version: str,
    runner: CommandRunner,
) -> None:
    config = load_translation_repository_config(_resolve_repo_path(repo_root, config_path))
    paths = version_paths(config, version)
    python = _tooling_python(tooling_repo)
    _run_checked(
        runner,
        [
            str(python),
            "src/sync_shared_strings.py",
            "--tree-dir",
            str(repo_root / paths.translation_tree_dir),
            "--original-po",
            str(repo_root / paths.localize_latest_po_path),
            "--out-po",
            str(repo_root / paths.final_po_path),
            "--diff-out",
            str(repo_root / paths.review_diff_path),
            "--outline-out",
            str(repo_root / paths.translation_tree_dir / "outline.md"),
            "--shared-blocks-dir-out",
            str(repo_root / paths.translation_tree_dir / "shared_blocks"),
            "--shared-blocks-outline-out",
            str(repo_root / paths.translation_tree_dir / "shared_blocks_outline.md"),
            "--source-lang",
            config.translation.source_language,
            "--target-lang",
            config.translation.target_language,
            "--group-by",
            "shared-block",
        ],
        cwd=tooling_repo,
        description=f"sync translation artifacts for KM {version}",
        echo_output=True,
    )
    _run_checked(
        runner,
        [
            str(python),
            "src/merge_localize_po.py",
            "--repo-root",
            str(repo_root),
            "--config",
            config_path.as_posix(),
            "--km-version",
            version,
        ],
        cwd=tooling_repo,
        description=f"merge Localize PO for KM {version}",
        echo_output=True,
    )
    _run_checked(
        runner,
        [
            str(python),
            "src/po_to_km.py",
            "--translated-po",
            str(repo_root / paths.final_po_path),
            "--original-km",
            str(repo_root / paths.source_km_path),
            "--out-km",
            str(repo_root / paths.final_km_path),
            "--source-lang",
            config.translation.source_language,
            "--target-lang",
            config.translation.target_language,
            "--output-organization-id",
            config.translation.translated_organization_id,
            "--output-km-id",
            config.translation.translated_km_id,
            "--output-name",
            config.translation.translated_name,
        ],
        cwd=tooling_repo,
        description=f"build translated KM for KM {version}",
        echo_output=True,
    )
    _run_checked(
        runner,
        [str(python), "-m", "pytest", "tests/translation"],
        cwd=tooling_repo,
        env={"DSW_COLLAB_OUTPUT_ROOT": str(repo_root)},
        description=f"run translation tests for KM {version}",
        echo_output=True,
    )


def _commit_and_push(
    *,
    repo_root: Path,
    branch: str,
    message: str,
    runner: CommandRunner,
) -> None:
    _configure_git_identity(repo_root, runner)
    _run_checked(
        runner,
        ["git", "add", "-A", "--", "."],
        cwd=repo_root,
        description="stage repository changes",
    )
    status = _run_checked(
        runner,
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        description="inspect repository changes",
    )
    if not status.stdout.strip():
        return
    _run_checked(
        runner,
        ["git", "commit", "-m", message],
        cwd=repo_root,
        description="create latest-KM sync commit",
    )
    _run_checked(
        runner,
        ["git", "push", "origin", f"HEAD:{branch}"],
        cwd=repo_root,
        description=f"push latest-KM sync commit to {branch}",
    )


def _ensure_git_repo_is_clean(repo_root: Path, runner: CommandRunner) -> None:
    status = _run_checked(
        runner,
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        description="inspect repository cleanliness",
    )
    if status.stdout.strip():
        raise KmLatestSyncError("Repository has uncommitted changes; refusing latest-KM sync")


def _git_current_branch(repo_root: Path, runner: CommandRunner) -> str:
    result = _run_checked(
        runner,
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        description="read current branch",
    )
    branch = result.stdout.strip()
    if not branch:
        raise KmLatestSyncError("Cannot sync latest KM from a detached HEAD")
    return branch


def _configure_git_identity(repo_root: Path, runner: CommandRunner) -> None:
    _run_checked(
        runner,
        ["git", "config", "user.name", GITHUB_BOT_NAME],
        cwd=repo_root,
        description="configure git bot name",
    )
    _run_checked(
        runner,
        ["git", "config", "user.email", GITHUB_BOT_EMAIL],
        cwd=repo_root,
        description="configure git bot email",
    )


def _run_checked(
    runner: CommandRunner,
    args: Sequence[str],
    *,
    cwd: Path,
    description: str,
    env: Mapping[str, str] | None = None,
    echo_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    result = runner(args, cwd=cwd, env=env)
    if echo_output:
        _print_process_output(result)
    if result.returncode == 0:
        return result
    output = (result.stderr or result.stdout or "").strip()
    raise KmLatestSyncError(f"Failed to {description}: {output}")


def _print_process_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")


def _resolve_repo_path(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _tooling_python(tooling_repo: Path) -> Path:
    return tooling_repo / ".venv" / "bin" / "python"
