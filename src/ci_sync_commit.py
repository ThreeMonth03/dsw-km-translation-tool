#!/usr/bin/env python3
"""Run CI sync, translation validation, and optional auto-commit."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_translation_tool import DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG
from dsw_translation_tool.ci_sync import (
    DEFAULT_SYNC_COMMIT_MESSAGE,
    CiSyncCommitConfig,
    CiSyncError,
    run_ci_sync_commit,
)
from dsw_translation_tool.versioned_ci_sync import build_versioned_ci_sync_config


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser for CI sync automation.

    Returns:
        Configured parser instance.
    """

    parser = argparse.ArgumentParser(
        description=(
            "Run shared-string sync plus translation validation, then create "
            "and push a commit when tracked translation artifacts changed."
        ),
    )
    parser.add_argument("--host-repo", required=True, help="Host repository checkout path.")
    parser.add_argument(
        "--tooling-repo",
        required=True,
        help="Tooling repository checkout path that contains the sync CLI and tests.",
    )
    parser.add_argument(
        "--translation-root",
        default=None,
        help=(
            "Relative path inside the host repository that contains tree/, builds/, "
            "and reviews/. Defaults to '.' when --config is used."
        ),
    )
    parser.add_argument(
        "--target-ref",
        default=None,
        help=(
            "Branch/ref that should receive the pushed sync commit. Defaults to "
            "the configured tracking branch when --config is used."
        ),
    )
    parser.add_argument(
        "--mode",
        choices=("schedule", "pull_request"),
        required=True,
        help="Trigger mode for the current CI run.",
    )
    parser.add_argument("--source-lang", default=None)
    parser.add_argument("--target-lang", default=None)
    parser.add_argument("--commit-message", default=DEFAULT_SYNC_COMMIT_MESSAGE)
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Path to translation-config.yml. Relative paths are resolved inside "
            "the host repository."
        ),
    )
    parser.add_argument(
        "--km-version",
        default=None,
        help="KM version to sync when --config is used. Defaults to the latest configured version.",
    )
    parser.add_argument(
        "--original-po",
        default=None,
        help=(
            "Source PO template path. Relative paths are resolved inside the host "
            "repository. Defaults to the canonical tooling PO."
        ),
    )
    parser.add_argument(
        "--original-km",
        default=None,
        help=(
            "Source KM bundle path. Relative paths are resolved inside the host "
            "repository. Defaults to the canonical tooling KM."
        ),
    )
    parser.add_argument(
        "--output-organization-id",
        default=None,
        help="Organization ID for the generated translated KM.",
    )
    parser.add_argument(
        "--output-km-id",
        default=None,
        help="KM ID for the generated translated KM.",
    )
    parser.add_argument(
        "--output-name",
        default=None,
        help="Display name for the generated translated KM.",
    )
    parser.add_argument(
        "--restore-source-ref",
        default=None,
        help=(
            "Git ref used when restoring a malformed translation source file during "
            "CI recovery. Defaults to origin/master, or origin/<tracking branch> "
            "when --config is used."
        ),
    )
    return parser


def main() -> None:
    """Run the CI sync-and-commit CLI."""

    parser = build_argument_parser()
    args = parser.parse_args()
    source_po_path = Path(args.original_po) if args.original_po else None
    source_km_path = Path(args.original_km) if args.original_km else None
    if args.config:
        config = build_versioned_ci_sync_config(
            host_repo_path=Path(args.host_repo),
            tooling_repo_path=Path(args.tooling_repo),
            config_path=Path(args.config),
            mode=args.mode,
            km_version=args.km_version,
            translation_root=args.translation_root,
            target_ref=args.target_ref,
            source_lang=args.source_lang,
            target_lang=args.target_lang,
            commit_message=args.commit_message,
            source_po_path=source_po_path,
            source_km_path=source_km_path,
            output_organization_id=args.output_organization_id,
            output_km_id=args.output_km_id,
            output_name=args.output_name,
            restore_source_ref=args.restore_source_ref,
        )
    else:
        if not args.translation_root:
            parser.error("--translation-root is required when --config is not used")
        if not args.target_ref:
            parser.error("--target-ref is required when --config is not used")
        config = CiSyncCommitConfig(
            host_repo_path=Path(args.host_repo),
            tooling_repo_path=Path(args.tooling_repo),
            translation_root=args.translation_root,
            target_ref=args.target_ref,
            mode=args.mode,
            source_lang=args.source_lang or DEFAULT_SOURCE_LANG,
            target_lang=args.target_lang or DEFAULT_TARGET_LANG,
            commit_message=args.commit_message,
            source_po_path=source_po_path,
            source_km_path=source_km_path,
            output_organization_id=args.output_organization_id,
            output_km_id=args.output_km_id,
            output_name=args.output_name,
            restore_source_ref=args.restore_source_ref or "origin/master",
        )
    try:
        committed = run_ci_sync_commit(config)
    except CiSyncError as error:
        raise SystemExit(str(error)) from error

    if committed:
        print("[ci-sync] Sync changes were committed and pushed.")
        return
    print("[ci-sync] Sync completed without tracked translation changes.")


if __name__ == "__main__":
    main()
