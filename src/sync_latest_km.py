#!/usr/bin/env python3
"""Keep the current translation branch synchronized with the latest KM."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dsw_translation_tool.km_latest_sync import KmLatestSyncError, sync_latest_km_version


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Update the current translation branch when the Registry has a newer KM.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--tooling-repo", default=".")
    parser.add_argument("--config", default="translation-config.yml")
    parser.add_argument("--registry-token-env", default="DSW_REGISTRY_TOKEN")
    parser.add_argument("--skip-without-token", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
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
            skip_without_token=args.skip_without_token,
            dry_run=args.dry_run,
        )
    except KmLatestSyncError as error:
        raise SystemExit(f"Unable to sync latest KM: {error}") from error

    print(f"Configured KM version: {result.configured_version}")
    print(f"Registry KM version  : {result.registry_version or '(none)'}")
    if result.skipped_reason:
        print(f"Skipped latest-KM sync: {result.skipped_reason}")
        return
    if result.dry_run:
        print("Dry run only; no files were changed.")
        return
    print(f"Changed: {result.changed}")


if __name__ == "__main__":
    main()
