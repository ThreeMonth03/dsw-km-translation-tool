#!/usr/bin/env python3
"""Check or synchronize files managed by translation repository templates."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_km_translation_tool.translation_repository_scaffold import (
    TranslationRepositoryScaffoldError,
    check_translation_repository_scaffold,
    sync_translation_repository_scaffold,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description=(
            "Check or update translation repository docs and workflows without "
            "changing translation-config.yml or translation artifacts."
        ),
    )
    parser.add_argument("action", choices=("check", "sync"))
    parser.add_argument("--repo-root", required=True, help="Translation repository path.")
    parser.add_argument(
        "--tooling-repo",
        default=".",
        help="Tooling repository containing scaffold templates.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Config path relative to --repo-root unless absolute.",
    )
    return parser


def main() -> None:
    """Run a scaffold check or synchronization."""

    args = build_argument_parser().parse_args()
    try:
        if args.action == "check":
            result = check_translation_repository_scaffold(
                repo_root=Path(args.repo_root),
                tooling_repo=Path(args.tooling_repo),
                config_path=Path(args.config),
            )
        else:
            result = sync_translation_repository_scaffold(
                repo_root=Path(args.repo_root),
                tooling_repo=Path(args.tooling_repo),
                config_path=Path(args.config),
            )
    except (OSError, ValueError, TranslationRepositoryScaffoldError) as error:
        raise SystemExit(
            f"Unable to {args.action} translation repository scaffold: {error}"
        ) from error

    print("Translation repository scaffold")
    print(f"  Repository : {result.repo_root}")
    print(f"  Managed    : {len(result.managed_files)}")
    print(f"  Changed    : {len(result.changed_files)}")
    for path in result.changed_files:
        print(f"    {path}")

    if args.action == "check" and not result.aligned:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
