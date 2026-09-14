"""Measure translation coverage against a POT exported by official DSW."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import PoFileError, read_po

from .translation_repository_config import normalize_version


class LocaleCoverageError(ValueError):
    """Raised when catalogs cannot be compared reliably."""


def _read_catalog(path: Path) -> Catalog:
    try:
        with path.open(encoding="utf-8") as handle:
            return read_po(handle, abort_invalid=True)
    except (PoFileError, UnicodeError, ValueError) as error:
        raise LocaleCoverageError(f"Invalid gettext catalog {path.name}: {error}") from error


def _key(message: Message) -> tuple[str | None, str | tuple[str, ...]]:
    return message.context, message.id


def _entry(message: Message) -> dict[str, object]:
    return {
        "msgctxt": message.context,
        "msgid": message.id,
        "references": [location for location, _ in message.locations],
    }


def _read_official_pot(path: Path, package_id: str, source_language: str) -> Catalog:
    pot = _read_catalog(path)
    if dict(pot.mime_headers).get("Project-Id-Version", "").strip() != package_id:
        raise LocaleCoverageError("Official POT does not identify the configured KM package")
    if pot.locale_identifier != source_language:
        raise LocaleCoverageError(f"POT Language header does not match {source_language!r}")
    if not any(message.id for message in pot):
        raise LocaleCoverageError("Official POT contains no translatable messages")
    return pot


def compare_locale_coverage(
    *,
    pot_path: Path,
    po_path: Path,
    package_id: str,
    source_language: str,
    target_language: str,
) -> dict[str, object]:
    """Report missing, empty, fuzzy and extra messages without changing either file.

    Message identity uses gettext context and source text, not source-reference
    formatting. The official POT and Weblate can format UUID references differently.
    Partial locales are importable, but must never be reported as complete.
    """

    pot = _read_official_pot(pot_path, package_id, source_language)
    po = _read_catalog(po_path)
    if po.locale_identifier != target_language:
        raise LocaleCoverageError(f"PO Language header does not match {target_language!r}")
    expected = {_key(message): message for message in pot if message.id}
    actual = {_key(message): message for message in po if message.id}

    missing, untranslated, fuzzy, translated = [], [], [], 0
    for key, source in expected.items():
        target = actual.get(key)
        if target is None:
            missing.append(_entry(source))
        elif target.fuzzy:
            fuzzy.append(_entry(source))
        elif not target.string or (
            isinstance(target.string, (tuple, list)) and not all(target.string)
        ):
            untranslated.append(_entry(source))
        else:
            translated += 1
    extra = [_entry(message) for key, message in actual.items() if key not in expected]
    return {
        "package_id": package_id,
        "source_language": source_language,
        "target_language": target_language,
        "pot_sha256": hashlib.sha256(pot_path.read_bytes()).hexdigest(),
        "po_sha256": hashlib.sha256(po_path.read_bytes()).hexdigest(),
        "status": "complete" if not (missing or untranslated or fuzzy or extra) else "incomplete",
        "counts": {
            "expected": len(expected),
            "catalog": len(actual),
            "translated": translated,
            "missing": len(missing),
            "untranslated": len(untranslated),
            "fuzzy": len(fuzzy),
            "extra": len(extra),
        },
        "missing": missing,
        "untranslated": untranslated,
        "fuzzy": fuzzy,
        "extra": extra,
    }


def compare_source_catalog(
    *, pot_path: Path, upstream_pot_path: Path, package_id: str, source_language: str
) -> dict[str, object]:
    """Compare the official export with Weblate's shared source POT, without merging.

    The repository POT may use a human-readable project name instead of package
    coordinates. Require its version to match; retain both headers as evidence.
    Source changes cannot safely be distinguished from removals and additions,
    so any upstream-only entry requires maintainer review, never automatic deletion.
    """
    pot = _read_official_pot(pot_path, package_id, source_language)
    upstream, project, version = read_upstream_pot(upstream_pot_path, package_id, source_language)
    expected = {_key(message): message for message in pot if message.id}
    actual = {_key(message): message for message in upstream if message.id}
    if version != package_id.rsplit(":", 1)[-1]:
        return {
            "package_id": package_id,
            "upstream_project_id_version": project,
            "required_package_id": f"{package_id.rsplit(':', 1)[0]}:{version}",
            "pot_sha256": hashlib.sha256(pot_path.read_bytes()).hexdigest(),
            "upstream_pot_sha256": hashlib.sha256(upstream_pot_path.read_bytes()).hexdigest(),
            "status": "waiting-for-km",
            "counts": {"official": len(expected), "upstream": len(actual)},
            "missing_upstream": [],
            "upstream_only": [],
        }
    missing = [_entry(message) for key, message in expected.items() if key not in actual]
    extra = [_entry(message) for key, message in actual.items() if key not in expected]
    return {
        "package_id": package_id,
        "upstream_project_id_version": project,
        "pot_sha256": hashlib.sha256(pot_path.read_bytes()).hexdigest(),
        "upstream_pot_sha256": hashlib.sha256(upstream_pot_path.read_bytes()).hexdigest(),
        "status": "review-required" if extra else "additions-only" if missing else "aligned",
        "counts": {
            "official": len(expected),
            "upstream": len(actual),
            "shared": len(expected.keys() & actual.keys()),
            "missing_upstream": len(missing),
            "upstream_only": len(extra),
        },
        "missing_upstream": missing,
        "upstream_only": extra,
    }


def read_upstream_pot(
    path: Path, package_id: str, source_language: str
) -> tuple[Catalog, str, str]:
    """Read a nonempty source POT and identify its KM without relabeling it."""
    catalog = _read_catalog(path)
    project = dict(catalog.mime_headers).get("Project-Id-Version", "").strip()
    family, current_version = package_id.rsplit(":", 1)
    if project.startswith(f"{family}:"):
        try:
            version = normalize_version(project[len(family) + 1 :])
        except ValueError as error:
            raise LocaleCoverageError("Upstream POT has an invalid KM version") from error
    elif ":" not in project and project.endswith(f" {current_version}"):
        version = current_version
    else:
        raise LocaleCoverageError(
            "Upstream POT package/version does not identify the configured KM"
        )
    if catalog.locale_identifier not in (None, "", source_language):
        raise LocaleCoverageError("Upstream POT Language header differs from the source language")
    if not any(message.id for message in catalog):
        raise LocaleCoverageError("Upstream POT contains no translatable messages")
    return catalog, project, version


def _render_entries(entries: list[dict[str, object]]) -> list[str]:
    lines = []
    for entry in entries:
        source = json.dumps(entry["msgid"], ensure_ascii=False)
        fence = "`" * max(3, 1 + max(map(len, re.findall(r"`+", source)), default=0))
        lines.extend([fence, source, fence, ""])
        if entry["msgctxt"]:
            lines.extend([f"Context: {json.dumps(entry['msgctxt'])}", ""])
    return lines


def render_source_catalog(report: dict[str, object], *, details: bool = True) -> str:
    """Render an upstream review report, not a proposed translation replacement."""
    if report["status"] == "waiting-for-km":
        return (
            "## Weblate upstream source catalog\n\n"
            "Status: **waiting-for-km**\n\n"
            f"Configured KM: `{report['package_id']}`\n\n"
            f"Upstream POT requires: `{report['required_package_id']}`\n\n"
            f"Upstream POT: {report['upstream_url']}\n\n"
            "Coverage was not compared across KM versions. Existing translations are unchanged.\n"
        )
    lines = [
        "## Weblate upstream source catalog",
        "",
        f"Knowledge Model: `{report['package_id']}`",
        f"Source catalog: **{report['status']}**",
        f"Upstream POT: {report['upstream_url']}",
        "",
        "| Category | Messages |",
        "| --- | ---: |",
        *(f"| {name} | {count} |" for name, count in report["counts"].items()),
        "",
        "This compares the repository POT, not live Weblate units or translation quality.",
        "No POT, PO, Weblate settings or translations have been updated.",
        "",
        "Review source differences with the upstream maintainers. Any accepted POT update",
        "still needs a PO merge in Weblate or upstream automation. All language catalogs",
        "may gain untranslated entries; preserve existing translations and review any",
        "changed or removed source strings before merging. Do not replace language PO files.",
        "",
    ]
    if details:
        for category in ("missing_upstream", "upstream_only"):
            if report[category]:
                lines.extend([f"### {category.replace('_', ' ').capitalize()}", ""])
                lines.extend(_render_entries(report[category]))
    return "\n".join(lines)


def render_locale_coverage(report: dict[str, object], *, details: bool = True) -> str:
    """Render counts and, optionally, complete source strings for human review."""

    lines = [
        "## Official DSW locale coverage",
        "",
        f"Knowledge Model: `{report['package_id']}`",
        f"Coverage: **{report['status']}**",
        "",
        "| Category | Messages |",
        "| --- | ---: |",
        *(f"| {name} | {count} |" for name, count in report["counts"].items()),
        "",
        "Import success and complete translation coverage are separate checks.",
        "",
    ]
    if details:
        for category in ("missing", "untranslated", "fuzzy", "extra"):
            if not report[category]:
                continue
            lines.extend([f"### {category.capitalize()}", ""])
            lines.extend(_render_entries(report[category]))
    return "\n".join(lines)
