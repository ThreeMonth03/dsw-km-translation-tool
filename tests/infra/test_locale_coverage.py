"""Coverage must count missing messages, not only translated PO entries."""

from __future__ import annotations

from pathlib import Path

import pytest
from babel.messages.catalog import Catalog
from babel.messages.pofile import write_po

from dsw_km_translation_tool.locale_coverage import (
    LocaleCoverageError,
    compare_locale_coverage,
    render_locale_coverage,
)


def write_catalog(path: Path, catalog: Catalog) -> None:
    with path.open("wb") as handle:
        write_po(handle, catalog)


@pytest.fixture
def catalogs(tmp_path: Path) -> tuple[Path, Path, Catalog, Catalog]:
    pot = Catalog(locale="en", project="dsw:root:2.7.0", version="")
    pot.version = ""
    po = Catalog(locale="zh_Hant")
    for source, target in (("Administrative information", "行政資訊"), ("Contributors", "貢獻者")):
        pot.add(source, locations=[("chapter/uuid/title", None)])
        po.add(source, target, locations=[("chapter:uuid:title", None)])
    return tmp_path / "official.pot", tmp_path / "translation.po", pot, po


def compare(catalogs: tuple[Path, Path, Catalog, Catalog]) -> dict[str, object]:
    pot_path, po_path, pot, po = catalogs
    write_catalog(pot_path, pot)
    write_catalog(po_path, po)
    return compare_locale_coverage(
        pot_path=pot_path,
        po_path=po_path,
        package_id="dsw:root:2.7.0",
        source_language="en",
        target_language="zh_Hant",
    )


def test_complete_catalog_ignores_reference_separator(catalogs) -> None:
    report = compare(catalogs)
    assert report["status"] == "complete"
    assert report["counts"]["translated"] == 2


def test_removed_message_is_reported_even_when_remaining_po_is_fully_translated(catalogs) -> None:
    catalogs[3].delete("Administrative information")
    report = compare(catalogs)
    assert report["status"] == "incomplete"
    assert report["counts"]["catalog"] == report["counts"]["translated"] == 1
    assert report["counts"]["expected"] == 2
    assert report["missing"][0]["msgid"] == "Administrative information"
    assert "Administrative information" in render_locale_coverage(report)


def test_empty_fuzzy_and_extra_are_distinct(catalogs) -> None:
    po = catalogs[3]
    po.get("Administrative information").string = ""
    po.get("Contributors").flags.add("fuzzy")
    po.add("Removed upstream", "過時")
    report = compare(catalogs)
    assert report["counts"] == {
        "expected": 2,
        "catalog": 3,
        "translated": 0,
        "missing": 0,
        "untranslated": 1,
        "fuzzy": 1,
        "extra": 1,
    }


def test_gettext_context_is_part_of_identity(catalogs) -> None:
    catalogs[2].add("Shared source", context="one")
    catalogs[3].add("Shared source", "共用", context="two")
    report = compare(catalogs)
    assert report["missing"][0]["msgctxt"] == "one"
    assert report["extra"][0]["msgctxt"] == "two"


def test_wrong_package_is_rejected(catalogs) -> None:
    catalogs[2].project = "dsw:root:2.8.0"
    with pytest.raises(LocaleCoverageError, match="configured KM"):
        compare(catalogs)


@pytest.mark.parametrize("index,language", [(2, "de"), (3, "en")])
def test_wrong_language_is_rejected(catalogs, index, language) -> None:
    catalogs[index].locale = language
    with pytest.raises(LocaleCoverageError, match="Language"):
        compare(catalogs)


def test_empty_pot_cannot_claim_complete_coverage(catalogs) -> None:
    catalogs[2].delete("Administrative information")
    catalogs[2].delete("Contributors")
    with pytest.raises(LocaleCoverageError, match="no translatable"):
        compare(catalogs)


def test_failed_download_is_not_a_pot(catalogs) -> None:
    pot_path, po_path, _, po = catalogs
    pot_path.write_text("<?xml version='1.0'?><Error>NoSuchKey</Error>")
    write_catalog(po_path, po)
    with pytest.raises(LocaleCoverageError, match="Invalid gettext"):
        compare_locale_coverage(
            pot_path=pot_path,
            po_path=po_path,
            package_id="dsw:root:2.7.0",
            source_language="en",
            target_language="zh_Hant",
        )
