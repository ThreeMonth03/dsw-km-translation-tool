#!/usr/bin/env python3
"""Discover upstream DSW Registry KM versions for a translation repository."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_translation_tool.km_registry import (
    KmRegistryError,
    discover_km_versions,
    render_km_version_discovery_markdown,
    write_km_version_discovery_markdown,
    write_km_version_discovery_report,
)
from dsw_translation_tool.translation_repository_config import TranslationRepositoryConfigError


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""

    parser = argparse.ArgumentParser(
        description="Discover KM package versions from the DSW Registry.",
    )
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml.",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Translation repository root used to resolve relative config/report paths.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional JSON report path, for example reviews/km_version_discovery.json.",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help="Optional Markdown summary path, for example $GITHUB_STEP_SUMMARY.",
    )
    parser.add_argument(
        "--details-out",
        default=None,
        help="Optional path to write a full Markdown discovery report.",
    )
    parser.add_argument(
        "--fail-on-new-version",
        action="store_true",
        help="Exit with a non-zero status when Registry has versions missing from config.",
    )
    return parser


def main() -> None:
    """Run KM Registry version discovery."""

    args = build_argument_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    config_path = _resolve_path(repo_root, args.config)
    try:
        result = discover_km_versions(config_path=config_path)
    except (KmRegistryError, TranslationRepositoryConfigError) as error:
        raise SystemExit(f"Unable to discover KM versions: {error}") from error

    print(f"KM Registry discovery for {result.organization_id}:{result.km_id}")
    print(f"  Registry API       : {result.registry_api_url}")
    print(f"  Configured versions: {_format_versions(result.configured_versions)}")
    print(f"  Registry versions  : {_format_versions(result.registry_versions)}")
    print(f"  New versions       : {_format_versions(result.new_versions)}")
    print(f"  Missing in registry: {_format_versions(result.missing_versions)}")
    print()
    print(render_km_version_discovery_markdown(result), end="")
    if args.report:
        report_path = _resolve_path(repo_root, args.report)
        write_km_version_discovery_report(result=result, report_path=report_path)
        print(f"  Report             : {report_path}")
    if args.summary:
        summary_path = _resolve_path(repo_root, args.summary)
        write_km_version_discovery_markdown(result=result, report_path=summary_path)
    if args.details_out:
        details_path = _resolve_path(repo_root, args.details_out)
        write_km_version_discovery_markdown(result=result, report_path=details_path)
        print(f"  Markdown report    : {details_path}")
    if args.fail_on_new_version and result.new_versions:
        raise SystemExit(
            "Registry has KM versions missing from translation-config.yml: "
            + ", ".join(result.new_versions)
        )


def _resolve_path(repo_root: Path, path_arg: str) -> Path:
    path = Path(path_arg)
    if path.is_absolute():
        return path
    return repo_root / path


def _format_versions(versions: tuple[str, ...]) -> str:
    return ", ".join(versions) if versions else "(none)"


if __name__ == "__main__":
    main()
