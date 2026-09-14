#!/usr/bin/env python3
"""Keep the current translation branch synchronized with the latest KM."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dsw_km_translation_tool.km_latest_sync import (
    KmLatestSyncError,
    sync_latest_km_version,
    write_km_latest_sync_markdown,
    write_km_latest_sync_report,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Update the current translation branch when the Registry has a newer KM.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--tooling-repo", default=".")
    parser.add_argument("--config", default="translation-config.yml")
    parser.add_argument("--target-ref", default=None)
    parser.add_argument("--registry-token-env", default="DSW_REGISTRY_TOKEN")
    parser.add_argument("--skip-without-token", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--report",
        default=None,
        help="Optional JSON report path, for example $RUNNER_TEMP/km_auto_update.json.",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help="Optional Markdown summary path, for example $GITHUB_STEP_SUMMARY.",
    )
    parser.add_argument(
        "--details-out",
        default=None,
        help="Optional path to write a full Markdown report.",
    )
    return parser


def main() -> None:
    """Run latest-KM synchronization."""

    args = build_argument_parser().parse_args()
    token = os.environ.get(args.registry_token_env, "")
    try:
        result = sync_latest_km_version(
            repo_root=Path(args.repo_root),
            tooling_repo=Path(args.tooling_repo),
            config_path=Path(args.config),
            registry_token=token,
            target_ref=args.target_ref,
            skip_without_token=args.skip_without_token,
            dry_run=args.dry_run,
        )
    except KmLatestSyncError as error:
        raise SystemExit(f"Unable to sync latest KM: {error}") from error

    print(f"Configured KM version: {result.configured_version}")
    print(f"Registry KM version  : {result.registry_version or '(none)'}")
    print(f"Target ref           : {result.target_ref or '(none)'}")
    print(f"Status               : {result.status}")
    if args.report:
        write_km_latest_sync_report(result=result, report_path=Path(args.report))
        print(f"JSON report          : {args.report}")
    if args.summary:
        write_km_latest_sync_markdown(result=result, report_path=Path(args.summary))
    if args.details_out:
        write_km_latest_sync_markdown(result=result, report_path=Path(args.details_out))
        print(f"Markdown report      : {args.details_out}")
    if result.skipped_reason:
        print(f"Skipped latest-KM sync: {result.skipped_reason}")
        return
    if result.dry_run:
        print("Dry run only; no files were changed.")
        return
    print(f"Changed: {result.changed}")


if __name__ == "__main__":
    main()
