#!/usr/bin/env python3
"""Run an integration smoke test against current upstream KM and Weblate PO."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from dsw_km_translation_tool.upstream_smoke import (
    UpstreamSmokeError,
    render_upstream_smoke_markdown,
    run_upstream_smoke,
    write_upstream_smoke_markdown,
    write_upstream_smoke_report,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Verify that current upstream KM and Weblate PO still build.",
    )
    parser.add_argument(
        "--work-dir",
        default=".cache/upstream-smoke",
        help="Disposable workspace used for downloaded source snapshots and outputs.",
    )
    parser.add_argument(
        "--config",
        default="examples/translation-config.yml",
        help="Translation config template copied into the smoke workspace.",
    )
    parser.add_argument(
        "--registry-token-env",
        default="DSW_REGISTRY_TOKEN",
        help="Environment variable containing the DSW Registry token.",
    )
    parser.add_argument(
        "--skip-without-token",
        action="store_true",
        help="Exit successfully without testing when the registry token is missing.",
    )
    parser.add_argument(
        "--report",
        default=None,
        help="Optional JSON report path.",
    )
    parser.add_argument(
        "--summary",
        default=None,
        help="Optional Markdown summary path, for example $GITHUB_STEP_SUMMARY.",
    )
    parser.add_argument(
        "--details-out",
        default=None,
        help="Optional path to write a full Markdown report.",
    )
    return parser


def main() -> None:
    """Run the upstream smoke CLI."""

    args = build_argument_parser().parse_args()
    token = os.environ.get(args.registry_token_env, "")
    try:
        result = run_upstream_smoke(
            work_dir=Path(args.work_dir),
            config_template_path=Path(args.config),
            registry_token=token,
            skip_without_token=args.skip_without_token,
        )
    except UpstreamSmokeError as error:
        raise SystemExit(f"Unable to run upstream smoke: {error}") from error

    print(render_upstream_smoke_markdown(result), end="")
    if args.report:
        write_upstream_smoke_report(result=result, report_path=Path(args.report))
        print(f"JSON report written to {args.report}")
    if args.summary:
        write_upstream_smoke_markdown(result=result, report_path=Path(args.summary))
    if args.details_out:
        write_upstream_smoke_markdown(result=result, report_path=Path(args.details_out))
        print(f"Markdown details written to {args.details_out}")


if __name__ == "__main__":
    main()
