#!/usr/bin/env python3
"""Merge pulled Localize/Weblate PO updates into the repo-generated PO."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_translation_tool.localize_merge import LocalizePoMerger
from dsw_translation_tool.translation_repository_config import (
    load_translation_repository_config,
    version_paths,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Merge Localize/Weblate PO snapshots into a repo PO.",
    )
    parser.add_argument("--config", default="translation-config.yml")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--km-version", default=None)
    parser.add_argument("--base-po", default=None)
    parser.add_argument("--latest-po", default=None)
    parser.add_argument("--repo-po", default=None)
    parser.add_argument("--out-po", default=None)
    parser.add_argument("--report", default=None)
    parser.add_argument("--tree-dir", default=None)
    parser.add_argument(
        "--conflict-policy",
        choices=("conservative", "latest-wins"),
        default="conservative",
        help=(
            "How to handle entries changed in both the repository and Weblate. "
            "Use latest-wins when the latest Weblate state is authoritative."
        ),
    )
    return parser


def main() -> None:
    """Run the Localize PO merge CLI."""

    args = build_argument_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    config_path = _resolve_repo_path(repo_root, Path(args.config))
    repository_config = load_translation_repository_config(config_path)
    version = args.km_version or repository_config.knowledge_model.supported_versions[-1]
    paths = version_paths(repository_config, version)
    result = LocalizePoMerger().merge(
        base_po_path=_resolve_optional_repo_path(
            repo_root,
            args.base_po,
            paths.localize_base_po_path,
        ),
        latest_po_path=_resolve_optional_repo_path(
            repo_root,
            args.latest_po,
            paths.localize_latest_po_path,
        ),
        repo_po_path=_resolve_optional_repo_path(
            repo_root,
            args.repo_po,
            paths.final_po_path,
        ),
        out_po_path=_resolve_optional_repo_path(
            repo_root,
            args.out_po,
            paths.final_po_path,
        ),
        report_path=_resolve_optional_repo_path(
            repo_root,
            args.report,
            paths.localize_merge_report_path,
        ),
        tree_dir=_resolve_optional_repo_path(
            repo_root,
            args.tree_dir,
            paths.translation_tree_dir,
        ),
        protected_chapters=repository_config.migration.protected_chapters,
        conflict_policy=args.conflict_policy,
    )
    print("Localize PO merge")
    print(f"  Version              : {version}")
    print(f"  Output PO            : {result.output_po_path}")
    print(f"  Report               : {result.report_path}")
    print(f"  Total entries        : {result.total_entries}")
    print(f"  Conflict policy      : {args.conflict_policy}")
    print(f"  Accepted latest      : {result.accepted_latest}")
    print(f"  Conflicts            : {result.conflicts}")
    print(f"  Protected skips      : {result.protected_skips}")
    print(f"  Empty overwrite skips: {result.empty_overwrite_skips}")
    print(f"  Source mismatches    : {result.source_mismatches}")
    print(f"  Fuzzy skips          : {result.fuzzy_skips}")
    print(f"  Missing Localize keys: {result.missing_localize_entries}")


def _resolve_optional_repo_path(repo_root: Path, value: str | None, default: Path) -> Path:
    if value:
        return _resolve_repo_path(repo_root, Path(value))
    return repo_root / default


def _resolve_repo_path(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


if __name__ == "__main__":
    main()
