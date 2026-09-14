"""Select and report observable resource-page translations for browser review."""

from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path

from babel.messages.pofile import read_po
from markdown_it import MarkdownIt


def resource_page_candidates(pot_path: Path, po_path: Path) -> dict[str, dict]:
    """Match exact gettext identities against the KM actually loaded by DSW.

    Blank, fuzzy, unchanged and absent translations cannot demonstrate language
    switching. Source-version differences belong in the separate coverage report.
    """
    with pot_path.open(encoding="utf-8") as handle:
        pot = read_po(handle, abort_invalid=True)
    with po_path.open(encoding="utf-8") as handle:
        po = read_po(handle, abort_invalid=True)
    pages: dict[str, dict] = {}
    for message in pot:
        translation = po.get(message.id, context=message.context)
        if not translation or translation.fuzzy or not translation.string:
            continue
        if not isinstance(message.id, str) or not isinstance(translation.string, str):
            continue
        for location, _ in message.locations:
            parts = location.split("/")
            if (
                len(parts) != 3
                or parts[0] != "resourcePage"
                or parts[2] not in {"title", "content"}
            ):
                continue
            field = parts[2]
            original = expected_text(field, message.id)
            translated = expected_text(field, translation.string)
            if original and translated and original != translated:
                pages.setdefault(parts[1], {})[field] = {
                    "source": original,
                    "translation": translated,
                }
    return dict(sorted(pages.items()))


class _TextParser(HTMLParser):
    """Keep block boundaries while ignoring inline presentation differences."""

    blocks = {
        "p",
        "div",
        "li",
        "ul",
        "ol",
        "br",
        "hr",
        "blockquote",
        "pre",
        "table",
        "tr",
        "td",
        "th",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
    }

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in self.blocks:
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in self.blocks:
            self.parts.append(" ")

    def handle_data(self, data):
        self.parts.append(data)


def html_text(html: str) -> str:
    parser = _TextParser()
    parser.feed(html)
    parser.close()
    return " ".join("".join(parser.parts).split())


def expected_text(field: str, value: str) -> str:
    if field == "content":
        return html_text(MarkdownIt("commonmark").render(value))
    return " ".join(value.split())


def compare_resource_field(expected: dict, displayed_html: str) -> dict:
    displayed = html_text(displayed_html)
    if displayed == expected["translation"]:
        status = "translated"
    elif displayed == expected["source"]:
        status = "source"
    else:
        status = "unexpected"
    return {**expected, "displayed": displayed, "status": status}


def summarize_resource_pages(pages: list[dict]) -> dict:
    fields = [field for page in pages for field in page["fields"].values()]
    counts = {
        status: sum(field["status"] == status for field in fields)
        for status in ("translated", "source", "unexpected")
    }
    status = "passed"
    if not fields:
        status = "not-checked"
    elif counts["unexpected"]:
        status = "failed"
    elif counts["source"]:
        status = "incomplete"
    return {
        "status": status,
        "pages_checked": len(pages),
        "fields_checked": len(fields),
        "counts": counts,
        "report": "resource-pages.json",
    }


def render_resource_pages(summary: dict) -> str:
    counts = summary["counts"]
    return (
        f"## Resource-page rendering: {summary['status']}\n\n"
        f"Checked {summary['fields_checked']} translated fields across "
        f"{summary['pages_checked']} standalone resource pages: "
        f"{counts['translated']} displayed the translation, {counts['source']} "
        f"displayed the source, {counts['unexpected']} displayed unexpected text.\n\n"
        "Only non-fuzzy translations with matching source text in the test KM are checked. "
        "This is separate from PO import and questionnaire language switching; "
        "it does not verify every KM field or Markdown formatting. "
        "See `resource-pages.json` and `resource-*.png` in the review artifact.\n\n"
    )
