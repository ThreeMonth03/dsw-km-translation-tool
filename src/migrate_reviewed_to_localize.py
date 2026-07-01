#!/usr/bin/env python3
"""Prepare or apply a one-shot reviewed-translation migration to Localize."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dsw_translation_tool.localize_migration import (
    LocalizeMigrationError,
    LocalizeMigrationResult,
    build_migration_result,
    derive_upload_url,
    prepare_consolidated_localize_migration,
    prepare_reviewed_localize_migration,
    upload_migration_po,
    write_migration_report,
)
from dsw_translation_tool.translation_repository_config import (
    TranslationRepositoryConfig,
    load_translation_repository_config,
    version_paths,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Prepare a reviewed-chapter PO for one-shot upload to Localize/Weblate. "
            "The command is dry-run by default; pass --apply to upload."
        ),
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Translation repository root.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml.",
    )
    parser.add_argument(
        "--km-version",
        default=None,
        help="KM version to use for default paths. Defaults to latest configured version.",
    )
    parser.add_argument(
        "--chapters",
        nargs="+",
        required=True,
        help='Reviewed top-level chapter prefixes, for example "0004" "0005" "0006".',
    )
    parser.add_argument("--localize-po", default=None, help="Current Localize PO path.")
    parser.add_argument("--repo-po", default=None, help="PO generated from repository tree.")
    parser.add_argument("--tree-dir", default=None, help="Repository translation tree path.")
    parser.add_argument(
        "--out-po",
        default=None,
        help="Prepared migration PO path.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Migration report JSON path.",
    )
    parser.add_argument(
        "--upload-url",
        default=None,
        help="Localize/Weblate upload API URL. Defaults to one derived from localize.download_url.",
    )
    parser.add_argument(
        "--token-env",
        default="LOCALIZE_API_TOKEN",
        help="Environment variable containing the Localize/Weblate API token.",
    )
    parser.add_argument(
        "--auth-scheme",
        default="Token",
        choices=("Token", "Bearer"),
        help="Authorization header scheme for Localize/Weblate.",
    )
    parser.add_argument(
        "--method",
        default="translate",
        help="Weblate upload method. Keep the default for migration uploads.",
    )
    parser.add_argument(
        "--conflicts",
        default="replace-translated",
        choices=("ignore", "replace-translated", "replace-approved"),
        help=("Weblate conflict handling for uploaded strings that already have translations."),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Upload the prepared PO to Localize/Weblate.",
    )
    parser.add_argument(
        "--fill-localize-blanks-from-repo",
        action="store_true",
        help=(
            "Keep non-empty Localize translations outside reviewed chapters and use "
            "repository translations only to fill Localize blanks."
        ),
    )
    return parser


def main() -> None:
    """Run reviewed translation migration preparation and optional upload."""

    args = build_argument_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path
    config = load_translation_repository_config(config_path) if config_path.exists() else None
    paths = None
    if config is not None:
        version = args.km_version or config.knowledge_model.supported_versions[-1]
        paths = version_paths(config, version)
    elif not (args.localize_po and args.repo_po and args.tree_dir):
        raise SystemExit(
            "translation-config.yml was not found; pass --localize-po, --repo-po, "
            "and --tree-dir to run without repository config"
        )

    localize_po = _resolve_repo_path(
        repo_root,
        Path(args.localize_po)
        if args.localize_po
        else _configured_path(paths.localize_latest_po_path, "--localize-po"),
    )
    repo_po = _resolve_repo_path(
        repo_root,
        Path(args.repo_po) if args.repo_po else _configured_path(paths.final_po_path, "--repo-po"),
    )
    tree_dir = _resolve_repo_path(
        repo_root,
        Path(args.tree_dir)
        if args.tree_dir
        else _configured_path(paths.translation_tree_dir, "--tree-dir"),
    )
    out_po = _resolve_repo_path(
        repo_root,
        Path(args.out_po) if args.out_po else Path("reviews/localize_migration_upload.po"),
    )
    report_path = _resolve_repo_path(
        repo_root,
        Path(args.report) if args.report else Path("reviews/localize_migration_report.json"),
    )

    try:
        prepare = (
            prepare_consolidated_localize_migration
            if args.fill_localize_blanks_from_repo
            else prepare_reviewed_localize_migration
        )
        result = prepare(
            localize_po_path=localize_po,
            repo_po_path=repo_po,
            tree_dir=tree_dir,
            chapters=tuple(args.chapters),
            out_po_path=out_po,
            report_path=report_path,
        )
        if args.apply:
            if result.included_entries == 0:
                print("No reviewed translation differences to upload.")
            else:
                token = os.environ.get(args.token_env, "")
                upload = upload_migration_po(
                    upload_url=args.upload_url or _configured_upload_url(config),
                    token=token,
                    po_path=result.migration_po_path,
                    method=args.method,
                    auth_scheme=args.auth_scheme,
                    extra_fields={"conflicts": args.conflicts},
                )
                result = build_migration_result(
                    migration_po_path=result.migration_po_path,
                    report_path=result.report_path,
                    chapters=result.chapters,
                    decisions=result.decisions,
                    upload=upload,
                    total_reviewed_keys=result.total_reviewed_keys,
                )
                write_migration_report(result)
    except LocalizeMigrationError as error:
        raise SystemExit(str(error)) from error

    print("Reviewed Localize migration prepared.")
    print(f"  Chapters         : {', '.join(result.chapters)}")
    print(f"  Migration PO     : {result.migration_po_path}")
    print(f"  Report           : {result.report_path}")
    print(f"  Reviewed keys    : {result.total_reviewed_keys}")
    print(f"  Included entries : {result.included_entries}")
    print(f"  Already current  : {result.already_current}")
    print(f"  Empty repo skips : {result.skipped_empty_repo}")
    print(f"  Source mismatches: {result.source_mismatches}")
    print(f"  Missing Localize : {result.missing_localize_entries}")
    if args.fill_localize_blanks_from_repo:
        counts = _decision_counts(result)
        print(f"  Kept Localize    : {counts.get('keep-localize', 0)}")
        print(f"  Blank fills      : {counts.get('fill-localize-blank', 0)}")
        print(f"  Empty both       : {counts.get('empty-both', 0)}")
    if result.upload:
        print(f"  Uploaded         : HTTP {result.upload.status_code}")
    else:
        print("  Uploaded         : no (dry run)")


def _resolve_repo_path(repo_root: Path, path: Path) -> Path:
    """Resolve a path relative to the translation repository root."""

    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _configured_path(path: Path | None, argument_name: str) -> Path:
    """Return a configured default path or fail with a helpful argument hint."""

    if path is None:
        raise SystemExit(
            f"translation-config.yml was not found; pass {argument_name} to run without "
            "repository config"
        )
    return path


def _configured_upload_url(config: TranslationRepositoryConfig | None) -> str:
    """Return the configured Localize upload URL or fail with a helpful hint."""

    if config is None:
        raise LocalizeMigrationError(
            "Uploading without translation-config.yml requires --upload-url"
        )
    return derive_upload_url(config.localize.download_url)


def _decision_counts(result: LocalizeMigrationResult) -> dict[str, int]:
    """Return decision counts from a migration result."""

    counts: dict[str, int] = {}
    for decision in result.decisions:
        counts[decision.decision] = counts.get(decision.decision, 0) + 1
    return counts


if __name__ == "__main__":
    main()
