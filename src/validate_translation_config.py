#!/usr/bin/env python3
"""Validate a versioned KM translation repository configuration."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_translation_tool.translation_repository_config import (
    TranslationRepositoryConfigError,
    load_translation_repository_config,
    version_branch,
    version_paths,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Validate translation-config.yml for versioned KM translation repos.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml.",
    )
    parser.add_argument(
        "--summary",
        help="Optional markdown summary path, for example $GITHUB_STEP_SUMMARY.",
    )
    return parser


def main() -> None:
    """Run config validation and print a compact summary."""

    args = build_argument_parser().parse_args()
    config_path = Path(args.config)
    try:
        config = load_translation_repository_config(config_path)
    except TranslationRepositoryConfigError as error:
        raise SystemExit(f"Invalid translation config: {error}") from error

    versions = config.knowledge_model.supported_versions
    latest_version = versions[-1]
    latest_paths = version_paths(config, latest_version)
    lines = [
        "KM translation config is valid.",
        f"Knowledge model: {config.knowledge_model.organization_id}:{config.knowledge_model.km_id}",
        f"Target language: {config.translation.target_language}",
        f"Supported versions: {', '.join(versions)}",
        f"Latest branch: {version_branch(config, latest_version)}",
        f"Latest source KM path: {latest_paths.source_km_path.as_posix()}",
        f"Translation tree path: {latest_paths.translation_tree_dir.as_posix()}",
        f"Protected chapters: {', '.join(config.migration.protected_chapters) or '(none)'}",
    ]
    print("\n".join(lines))
    if args.summary:
        write_summary(Path(args.summary), lines)


def write_summary(path: Path, lines: list[str]) -> None:
    """Append a markdown validation summary."""

    with path.open("a", encoding="utf-8") as handle:
        handle.write("## KM Translation Config\n\n")
        for line in lines:
            handle.write(f"- {line}\n")


if __name__ == "__main__":
    main()
