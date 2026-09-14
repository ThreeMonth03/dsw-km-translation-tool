"""Audit Weblate's upstream POT against an official export without uploading anything."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from dsw_km_translation_tool.locale_coverage import (
    LocaleCoverageError,
    render_source_catalog,
)
from dsw_km_translation_tool.source_catalog import audit_source_catalog
from dsw_km_translation_tool.translation_repository_config import (
    load_translation_repository_config,
    version_paths,
)


def main() -> None:
    """Write source-catalog evidence separately from native browser acceptance."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--official-pot", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="New directory for audit evidence.")
    parser.add_argument("--summary", type=Path)
    args = parser.parse_args()
    config = load_translation_repository_config(args.repo_root / "translation-config.yml")
    if args.out.exists():
        parser.error("--out must not exist to avoid mixing source catalog snapshots")
    args.out.mkdir(parents=True)
    if not config.localize.repository:
        report = {"status": "not-configured"}
        summary = (
            "## Weblate upstream source catalog\n\nNot checked: localize.repository is unset.\n"
        )
    else:
        try:
            report = audit_source_catalog(
                repository=config.localize.repository,
                pot_path=args.official_pot,
                out=args.out,
                package_id=version_paths(config).package_id,
                source_language=config.translation.source_language,
            )
        except (LocaleCoverageError, OSError) as error:
            report = {"status": "failed", "error": str(error)}
            summary = (
                "## Weblate upstream source catalog\n\nAudit failed; see source-catalog.json.\n"
            )
        else:
            summary = render_source_catalog(report, details=False)
    (args.out / "source-catalog.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "source-catalog.md").write_text(
        render_source_catalog(report) if "counts" in report else summary,
        encoding="utf-8",
    )
    print(summary)
    if args.summary:
        with args.summary.open("a", encoding="utf-8") as handle:
            handle.write(summary)
    if report["status"] == "failed":
        raise SystemExit(1)
    if report["status"] == "different":
        print("::warning::Upstream POT differs from the official export; review source-catalog.md.")


if __name__ == "__main__":
    main()
