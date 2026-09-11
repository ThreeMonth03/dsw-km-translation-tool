#!/usr/bin/env python3
"""Validate a PO for native DSW knowledge-model locale import."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dsw_km_translation_tool.native_locale import (
    NativeLocaleValidationError,
    validate_native_locale,
)


def build_argument_parser() -> argparse.ArgumentParser:
    """Build CLI arguments."""

    parser = argparse.ArgumentParser(
        description="Validate a PO for native DSW knowledge-model locale import.",
    )
    parser.add_argument("--po", required=True, help="Translated PO file.")
    parser.add_argument("--km", required=True, help="Source KM bundle.")
    parser.add_argument("--target-language", required=True, help="Expected PO Language value.")
    parser.add_argument("--report", help="Optional JSON report path.")
    return parser


def main() -> None:
    """Run native locale validation."""

    args = build_argument_parser().parse_args()
    try:
        result = validate_native_locale(
            po_path=Path(args.po),
            km_path=Path(args.km),
            target_language=args.target_language,
        )
    except (NativeLocaleValidationError, OSError) as error:
        raise SystemExit(f"Native DSW locale validation failed: {error}") from error

    if args.report:
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        "PO syntax, language and KM references are valid; coverage and server import are separate checks."
    )
    print(f"Language: {result.catalog_language}")
    print(f"Messages: {result.total_messages}")
    print(f"Translated: {result.translated_messages}")


if __name__ == "__main__":
    main()
