"""Automation for promoting discovered KM versions into translation branches."""

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
from .km_registry import discover_km_versions
from .localize_sync import pull_localize_po
from .translation_repository_config import (
    TranslationRepositoryConfig,
    TranslationRepositoryConfigError,
    load_translation_repository_config,
    sorted_versions,
    validate_supported_version,
    version_paths,
)


class CommandRunner(Protocol):
    """Protocol for command execution used by version-promotion automation."""

    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run one command and return its result."""


class KmVersionPromotionError(RuntimeError):
    """Raised when automatic KM version promotion cannot complete."""


@dataclass(frozen=True)
class VersionPromotionPlan:
    """Describe how one discovered KM version should be promoted."""

    version: str
    base_version: str
    branch: str
    base_branch: str


@dataclass(frozen=True)
class KmVersionPromotionResult:
    """Summary of one promotion run."""

    plans: tuple[VersionPromotionPlan, ...]
    promoted_versions: tuple[str, ...]
    skipped_reason: str | None = None
    dry_run: bool = False


def promote_new_km_versions(
    *,
    repo_root: Path,
    tooling_repo: Path,
    config_path: Path,
    registry_token: str,
    skip_without_token: bool = False,
    dry_run: bool = False,
    max_new_versions: int | None = None,
    runner: CommandRunner | None = None,
) -> KmVersionPromotionResult:
    """Promote newly discovered KM versions into version branches."""

    host_repo = repo_root.resolve()
    tooling_root = tooling_repo.resolve()
    resolved_config_path = _resolve_repo_path(host_repo, config_path)
    repository_config = load_translation_repository_config(resolved_config_path)
    discovery = discover_km_versions(config_path=resolved_config_path)
    new_versions = discovery.new_versions
    if max_new_versions is not None:
        new_versions = new_versions[:max_new_versions]
    plans = tuple(plan_version_promotions(repository_config, new_versions))
    if not plans:
        return KmVersionPromotionResult(plans=(), promoted_versions=(), dry_run=dry_run)
    if not registry_token.strip():
        if skip_without_token:
            return KmVersionPromotionResult(
                plans=plans,
                promoted_versions=(),
                skipped_reason="missing-registry-token",
                dry_run=dry_run,
            )
        raise KmVersionPromotionError(
            "Discovered new KM versions, but no DSW Registry token was provided."
        )
    if dry_run:
        return KmVersionPromotionResult(plans=plans, promoted_versions=(), dry_run=True)

    run = runner or default_command_runner
    _ensure_git_repo_is_clean(host_repo, run)
    current_branch = _git_current_branch(host_repo, run)
    all_new_versions = tuple(plan.version for plan in plans)
    update_supported_versions_in_config(resolved_config_path, all_new_versions)
    updated_config_text = resolved_config_path.read_text(encoding="utf-8")
    _commit_and_push_current_branch(
        repo_root=host_repo,
        branch=current_branch,
        message="chore: add discovered KM version support",
        runner=run,
    )

    promoted_versions: list[str] = []
    for plan in plans:
        _promote_one_version(
            repo_root=host_repo,
            tooling_repo=tooling_root,
            config_path=config_path,
            version=plan.version,
            branch=plan.branch,
            base_branch=plan.base_branch,
            operations_config_text=updated_config_text,
            registry_token=registry_token,
            runner=run,
        )
        promoted_versions.append(plan.version)
        _checkout_branch(host_repo, current_branch, run)

    return KmVersionPromotionResult(
        plans=plans,
        promoted_versions=tuple(promoted_versions),
        dry_run=False,
    )


def plan_version_promotions(
    config: TranslationRepositoryConfig,
    new_versions: Sequence[str],
) -> tuple[VersionPromotionPlan, ...]:
    """Build promotion plans for newly discovered versions."""

    supported_versions = list(config.knowledge_model.supported_versions)
    plans: list[VersionPromotionPlan] = []
    for version in sorted_versions(tuple(new_versions)):
        if not supported_versions:
            raise KmVersionPromotionError("At least one configured base version is required")
        base_version = supported_versions[-1]
        branch = f"{config.branches.version_branch_prefix}{version}"
        base_branch = f"{config.branches.version_branch_prefix}{base_version}"
        plans.append(
            VersionPromotionPlan(
                version=version,
                base_version=base_version,
                branch=branch,
                base_branch=base_branch,
            )
        )
        supported_versions.append(version)
    return tuple(plans)


def update_supported_versions_in_config(
    config_path: Path, versions: Sequence[str]
) -> tuple[str, ...]:
    """Add versions to ``knowledge_model.supported_versions`` in-place."""

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


def _promote_one_version(
    *,
    repo_root: Path,
    tooling_repo: Path,
    config_path: Path,
    version: str,
    branch: str,
    base_branch: str,
    operations_config_text: str,
    registry_token: str,
    runner: CommandRunner,
) -> None:
    _run_checked(
        runner,
        ["git", "fetch", "origin", f"{base_branch}:refs/remotes/origin/{base_branch}"],
        cwd=repo_root,
        description=f"fetch base branch {base_branch}",
    )
    _run_checked(
        runner,
        ["git", "checkout", "-B", branch, f"origin/{base_branch}"],
        cwd=repo_root,
        description=f"create version branch {branch}",
    )
    _write_text(_resolve_repo_path(repo_root, config_path), operations_config_text)
    repository_config = load_translation_repository_config(
        _resolve_repo_path(repo_root, config_path)
    )
    validate_supported_version(repository_config, version)

    pull_km_bundle(
        config_path=_resolve_repo_path(repo_root, config_path),
        repo_root=repo_root,
        token=registry_token,
        km_version=version,
    )
    pull_localize_po(
        config_path=_resolve_repo_path(repo_root, config_path),
        repo_root=repo_root,
        km_version=version,
    )
    _run_export_tree(
        repo_root=repo_root,
        tooling_repo=tooling_repo,
        config=repository_config,
        version=version,
        runner=runner,
    )
    _run_sync_merge_build_and_tests(
        repo_root=repo_root,
        tooling_repo=tooling_repo,
        config_path=config_path,
        version=version,
        runner=runner,
    )
    _commit_and_push_current_branch(
        repo_root=repo_root,
        branch=branch,
        message=f"chore(scaffold): initialize KM {version} translation branch",
        runner=runner,
    )


def _run_export_tree(
    *,
    repo_root: Path,
    tooling_repo: Path,
    config: TranslationRepositoryConfig,
    version: str,
    runner: CommandRunner,
) -> None:
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
    repository_config = load_translation_repository_config(
        _resolve_repo_path(repo_root, config_path)
    )
    paths = version_paths(repository_config, version)
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
            repository_config.translation.source_language,
            "--target-lang",
            repository_config.translation.target_language,
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
            repository_config.translation.source_language,
            "--target-lang",
            repository_config.translation.target_language,
            "--output-organization-id",
            repository_config.translation.translated_organization_id,
            "--output-km-id",
            repository_config.translation.translated_km_id,
            "--output-name",
            repository_config.translation.translated_name,
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


def _commit_and_push_current_branch(
    *,
    repo_root: Path,
    branch: str,
    message: str,
    runner: CommandRunner,
) -> bool:
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
        _run_checked(
            runner,
            ["git", "push", "origin", f"HEAD:{branch}"],
            cwd=repo_root,
            description=f"push existing branch {branch}",
        )
        return False
    _run_checked(
        runner,
        ["git", "commit", "-m", message],
        cwd=repo_root,
        description="create promotion commit",
    )
    _run_checked(
        runner,
        ["git", "push", "origin", f"HEAD:{branch}"],
        cwd=repo_root,
        description=f"push branch {branch}",
    )
    return True


def _ensure_git_repo_is_clean(repo_root: Path, runner: CommandRunner) -> None:
    status = _run_checked(
        runner,
        ["git", "status", "--porcelain"],
        cwd=repo_root,
        description="inspect repository cleanliness",
    )
    if status.stdout.strip():
        raise KmVersionPromotionError("Repository has uncommitted changes; refusing promotion")


def _git_current_branch(repo_root: Path, runner: CommandRunner) -> str:
    result = _run_checked(
        runner,
        ["git", "branch", "--show-current"],
        cwd=repo_root,
        description="read current branch",
    )
    branch = result.stdout.strip()
    if not branch:
        raise KmVersionPromotionError("Cannot promote versions from a detached HEAD")
    return branch


def _checkout_branch(repo_root: Path, branch: str, runner: CommandRunner) -> None:
    _run_checked(
        runner,
        ["git", "checkout", branch],
        cwd=repo_root,
        description=f"return to branch {branch}",
    )


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
    raise KmVersionPromotionError(f"Failed to {description}: {output}")


def _print_process_output(result: subprocess.CompletedProcess[str]) -> None:
    if result.stdout:
        print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
    if result.stderr:
        print(result.stderr, end="" if result.stderr.endswith("\n") else "\n")


def _resolve_repo_path(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _write_text(destination: Path, text: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")


def _tooling_python(tooling_repo: Path) -> Path:
    return tooling_repo / ".venv" / "bin" / "python"
