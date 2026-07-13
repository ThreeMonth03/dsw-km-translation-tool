#!/usr/bin/env python3
"""Pull a source KM bundle snapshot from the DSW Registry."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dsw_km_translation_tool.km_bundle_sync import pull_km_bundle
from dsw_km_translation_tool.km_registry import KmRegistryError
from dsw_km_translation_tool.translation_repository_config import (
    TranslationRepositoryConfigError,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Download a KM bundle snapshot into sources/knowledge-models/.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Translation repository root where sources/ should be updated.",
    )
    parser.add_argument(
        "--registry-token-env",
        default="DSW_REGISTRY_TOKEN",
        help="Environment variable containing the DSW Registry token.",
    )
    parser.add_argument(
        "--skip-without-token",
        action="store_true",
        help="Exit successfully without pulling when the token environment variable is empty.",
    )
    parser.add_argument(
        "--allow-existing-change",
        action="store_true",
        help="Allow overwriting an existing KM bundle snapshot with different bytes.",
    )
    return parser


def main() -> None:
    """Run the KM bundle pull CLI."""

    args = build_argument_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    token = os.environ.get(args.registry_token_env, "")
    if not token.strip() and args.skip_without_token:
        print(f"Skipping KM bundle pull because {args.registry_token_env} is not set or empty.")
        return
    try:
        result = pull_km_bundle(
            config_path=config_path,
            repo_root=repo_root,
            token=token,
            allow_existing_change=args.allow_existing_change,
        )
    except (KmRegistryError, TranslationRepositoryConfigError) as error:
        raise SystemExit(f"Unable to pull KM bundle: {error}") from error

    print(f"KM bundle pull for {result.coordinate}")
    print(f"  URL            : {result.url}")
    print(f"  Target KM      : {result.target_path}")
    print(f"  Downloaded     : {result.bytes_downloaded} bytes")
    print(f"  SHA-256        : {result.sha256}")
    print(f"  Previous SHA-256: {result.previous_sha256 or '(none)'}")
    print(f"  Changed        : {result.changed}")
    print(f"  Initialized    : {result.initialized}")


if __name__ == "__main__":
    main()
