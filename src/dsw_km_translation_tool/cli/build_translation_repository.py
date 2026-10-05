#!/usr/bin/env python3
"""Rebuild a Git-managed KM translation repository."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_km_translation_tool.translation_repository_build import (
    TranslationRepositoryBuildError,
    build_translation_repository,
    validate_committed_locale,
)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rebuild checked-in translation outputs without Weblate.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--config", default="translation-config.yml")
    parser.add_argument(
        "--base-ref", help="Accepted PR base for generated-locale integrity checks."
    )
    parser.add_argument(
        "--head-ref", help="Candidate PR revision for generated-locale integrity checks."
    )
    return parser


def main() -> None:
    args = build_argument_parser().parse_args()
    if bool(args.base_ref) != bool(args.head_ref):
        raise SystemExit("--base-ref and --head-ref must be provided together")
    try:
        result = build_translation_repository(
            repo_root=Path(args.repo_root),
            config_path=Path(args.config),
        )
        if args.base_ref:
            validate_committed_locale(
                repo_root=Path(args.repo_root).resolve(),
                final_po_path=result.final_po_path,
                base_ref=args.base_ref,
                head_ref=args.head_ref,
            )
    except (OSError, ValueError, TranslationRepositoryBuildError) as error:
        raise SystemExit(f"Unable to build translation repository: {error}") from error

    print(f"Source KM: {result.source_km_path}")
    print(f"Source catalog: {result.source_po_path}")
    print(f"Translation tree: {result.tree_dir}")
    print(f"Final PO: {result.final_po_path}")


if __name__ == "__main__":
    main()
