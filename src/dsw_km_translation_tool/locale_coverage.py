"""Measure translation coverage against a POT exported by official DSW."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from babel.messages.catalog import Catalog, Message
from babel.messages.pofile import PoFileError, read_po


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

    pot = _read_catalog(pot_path)
    po = _read_catalog(po_path)
    if dict(pot.mime_headers).get("Project-Id-Version", "").strip() != package_id:
        raise LocaleCoverageError("Official POT does not identify the configured KM package")
    for name, catalog, language in (("POT", pot, source_language), ("PO", po, target_language)):
        if catalog.locale_identifier != language:
            raise LocaleCoverageError(f"{name} Language header does not match {language!r}")
    expected = {_key(message): message for message in pot if message.id}
    actual = {_key(message): message for message in po if message.id}
    if not expected:
        raise LocaleCoverageError("Official POT contains no translatable messages")

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
            for entry in report[category]:
                source = json.dumps(entry["msgid"], ensure_ascii=False)
                fence = "`" * max(3, 1 + max(map(len, re.findall(r"`+", source)), default=0))
                lines.extend([fence, source, fence, ""])
                if entry["msgctxt"]:
                    lines.extend([f"Context: {entry['msgctxt']}", ""])
    return "\n".join(lines)
