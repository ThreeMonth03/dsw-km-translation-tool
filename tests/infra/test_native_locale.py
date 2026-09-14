"""Tests for native DSW knowledge-model locale validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from dsw_km_translation_tool.native_locale import (
    NativeLocaleValidationError,
    validate_native_locale,
)
from dsw_km_translation_tool.po import PoCatalogParser
from tests.helpers import run_cli_command


def test_native_locale_accepts_valid_po(
    po_path: Path,
    model_path: Path,
    monkeypatch,
) -> None:
    from dsw_km_translation_tool.po_support import parser

    reads = []
    read_po = parser.read_po

    def counted_read(*args, **kwargs):
        reads.append(1)
        return read_po(*args, **kwargs)

    monkeypatch.setattr(parser, "read_po", counted_read)
    result = validate_native_locale(
        po_path=po_path,
        km_path=model_path,
        target_language="zh_Hant",
    )

    assert result.catalog_language == "zh_Hant"
    assert result.total_messages == 1466
    assert result.translated_messages > 0
    assert result.model_report["missingEntities"] == 0
    assert result.model_report["missingFields"] == 0
    assert result.model_report["mismatches"] == 0
    assert len(reads) == 1


def test_native_locale_rejects_wrong_language_header(
    po_path: Path,
    model_path: Path,
) -> None:
    with pytest.raises(NativeLocaleValidationError, match="Language header"):
        validate_native_locale(
            po_path=po_path,
            km_path=model_path,
            target_language="de",
        )


def test_native_locale_rejects_stale_source_text(
    po_path: Path,
    model_path: Path,
    workspace: Path,
) -> None:
    stale_po = workspace / "stale.po"
    stale_po.write_text(
        po_path.read_text(encoding="utf-8").replace(
            'msgid "10 years"',
            'msgid "11 years"',
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(NativeLocaleValidationError, match="Source mismatch"):
        validate_native_locale(
            po_path=stale_po,
            km_path=model_path,
            target_language="zh_Hant",
        )


@pytest.mark.parametrize("separator", [":", "/"])
def test_native_locale_rejects_missing_field_with_matching_title(
    po_path: Path,
    model_path: Path,
    workspace: Path,
    separator: str,
) -> None:
    entry = next(
        entry
        for entry in PoCatalogParser(str(po_path)).parse_entries()
        if entry.prefix == "chapter" and entry.field == "title"
    )
    invalid_reference = separator.join((entry.prefix, entry.uuid, "name"))
    invalid_po = workspace / "missing-field.po"
    invalid_po.write_text(
        po_path.read_text(encoding="utf-8").replace(entry.comment, invalid_reference, 1),
        encoding="utf-8",
    )

    with pytest.raises(NativeLocaleValidationError, match=f"Missing field: {entry.uuid}:name"):
        validate_native_locale(
            po_path=invalid_po,
            km_path=model_path,
            target_language="zh_Hant",
        )


def test_native_locale_cli_writes_report(
    repo_root: Path,
    po_path: Path,
    model_path: Path,
    workspace: Path,
) -> None:
    report_path = workspace / "native-locale.json"
    result = run_cli_command(
        repo_root,
        "dsw-km-validate-locale",
        "--po",
        str(po_path),
        "--km",
        str(model_path),
        "--target-language",
        "zh_Hant",
        "--report",
        str(report_path),
    )

    assert result.returncode == 0, result.stderr or result.stdout
    assert "PO syntax, language and KM references are valid" in result.stdout
    assert "coverage and server import are separate checks" in result.stdout
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["catalog_language"] == "zh_Hant"
