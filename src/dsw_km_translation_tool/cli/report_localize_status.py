#!/usr/bin/env python3
"""Report status metrics for a Localize/Weblate PO snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from dsw_km_translation_tool.localize_status import (
    build_localize_po_status_report,
    render_localize_po_status_markdown,
    write_localize_po_status_json,
    write_localize_po_status_markdown,
)
from dsw_km_translation_tool.localize_sync import download_localize_po
from dsw_km_translation_tool.po_support.parser import PoCatalogError
from dsw_km_translation_tool.translation_repository_config import (
    load_translation_repository_config,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Report translation status metrics for a Localize/Weblate PO file.",
    )
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument(
        "--po",
        help="Path to the Localize/Weblate PO file to inspect.",
    )
    source.add_argument(
        "--repo-root",
        type=Path,
        help="Inspect live Weblate without replacing the repository snapshot.",
    )
    parser.add_argument("--config", type=Path, default=Path("translation-config.yml"))
    parser.add_argument(
        "--json-out",
        help="Optional path to write the status report as JSON.",
    )
    parser.add_argument(
        "--summary",
        help="Optional Markdown summary path, for example $GITHUB_STEP_SUMMARY.",
    )
    parser.add_argument(
        "--details-out",
        help="Optional path to write a full Markdown issue report.",
    )
    parser.add_argument(
        "--issue-limit",
        type=int,
        default=20,
        help="Maximum issue rows to print per issue type. Use 0 to print all.",
    )
    return parser


def main() -> None:
    """Run the Localize/Weblate PO status CLI."""

    args = build_argument_parser().parse_args()
    try:
        with TemporaryDirectory(prefix="dsw-live-status-") as temp:
            if args.repo_root:
                config_path = (
                    args.config if args.config.is_absolute() else args.repo_root / args.config
                )
                config = load_translation_repository_config(config_path)
                po_path = Path(temp) / "latest.po"
                po_path.write_bytes(download_localize_po(config=config))
            else:
                po_path = Path(args.po)
            report = build_localize_po_status_report(po_path)
    except (OSError, PoCatalogError) as error:
        raise SystemExit(f"Unable to report PO status: {error}") from error
    issue_limit = None if args.issue_limit == 0 else args.issue_limit
    print(render_localize_po_status_markdown(report, issue_limit=issue_limit), end="")
    if args.json_out:
        write_localize_po_status_json(report, args.json_out)
        print(f"JSON report written to {args.json_out}")
    if args.summary:
        write_localize_po_status_markdown(report, args.summary, issue_limit=issue_limit)
    if args.details_out:
        write_localize_po_status_markdown(report, args.details_out, issue_limit=None)
        print(f"Markdown details written to {args.details_out}")


if __name__ == "__main__":
    main()
