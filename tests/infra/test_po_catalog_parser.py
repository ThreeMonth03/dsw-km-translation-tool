"""Native references must be complete, not silently filtered to an empty tree."""

from pathlib import Path

import pytest

from dsw_km_translation_tool.localize_status import build_localize_po_status_report
from dsw_km_translation_tool.po_support.parser import PoCatalogError, PoCatalogParser

UUID = "123e4567-e89b-12d3-a456-426614174000"
HEADER = 'msgid ""\nmsgstr ""\n"Language: zh_Hant\\n"\n\n'


def test_native_references_and_unicode_survive_parsing() -> None:
    source = "A source containing a Unicode separator\u2028and another line\\n"
    text = HEADER + (
        f"#: question/{UUID}/title\n#: phase/{UUID}/description\n"
        f'#, fuzzy\nmsgid "{source}"\nmsgstr "需要檢查"\n'
    )
    blocks = PoCatalogParser.parse_text(text, target_language="zh_Hant")
    assert len(blocks) == 1
    assert blocks[0].msgid == source.replace("\\n", "\n")
    assert blocks[0].msgstr == "需要檢查"
    assert blocks[0].is_fuzzy
    assert [r.prefix for r in blocks[0].references] == ["question", "phase"]


@pytest.mark.parametrize(
    "text",
    [
        "",
        HEADER,
        "<html>Service unavailable</html>",
        HEADER + 'msgid "Unmapped"\nmsgstr "未對應"\n',
        HEADER + f'#: question:{UUID}/title\nmsgid "Mixed separator"\nmsgstr ""\n',
        HEADER + f'#: question/{UUID}/title\n#: invalid\nmsgid "Mixed"\nmsgstr ""\n',
        HEADER + '#: question/not-a-uuid/title\nmsgid "Invalid"\nmsgstr ""\n',
    ],
)
def test_unusable_catalogs_fail_parsing_and_status(tmp_path: Path, text: str) -> None:
    path = tmp_path / "invalid.po"
    path.write_text(text, encoding="utf-8")
    with pytest.raises(PoCatalogError):
        PoCatalogParser(str(path)).parse_blocks()
    with pytest.raises(PoCatalogError):
        build_localize_po_status_report(path)


def test_split_shared_messages_remain_independent() -> None:
    text = HEADER + (
        f'#: question/{UUID}/title\nmsgid "Shared"\nmsgstr "第一個"\n\n'
        f'#: phase/{UUID}/title\nmsgid "Shared"\nmsgstr "第二個"\n'
    )
    assert [b.msgstr for b in PoCatalogParser.parse_text(text)] == ["第一個", "第二個"]


def test_windows_newlines_do_not_change_message_content() -> None:
    text = HEADER + f'#: question/{UUID}/title\nmsgid "Question"\nmsgstr "問題"\n'
    assert PoCatalogParser.parse_text(text.replace("\n", "\r\n")) == PoCatalogParser.parse_text(
        text
    )


@pytest.mark.parametrize("separator", [":", "/"])
def test_existing_and_native_reference_tokens_are_preserved(separator: str):
    reference = separator.join(("question", UUID, "title"))
    blocks = PoCatalogParser.parse_text(HEADER + f'#: {reference}\nmsgid "Source"\nmsgstr "譯文"\n')
    assert blocks[0].references[0].comment == reference
    assert blocks[0].references[0].uuid == UUID
    assert blocks[0].references[0].field == "title"
