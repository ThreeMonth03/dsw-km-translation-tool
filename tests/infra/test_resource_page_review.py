"""Resource-page reports must not confuse an importable PO with translated UI."""

from pathlib import Path

import pytest
from babel.messages.catalog import Catalog
from babel.messages.pofile import write_po

from dsw_km_translation_tool.resource_page_review import (
    compare_resource_field,
    expected_text,
    html_text,
    render_resource_pages,
    resource_page_candidates,
    summarize_resource_pages,
)


def test_candidates_use_official_locations_and_exact_gettext_identity(tmp_path: Path):
    pot, po = Catalog(), Catalog(locale="zh_Hant")
    pot.add("Title", locations=[("question/q/title", None), ("resourcePage/page/title", None)])
    po.add("Title", "標題", locations=[("entity/different/title", None)])
    pot.add("Body", context="help", locations=[("resourcePage/page/content", None)])
    po.add("Body", "錯誤的 context")
    po.add("Body", "**內文**", context="help")
    for name, translation, flags in (
        ("Empty", "", ()),
        ("Fuzzy", "模糊", ("fuzzy",)),
        ("Unchanged", "Unchanged", ()),
        ("Missing", None, ()),
        ("Formatting", "**Formatting**", ()),
    ):
        pot.add(name, locations=[(f"resourcePage/{name}/content", None)])
        if translation is not None:
            po.add(name, translation, flags=flags)
    po.add("New source", "新字串", locations=[("resourcePage/absent/title", None)])
    for path, catalog in ((tmp_path / "km.pot", pot), (tmp_path / "locale.po", po)):
        with path.open("wb") as handle:
            write_po(handle, catalog)
    assert resource_page_candidates(tmp_path / "km.pot", tmp_path / "locale.po") == {
        "page": {
            "title": {"source": "Title", "translation": "標題"},
            "content": {"source": "Body", "translation": "內文"},
        }
    }


def test_markdown_comparison_preserves_inline_spacing_and_block_boundaries():
    markdown = "**後設資料**與[詞彙](https://example.com)。\n\n- A & B\n- `識別碼`"
    html = '<div><p><strong>後設資料</strong>與<a href="/other">詞彙</a>。</p><ul><li>A &amp; B</li><li><code>識別碼</code></li></ul></div>'
    assert expected_text("content", markdown) == html_text(html) == "後設資料與詞彙。 A & B 識別碼"
    assert expected_text("title", "A < B & C") == html_text("A &lt; B &amp; C")


@pytest.mark.parametrize(
    "html,status",
    [
        ("<p>譯文</p>", "translated"),
        ("Source", "source"),
        ("", "unexpected"),
        ("Error", "unexpected"),
    ],
)
def test_source_fallback_is_distinct_from_unexpected_rendering(html, status):
    assert (
        compare_resource_field({"source": "Source", "translation": "譯文"}, html)["status"]
        == status
    )


@pytest.mark.parametrize(
    "statuses,outcome",
    [
        ([], "not-checked"),
        (["translated"], "passed"),
        (["translated", "source"], "incomplete"),
        (["source", "unexpected"], "failed"),
    ],
)
def test_summary_never_calls_unchecked_or_source_only_pages_passed(statuses, outcome):
    pages = [{"fields": {"title": {"status": status}}} for status in statuses]
    summary = summarize_resource_pages(pages)
    assert summary["status"] == outcome
    assert summary["pages_checked"] == len(pages)
    assert summary["fields_checked"] == len(statuses)
    assert sum(summary["counts"].values()) == len(statuses)
    assert "fields" not in summary
    assert outcome in render_resource_pages(summary)
    assert "separate from PO import" in render_resource_pages(summary)
