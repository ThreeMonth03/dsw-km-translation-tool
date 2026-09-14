"""Distinguish a known upstream version transition from broken translation inputs."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from .locale_coverage import read_upstream_pot
from .native_locale import NativeLocaleValidationError, validate_native_locale
from .po_support.parser import PoCatalogParser
from .source_catalog import snapshot_upstream_pot
from .translation_repository_config import TranslationRepositoryConfig, version_paths


@dataclass(frozen=True)
class PendingSourceUpdate:
    """Evidence for a PO that targets a different, explicitly identified KM."""

    configured_package_id: str
    required_package_id: str
    upstream_commit: str
    upstream_url: str
    pot_sha256: str
    po_sha256: str
    status: str = "waiting-for-km"

    def markdown(self) -> str:
        return (
            "## Upstream source readiness\n\nStatus: **waiting-for-km**\n\n"
            f"Configured KM: `{self.configured_package_id}`\n\n"
            f"Weblate POT and PO require: `{self.required_package_id}`\n\n"
            f"Source evidence: {self.upstream_url}\n\n"
            "No translations were applied. Keep the existing KM/PO pair until the matching "
            "official bundle is available and passes validation.\n"
        )


class SourceUpdatePending(Exception):
    """A known version transition; never used for syntax or same-version source errors."""

    def __init__(self, report: PendingSourceUpdate):
        self.report = report
        super().__init__(f"Weblate requires {report.required_package_id}; waiting for matching KM")


def upstream_target_version(config: TranslationRepositoryConfig) -> str:
    """Select the KM declared by the configured upstream POT, not a newer unrelated release."""
    if not config.localize.repository:
        raise ValueError("KM updates require localize.repository to identify the source POT")
    with tempfile.TemporaryDirectory(prefix="dsw-km-target-") as temp:
        pot_path = Path(temp) / "upstream.pot"
        snapshot_upstream_pot(config.localize.repository, pot_path)
        _, _, version = read_upstream_pot(
            pot_path, version_paths(config).package_id, config.translation.source_language
        )
        return version


def check_po_source(*, config: TranslationRepositoryConfig, po_path: Path, km_path: Path) -> None:
    """Accept a valid PO/KM pair, or prove why a different source version must wait.

    The PO header alone is not authoritative: Weblate may retain its old project
    version after msgmerge. Require the actual PO source fields to match the
    upstream POT before classifying any model mismatch as an expected wait.
    """
    blocks = PoCatalogParser.parse_text(
        po_path.read_text(encoding="utf-8"), target_language=config.translation.target_language
    )
    try:
        validate_native_locale(
            po_path=po_path, km_path=km_path, target_language=config.translation.target_language
        )
    except NativeLocaleValidationError as error:
        if not config.localize.repository:
            raise
        package_id = version_paths(config).package_id
        with tempfile.TemporaryDirectory(prefix="dsw-source-readiness-") as temp:
            pot_path = Path(temp) / "upstream.pot"
            commit, url = snapshot_upstream_pot(config.localize.repository, pot_path)
            _, _, version = read_upstream_pot(
                pot_path, package_id, config.translation.source_language
            )
            expected = PoCatalogParser(str(pot_path)).parse_blocks()

            def source_fields(catalog):
                return {
                    (reference.prefix, reference.uuid, reference.field, block.msgid)
                    for block in catalog
                    for reference in block.references
                }

            if version == config.knowledge_model.version or source_fields(blocks) != source_fields(
                expected
            ):
                raise error
            report = PendingSourceUpdate(
                configured_package_id=package_id,
                required_package_id=f"{package_id.rsplit(':', 1)[0]}:{version}",
                upstream_commit=commit,
                upstream_url=url,
                pot_sha256=hashlib.sha256(pot_path.read_bytes()).hexdigest(),
                po_sha256=hashlib.sha256(po_path.read_bytes()).hexdigest(),
            )
        raise SourceUpdatePending(report) from error


def report_pending(
    report: PendingSourceUpdate,
    *,
    json_path: Path | str | None = None,
    markdown_path: Path | str | None = None,
    summary_path: Path | str | None = None,
) -> None:
    """Publish an explicit waiting result without calling it a successful sync."""
    markdown = report.markdown()
    print(markdown)
    print("::warning::Upstream PO targets a different KM; existing translations were preserved.")
    for path, content in (
        (json_path, json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n"),
        (markdown_path, markdown),
    ):
        if path is not None:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
    summary = summary_path or os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with Path(summary).open("a", encoding="utf-8") as handle:
            handle.write(markdown)
