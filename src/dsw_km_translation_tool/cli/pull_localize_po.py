#!/usr/bin/env python3
"""Pull the latest Localize/Weblate PO into a translation branch."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_km_translation_tool.localize_sync import pull_localize_po


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Download the latest Localize PO snapshot into sources/localize/.",
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
    return parser


def main() -> None:
    """Run the Localize PO pull CLI."""

    args = build_argument_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    result = pull_localize_po(
        config_path=config_path,
        repo_root=repo_root,
    )
    print(f"Localize PO pull for KM {result.version}")
    print(f"  URL        : {result.url}")
    print(f"  Latest PO  : {result.latest_po_path}")
    print(f"  Downloaded : {result.bytes_downloaded} bytes")
    print(f"  Changed    : {result.changed}")
    print(f"  Initialized: {result.initialized}")


if __name__ == "__main__":
    main()
