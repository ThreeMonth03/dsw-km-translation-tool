#!/usr/bin/env python3
"""Report GitHub-originated translation changes against Weblate."""

from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from dsw_km_translation_tool.cli.github_outputs import (
    append_github_outputs,
    append_markdown_summary,
)
from dsw_km_translation_tool.github_translation_contributions import (
    build_github_translation_report,
    write_github_translation_json,
    write_github_translation_markdown,
)
from dsw_km_translation_tool.localize_sync import pull_localize_po
from dsw_km_translation_tool.translation_repository_config import (
    load_translation_repository_config,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build the command-line parser for GitHub translation reports."""

    parser = argparse.ArgumentParser(
        description=(
            "Compare GitHub translation-tree edits with the current Weblate PO "
            "without writing either Git or Weblate."
        ),
    )
    parser.add_argument("--repo-root", required=True, help="Translation repository root.")
    parser.add_argument(
        "--config",
        default="translation-config.yml",
        help="Path to translation-config.yml, relative to --repo-root unless absolute.",
    )
    parser.add_argument("--base-ref", required=True, help="Accepted base Git ref.")
    parser.add_argument("--head-ref", default="HEAD", help="Candidate Git ref.")
    parser.add_argument("--json-out", required=True, help="JSON report output path.")
    parser.add_argument("--details-out", required=True, help="Markdown report output path.")
    parser.add_argument("--summary", default=None, help="Optional GitHub step summary path.")
    parser.add_argument("--github-output", default=None, help="Optional GitHub output file path.")
    return parser


def main() -> None:
    """Run the GitHub translation contribution report."""

    args = build_argument_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    config_path = _resolve_repo_path(repo_root, Path(args.config))
    repository_config = load_translation_repository_config(config_path)
    with TemporaryDirectory(prefix="dsw-github-translations-") as temp_dir:
        pull_result = pull_localize_po(
            config_path=config_path,
            repo_root=Path(temp_dir),
        )
        report = build_github_translation_report(
            repo_root=repo_root,
            base_ref=args.base_ref,
            head_ref=args.head_ref,
            latest_po_path=pull_result.latest_po_path,
            source_lang=repository_config.translation.source_language,
            target_lang=repository_config.translation.target_language,
        )

    write_github_translation_json(report, args.json_out)
    write_github_translation_markdown(report, args.details_out)
    append_markdown_summary(
        summary_path=args.summary,
        markdown_path=Path(args.details_out),
    )
    append_github_outputs(
        output_path=args.github_output,
        values={
            "has_translation_changes": report.has_translation_changes,
            "has_conflicts": report.has_conflicts,
            "has_format_errors": report.has_format_errors,
            "has_shared_block_errors": report.has_shared_block_errors,
            "importable_entries": report.importable_entries,
        },
    )
    if report.has_format_errors:
        raise SystemExit(
            "GitHub translation changes contain Markdown format errors. "
            "Review the report before merging."
        )
    if report.has_conflicts:
        raise SystemExit(
            "GitHub translation changes conflict with the current Weblate state. "
            "Review the report before merging."
        )
    if report.has_shared_block_errors:
        raise SystemExit(
            "GitHub translation changes leave shared blocks out of sync. "
            "Run shared-string sync and review the report before merging."
        )


def _resolve_repo_path(repo_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


if __name__ == "__main__":
    main()
