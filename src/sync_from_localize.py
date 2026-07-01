#!/usr/bin/env python3
"""Mirror the current Localize/Weblate translation into a Git repository."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_translation_tool.ci_sync import (
    DEFAULT_SYNC_COMMIT_MESSAGE,
    CiSyncError,
    run_ci_sync_commit,
)
from dsw_translation_tool.localize_sync import pull_localize_po
from dsw_translation_tool.localize_tree_sync import refresh_tree_from_localize
from dsw_translation_tool.versioned_ci_sync import build_versioned_ci_sync_config


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for Localize-to-Git sync."""

    parser = argparse.ArgumentParser(
        description=(
            "Pull the current Localize/Weblate PO snapshot, rebuild translation "
            "artifacts, and push a Git sync commit when artifacts changed."
        ),
    )
    parser.add_argument("--host-repo", required=True, help="Translation repository checkout path.")
    parser.add_argument(
        "--tooling-repo",
        required=True,
        help="Tooling repository checkout path that contains this script and tests.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml, relative to --host-repo unless absolute.",
    )
    parser.add_argument(
        "--translation-root",
        default=".",
        help="Relative path inside --host-repo containing tree/, builds/, and reviews/.",
    )
    parser.add_argument(
        "--target-ref",
        default=None,
        help="Git branch/ref that should receive the sync commit. Defaults to tracking_branch.",
    )
    parser.add_argument(
        "--restore-source-ref",
        default=None,
        help="Git ref used for CI recovery restores. Defaults to origin/<tracking_branch>.",
    )
    parser.add_argument(
        "--mode",
        choices=("schedule", "pull_request"),
        required=True,
        help="Current automation mode. Pull requests push sync commits to the PR branch.",
    )
    parser.add_argument(
        "--km-version",
        default=None,
        help="KM version to sync. Defaults to the latest configured version.",
    )
    parser.add_argument(
        "--commit-message",
        default=DEFAULT_SYNC_COMMIT_MESSAGE,
        help="Commit message for generated Localize-to-Git sync commits.",
    )
    return parser


def main() -> None:
    """Run Localize-to-Git sync automation."""

    args = build_argument_parser().parse_args()
    host_repo = Path(args.host_repo).resolve()
    tooling_repo = Path(args.tooling_repo).resolve()
    config_path = Path(args.config)

    pull_result = pull_localize_po(
        config_path=_resolve_host_path(host_repo, config_path),
        repo_root=host_repo,
        km_version=args.km_version,
    )
    print("Localize PO pull")
    print(f"  Version         : {pull_result.version}")
    print(f"  Changed         : {pull_result.changed}")
    print(f"  Latest PO       : {pull_result.latest_po_path}")

    sync_config = build_versioned_ci_sync_config(
        host_repo_path=host_repo,
        tooling_repo_path=tooling_repo,
        config_path=config_path,
        mode=args.mode,
        km_version=args.km_version,
        translation_root=args.translation_root,
        target_ref=args.target_ref,
        commit_message=args.commit_message,
        restore_source_ref=args.restore_source_ref,
    )
    refresh_result = refresh_tree_from_localize(
        config=sync_config,
        km_version=pull_result.version,
    )
    print("Localize tree refresh")
    print(f"  Version         : {refresh_result.version}")
    print(f"  Tree            : {refresh_result.tree_dir}")
    print(f"  Folders         : {refresh_result.folder_count}")
    print(f"  Root folders    : {refresh_result.root_count}")
    print(f"  Shared blocks   : {refresh_result.shared_block_file_count}")

    try:
        committed = run_ci_sync_commit(sync_config)
    except CiSyncError as error:
        raise SystemExit(str(error)) from error

    if committed:
        print("[localize-sync] Localize changes were committed and pushed to Git.")
        return
    print("[localize-sync] Localize and Git translation artifacts are already aligned.")


def _resolve_host_path(host_repo: Path, path: Path) -> Path:
    """Resolve a path against the host repository when it is relative."""

    if path.is_absolute():
        return path.resolve()
    return (host_repo / path).resolve()


if __name__ == "__main__":
    main()
