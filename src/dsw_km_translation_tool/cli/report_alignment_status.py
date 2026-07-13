#!/usr/bin/env python3
"""Report read-only alignment between Localize, tree, PO, and KM artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from dsw_km_translation_tool.alignment_status import (
    build_alignment_status_report,
    render_alignment_status_markdown,
    write_alignment_status_json,
    write_alignment_status_markdown,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Verify that Weblate, the checked-in Localize PO, tree output, "
            "final PO, and final KM are aligned."
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
        "--json-out",
        help="Optional path to write the alignment report as JSON.",
    )
    parser.add_argument(
        "--summary",
        help="Optional Markdown summary path, for example $GITHUB_STEP_SUMMARY.",
    )
    parser.add_argument(
        "--details-out",
        help="Optional path to write a full Markdown report.",
    )
    parser.add_argument(
        "--artifact-dir",
        help="Optional directory for generated comparison artifacts.",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        help="Exit with status 1 when any alignment check fails.",
    )
    return parser


def main() -> None:
    """Run the alignment report CLI."""

    args = build_argument_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = repo_root / config_path

    report = build_alignment_status_report(
        repo_root=repo_root,
        config_path=config_path,
        artifact_dir=Path(args.artifact_dir) if args.artifact_dir else None,
    )
    print(render_alignment_status_markdown(report), end="")
    if args.json_out:
        write_alignment_status_json(report, args.json_out)
        print(f"JSON report written to {args.json_out}")
    if args.summary:
        write_alignment_status_markdown(report, args.summary)
    if args.details_out:
        write_alignment_status_markdown(report, args.details_out)
        print(f"Markdown details written to {args.details_out}")
    if args.fail_on_mismatch and not report.aligned:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
