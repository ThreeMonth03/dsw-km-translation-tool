"""CI helpers for syncing translation artifacts and committing updates."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .constants import SHARED_BLOCK_CONTEXT_FILENAME, TRANSLATION_FILENAME
from .layout import (
    DEFAULT_MODEL_PATH,
    DEFAULT_PO_PATH,
    DEFAULT_SOURCE_LANG,
    DEFAULT_TARGET_LANG,
    TranslationOutputLayout,
)
from .localize_merge import LocalizePoMerger

DEFAULT_SYNC_COMMIT_MESSAGE = "chore(sync): refresh translation artifacts"
GITHUB_BOT_NAME = "github-actions[bot]"
GITHUB_BOT_EMAIL = "41898282+github-actions[bot]@users.noreply.github.com"
RESTORABLE_SYNC_FILENAMES = frozenset(
    {
        TRANSLATION_FILENAME,
        SHARED_BLOCK_CONTEXT_FILENAME,
    }
)
SYNC_FILE_LINE_RE = re.compile(r"^File: (?P<path>.+)$", re.MULTILINE)


class CommandRunner(Protocol):
    """Protocol for subprocess execution used by the CI sync helper."""

    def __call__(
        self,
        args: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str] | None = None,
    ) -> subprocess.CompletedProcess[str]:
        """Run one command and return the completed-process result.

        Args:
            args: Command argument vector.
            cwd: Working directory for the command.
            env: Optional environment overrides.

        Returns:
            Completed process result.
        """


class CiSyncError(RuntimeError):
    """Raised when CI sync-and-commit automation cannot complete."""


@dataclass(frozen=True)
class CiSyncCommitConfig:
    """Describe one CI sync-and-commit operation.

    Args:
        host_repo_path: Repository whose translation tree should be updated.
        tooling_repo_path: Repository that contains the sync CLI and tests.
        translation_root: Relative path inside the host repository that contains
            `tree/`, `builds/`, and `reviews/`.
        target_ref: Branch/ref that should receive the push.
        mode: Trigger mode, either `schedule` or `pull_request`.
        source_lang: Source language code used by the sync CLI.
        target_lang: Target language code used by the sync CLI.
        commit_message: Commit message used when sync changes are detected.
        source_po_path: Optional source PO template path. Relative paths are
            resolved inside the host repository; absolute paths are used as-is.
            Defaults to the canonical PO bundled in the tooling repository.
        source_km_path: Optional source KM bundle path. Relative paths are
            resolved inside the host repository; absolute paths are used as-is.
            Defaults to the canonical KM bundled in the tooling repository.
        output_organization_id: Optional organization ID for the generated KM.
        output_km_id: Optional KM ID for the generated KM.
        output_name: Optional display name for the generated KM.
        restore_source_ref: Git ref used when restoring a malformed
            translation source file during CI recovery.
        localize_base_po_path: Optional Localize base PO snapshot used to enable
            conservative three-way merge before generating the KM.
        localize_merge_report_path: Optional JSON report path for Localize merge
            decisions. Relative paths are resolved inside the host repository.
        protected_chapters: Chapter numeric prefixes that should keep repo
            translations during Localize merges.
        localize_conflict_policy: Conflict policy passed to the Localize merge.
            Use ``latest-wins`` when Weblate is the source of truth.
    """

    host_repo_path: Path
    tooling_repo_path: Path
    translation_root: str
    target_ref: str
    mode: str
    source_lang: str = DEFAULT_SOURCE_LANG
    target_lang: str = DEFAULT_TARGET_LANG
    commit_message: str = DEFAULT_SYNC_COMMIT_MESSAGE
    source_po_path: Path | None = None
    source_km_path: Path | None = None
    output_organization_id: str | None = None
    output_km_id: str | None = None
    output_name: str | None = None
    restore_source_ref: str = "origin/master"
    localize_base_po_path: Path | None = None
    localize_merge_report_path: Path | None = None
    protected_chapters: tuple[str, ...] = ()
    localize_conflict_policy: str = "conservative"

    @property
    def host_repo_dir(self) -> Path:
        """Return the absolute host repository path."""

        return self.host_repo_path.resolve()

    @property
    def tooling_repo_dir(self) -> Path:
        """Return the absolute tooling repository path."""

        return self.tooling_repo_path.resolve()

    @property
    def translation_root_path(self) -> Path:
        """Return the translation root as a relative path object."""

        return Path(self.translation_root)

    @property
    def translation_root_arg(self) -> str:
        """Return the normalized pathspec used by git commands."""

        normalized = self.translation_root_path.as_posix()
        return normalized or "."

    @property
    def translation_root_dir(self) -> Path:
        """Return the absolute translation root inside the host repository."""

        return (self.host_repo_dir / self.translation_root_path).resolve()

    @property
    def output_layout(self) -> TranslationOutputLayout:
        """Return the shared artifact layout rooted in the host repository."""

        return TranslationOutputLayout(
            output_root=self.translation_root_dir,
            target_lang=self.target_lang,
        )

    @property
    def tree_dir(self) -> Path:
        """Return the absolute translation tree directory."""

        return self.output_layout.tree_dir

    @property
    def final_po_path(self) -> Path:
        """Return the generated PO output path."""

        return self.output_layout.final_po_path

    @property
    def final_km_path(self) -> Path:
        """Return the generated translated KM output path."""

        return self.output_layout.final_km_path

    @property
    def final_km_git_path(self) -> str:
        """Return the generated KM path relative to the host repo."""

        return self.final_km_path.relative_to(self.host_repo_dir).as_posix()

    @property
    def diff_path(self) -> Path:
        """Return the generated review diff path."""

        return self.output_layout.diff_path

    @property
    def outline_path(self) -> Path:
        """Return the generated outline markdown path."""

        return self.output_layout.outline_path

    @property
    def shared_blocks_dir(self) -> Path:
        """Return the canonical split shared-block directory root."""

        return self.output_layout.shared_blocks_dir

    @property
    def shared_blocks_outline_path(self) -> Path:
        """Return the compact shared-block outline markdown path."""

        return self.output_layout.shared_blocks_outline_path

    @property
    def tooling_python_path(self) -> Path:
        """Return the tooling virtualenv Python path."""

        return self.tooling_repo_dir / ".venv" / "bin" / "python"

    @property
    def original_po_path(self) -> Path:
        """Return the source PO template path for sync and validation."""

        return self._resolve_source_path(
            configured_path=self.source_po_path,
            default_path=self.tooling_repo_dir / DEFAULT_PO_PATH,
        )

    @property
    def localize_base_path(self) -> Path | None:
        """Return the optional Localize base PO snapshot path."""

        if self.localize_base_po_path is None:
            return None
        return self._resolve_source_path(
            configured_path=self.localize_base_po_path,
            default_path=self.localize_base_po_path,
        )

    @property
    def localize_merge_report_file(self) -> Path | None:
        """Return the optional Localize merge report path."""

        if self.localize_merge_report_path is None:
            return None
        if self.localize_merge_report_path.is_absolute():
            return self.localize_merge_report_path.resolve()
        return (self.host_repo_dir / self.localize_merge_report_path).resolve()

    @property
    def original_model_path(self) -> Path:
        """Return the source KM bundle path for building translated KM output."""

        return self._resolve_source_path(
            configured_path=self.source_km_path,
            default_path=self.tooling_repo_dir / DEFAULT_MODEL_PATH,
        )

    def _resolve_source_path(self, configured_path: Path | None, default_path: Path) -> Path:
        """Resolve one optional source path for CI automation.

        Args:
            configured_path: User-provided source path, or ``None``.
            default_path: Fallback path used by legacy single-version repos.

        Returns:
            Absolute path to the source file.
        """

        if configured_path is None:
            return default_path.resolve()
        if configured_path.is_absolute():
            return configured_path.resolve()
        return (self.host_repo_dir / configured_path).resolve()

    def validate(self) -> None:
        """Validate that the requested sync operation can run locally.

        Raises:
            CiSyncError: If the configuration points to missing or unsupported
                paths.
        """

        if self.mode not in {"schedule", "pull_request"}:
            raise CiSyncError(
                "Unsupported CI sync mode. Expected 'schedule' or "
                f"'pull_request', got {self.mode!r}."
            )
        if self.translation_root_path.is_absolute():
            raise CiSyncError("Translation root must be relative to the host repository.")
        if not self.host_repo_dir.is_dir():
            raise CiSyncError(f"Host repository does not exist: {self.host_repo_dir}")
        if not self.tooling_repo_dir.is_dir():
            raise CiSyncError(f"Tooling repository does not exist: {self.tooling_repo_dir}")
        if not self.translation_root_dir.is_dir():
            raise CiSyncError(
                "Translation root does not exist inside the host repository: "
                f"{self.translation_root_dir}"
            )
        if not self.tree_dir.is_dir():
            raise CiSyncError(f"Missing translation tree directory: {self.tree_dir}")
        if not self.tooling_python_path.exists():
            raise CiSyncError(
                "Missing tooling virtualenv Python. Run `make install-dev` first: "
                f"{self.tooling_python_path}"
            )
        if not self.restore_source_ref.strip():
            raise CiSyncError("Restore source ref must not be empty.")
        if not self.original_po_path.exists():
            raise CiSyncError(f"Missing original PO file: {self.original_po_path}")
        if not self.original_model_path.exists():
            raise CiSyncError(f"Missing original KM file: {self.original_model_path}")
        if self.localize_base_path is not None and not self.localize_base_path.exists():
            raise CiSyncError(f"Missing Localize base PO file: {self.localize_base_path}")
        if (self.localize_base_path is None) != (self.localize_merge_report_file is None):
            raise CiSyncError(
                "Localize merge requires both localize_base_po_path and localize_merge_report_path."
            )
        if self.localize_conflict_policy not in {"conservative", "latest-wins"}:
            raise CiSyncError(
                "Localize conflict policy must be either 'conservative' or 'latest-wins'."
            )


def default_command_runner(
    args: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run one subprocess command for CI sync orchestration.

    Args:
        args: Command argument vector.
        cwd: Working directory for the command.
        env: Optional environment overrides.

    Returns:
        Completed process result.
    """

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


def run_ci_sync_commit(
    config: CiSyncCommitConfig,
    *,
    runner: CommandRunner = default_command_runner,
) -> bool:
    """Run sync, translation validation, and optional commit/push.

    Args:
        config: Sync-and-commit configuration.
        runner: Injectable subprocess runner used by tests and production code.

    Returns:
        `True` when a commit was created and pushed, otherwise `False`.

    Raises:
        CiSyncError: If sync, validation, commit, or push fails.
    """

    config.validate()
    print(f"[ci-sync] Mode: {config.mode}")
    print(f"[ci-sync] Host repo: {config.host_repo_dir}")
    print(f"[ci-sync] Translation root: {config.translation_root_arg}")

    _run_sync_with_origin_restore(config, runner)
    _run_localize_merge(config)
    _run_checked(
        runner,
        _build_po_to_km_command(config),
        cwd=config.tooling_repo_dir,
        description="build translated KM artifact",
        echo_output=True,
    )
    _run_checked(
        runner,
        _build_translation_test_command(config),
        cwd=config.tooling_repo_dir,
        env={
            "DSW_COLLAB_OUTPUT_ROOT": str(config.translation_root_dir),
            "DSW_SOURCE_PO_PATH": str(config.original_po_path),
            "DSW_SOURCE_KM_PATH": str(config.original_model_path),
        },
        description="run translation tests",
        echo_output=True,
    )

    _mark_generated_km_as_intent_to_add(config, runner)
    if not _translation_root_has_tracked_changes(config, runner):
        print("[ci-sync] No tracked translation changes detected after sync.")
        return False

    _configure_git_identity(config, runner)
    _run_checked(
        runner,
        ["git", "add", "--", config.translation_root_arg],
        cwd=config.host_repo_dir,
        description="stage translation changes",
    )
    _run_checked(
        runner,
        ["git", "commit", "-m", config.commit_message],
        cwd=config.host_repo_dir,
        description="create sync commit",
    )
    _run_checked(
        runner,
        ["git", "push", "origin", f"HEAD:{config.target_ref}"],
        cwd=config.host_repo_dir,
        description="push sync commit",
    )
    print(f"[ci-sync] Pushed sync commit to {config.target_ref}.")
    return True


def _run_localize_merge(config: CiSyncCommitConfig) -> None:
    """Run optional Localize PO merge after rebuilding the repo PO."""

    base_po_path = config.localize_base_path
    merge_report_path = config.localize_merge_report_file
    if base_po_path is None or merge_report_path is None:
        return
    result = LocalizePoMerger().merge(
        base_po_path=base_po_path,
        latest_po_path=config.original_po_path,
        repo_po_path=config.final_po_path,
        out_po_path=config.final_po_path,
        report_path=merge_report_path,
        tree_dir=config.tree_dir,
        protected_chapters=config.protected_chapters,
        conflict_policy=config.localize_conflict_policy,
    )
    print("[ci-sync] Localize merge")
    print(f"[ci-sync]   Conflict policy: {config.localize_conflict_policy}")
    print(f"[ci-sync]   Accepted latest: {result.accepted_latest}")
    print(f"[ci-sync]   Conflicts: {result.conflicts}")
    print(f"[ci-sync]   Protected skips: {result.protected_skips}")


def _run_sync_with_origin_restore(
    config: CiSyncCommitConfig,
    runner: CommandRunner,
) -> None:
    """Run sync once, optionally restoring one broken source file from a git ref.

    Args:
        config: Sync-and-commit configuration.
        runner: Injectable subprocess runner.

    Raises:
        CiSyncError: If sync still fails after the restore attempt or if the
            failure is not eligible for aggressive restore.
    """

    try:
        _run_checked(
            runner,
            _build_sync_command(config),
            cwd=config.tooling_repo_dir,
            description="sync translation artifacts",
            echo_output=True,
        )
        return
    except CiSyncError as error:
        restore_path = _extract_origin_restore_candidate(str(error), config)
        if restore_path is None:
            raise

    print(
        "[ci-sync] WARNING: restoring malformed translation source from "
        f"{config.restore_source_ref}: {restore_path}"
    )
    _restore_file_from_configured_source(config, runner, restore_path)
    _run_checked(
        runner,
        _build_sync_command(config),
        cwd=config.tooling_repo_dir,
        description="re-run sync translation artifacts after git restore",
        echo_output=True,
    )


def _build_sync_command(config: CiSyncCommitConfig) -> list[str]:
    """Build the explicit sync CLI command for one CI operation.

    Args:
        config: Sync-and-commit configuration.

    Returns:
        Command argument vector.
    """

    return [
        str(config.tooling_python_path),
        "src/sync_shared_strings.py",
        "--tree-dir",
        str(config.tree_dir),
        "--original-po",
        str(config.original_po_path),
        "--out-po",
        str(config.final_po_path),
        "--diff-out",
        str(config.diff_path),
        "--outline-out",
        str(config.outline_path),
        "--shared-blocks-dir-out",
        str(config.shared_blocks_dir),
        "--shared-blocks-outline-out",
        str(config.shared_blocks_outline_path),
        "--source-lang",
        config.source_lang,
        "--target-lang",
        config.target_lang,
        "--group-by",
        "shared-block",
    ]


def _build_po_to_km_command(config: CiSyncCommitConfig) -> list[str]:
    """Build the explicit PO-to-KM CLI command for one CI operation.

    Args:
        config: Sync-and-commit configuration.

    Returns:
        Command argument vector.
    """

    return [
        str(config.tooling_python_path),
        "src/po_to_km.py",
        "--translated-po",
        str(config.final_po_path),
        "--original-km",
        str(config.original_model_path),
        "--out-km",
        str(config.final_km_path),
        "--source-lang",
        config.source_lang,
        "--target-lang",
        config.target_lang,
    ] + _build_optional_po_to_km_identity_args(config)


def _build_optional_po_to_km_identity_args(config: CiSyncCommitConfig) -> list[str]:
    """Build optional translated-KM identity flags.

    Args:
        config: Sync-and-commit configuration.

    Returns:
        Command-line flags for identity overrides.
    """

    args: list[str] = []
    if config.output_organization_id:
        args.extend(["--output-organization-id", config.output_organization_id])
    if config.output_km_id:
        args.extend(["--output-km-id", config.output_km_id])
    if config.output_name:
        args.extend(["--output-name", config.output_name])
    return args


def _build_translation_test_command(config: CiSyncCommitConfig) -> list[str]:
    """Build the explicit translation-test command for one CI operation.

    Args:
        config: Sync-and-commit configuration.

    Returns:
        Command argument vector.
    """

    return [
        str(config.tooling_python_path),
        "-m",
        "pytest",
        "tests/translation",
    ]


def _mark_generated_km_as_intent_to_add(
    config: CiSyncCommitConfig,
    runner: CommandRunner,
) -> None:
    """Make a newly generated KM visible to tracked-only status checks.

    Args:
        config: Sync-and-commit configuration.
        runner: Injectable subprocess runner.
    """

    _run_checked(
        runner,
        ["git", "add", "-N", "--", config.final_km_git_path],
        cwd=config.host_repo_dir,
        description="mark generated KM artifact for change detection",
    )


def _translation_root_has_tracked_changes(
    config: CiSyncCommitConfig,
    runner: CommandRunner,
) -> bool:
    """Return whether tracked files changed under the translation root.

    Args:
        config: Sync-and-commit configuration.
        runner: Injectable subprocess runner.

    Returns:
        `True` when tracked files changed under the translation root.

    Raises:
        CiSyncError: If git status fails.
    """

    result = _run_checked(
        runner,
        ["git", "status", "--porcelain", "--untracked-files=no", "--", config.translation_root_arg],
        cwd=config.host_repo_dir,
        description="inspect tracked translation changes",
    )
    return bool(result.stdout.strip())


def _configure_git_identity(
    config: CiSyncCommitConfig,
    runner: CommandRunner,
) -> None:
    """Configure the GitHub Actions bot identity inside the host repository.

    Args:
        config: Sync-and-commit configuration.
        runner: Injectable subprocess runner.

    Raises:
        CiSyncError: If git config fails.
    """

    _run_checked(
        runner,
        ["git", "config", "user.name", GITHUB_BOT_NAME],
        cwd=config.host_repo_dir,
        description="configure git bot name",
    )
    _run_checked(
        runner,
        ["git", "config", "user.email", GITHUB_BOT_EMAIL],
        cwd=config.host_repo_dir,
        description="configure git bot email",
    )


def _extract_origin_restore_candidate(
    error_message: str,
    config: CiSyncCommitConfig,
) -> Path | None:
    """Return a restorable source file path from one sync failure message.

    Args:
        error_message: Raised sync failure message.
        config: Sync-and-commit configuration.

    Returns:
        Absolute path to a restorable source file, or `None` when the failure
        should not trigger aggressive restore.
    """

    for match in SYNC_FILE_LINE_RE.finditer(error_message):
        candidate_path = Path(match.group("path").strip()).resolve()
        if candidate_path.name not in RESTORABLE_SYNC_FILENAMES:
            continue
        if not _is_relative_to(candidate_path, config.host_repo_dir):
            continue
        if not _is_relative_to(candidate_path, config.translation_root_dir):
            continue
        if candidate_path.name == SHARED_BLOCK_CONTEXT_FILENAME and not _is_relative_to(
            candidate_path,
            config.shared_blocks_dir,
        ):
            continue
        return candidate_path
    return None


def _restore_file_from_configured_source(
    config: CiSyncCommitConfig,
    runner: CommandRunner,
    file_path: Path,
) -> None:
    """Restore one tracked translation source file from the configured git ref.

    Args:
        config: Sync-and-commit configuration.
        runner: Injectable subprocess runner.
        file_path: Absolute host-repository file path to restore.

    Raises:
        CiSyncError: If the git restore command fails.
    """

    relative_path = file_path.relative_to(config.host_repo_dir).as_posix()
    _run_checked(
        runner,
        [
            "git",
            "restore",
            "--source",
            config.restore_source_ref,
            "--worktree",
            "--",
            relative_path,
        ],
        cwd=config.host_repo_dir,
        description=f"restore {relative_path} from {config.restore_source_ref}",
    )


def _is_relative_to(path: Path, root: Path) -> bool:
    """Return whether one path is located under the given root.

    Args:
        path: Candidate absolute path.
        root: Candidate absolute root.

    Returns:
        `True` when `path` is inside `root`, otherwise `False`.
    """

    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _run_checked(
    runner: CommandRunner,
    args: Sequence[str],
    *,
    cwd: Path,
    description: str,
    env: Mapping[str, str] | None = None,
    echo_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run one command and raise a readable error on failure.

    Args:
        runner: Injectable subprocess runner.
        args: Command argument vector.
        cwd: Working directory for the command.
        description: Human-readable operation description.
        env: Optional environment overrides.
        echo_output: Whether stdout/stderr should be relayed to the current
            process output stream.

    Returns:
        Completed process result.

    Raises:
        CiSyncError: If the command exits with a non-zero status.
    """

    result = runner(args, cwd=cwd, env=env)
    if echo_output:
        _print_process_output(result)
    if result.returncode == 0:
        return result

    output = (result.stderr or result.stdout or "").strip()
    command = " ".join(str(part) for part in args)
    if output:
        raise CiSyncError(f"Failed to {description}: {command}\n{output}")
    raise CiSyncError(f"Failed to {description}: {command}")


def _print_process_output(result: subprocess.CompletedProcess[str]) -> None:
    """Relay captured subprocess output to the current stdout/stderr.

    Args:
        result: Completed process whose output should be printed.
    """

    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")
