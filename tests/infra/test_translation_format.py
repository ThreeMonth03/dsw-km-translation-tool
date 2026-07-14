"""Tests for translated Markdown format validation."""

from dsw_km_translation_tool.translation_format import compare_markdown_format


def test_equivalent_translated_markdown_is_valid() -> None:
    source = "See *the **processor** definition* in [Article 4](https://example.test/4)."
    translation = "請參閱[第 4 條](https://example.test/4)中的「*以**資料處理者**為核心的定義*」。"

    assert compare_markdown_format(source, translation) == ()


def test_broken_nested_emphasis_reports_missing_structure() -> None:
    source = "*The **processor** definition.*"
    translation = "*「**「資料處理者」**是指……。」*"

    assert compare_markdown_format(source, translation) == (
        "strong emphasis: source has 1, translation has 0",
    )


def test_changed_link_destination_is_invalid() -> None:
    source = "[Article 4](https://example.test/4)"
    translation = "[第 4 條](https://example.test/wrong)"

    assert compare_markdown_format(source, translation) == (
        "link to `https://example.test/4`: source has 1, translation has 0",
        "link to `https://example.test/wrong`: source has 0, translation has 1",
    )


def test_boundary_whitespace_must_match_source() -> None:
    source = " Source title\u2028"
    translation = "翻譯"

    assert compare_markdown_format(source, translation) == (
        "leading whitespace: source has ' ', translation has ''",
        "trailing whitespace: source has '\\u2028', translation has ''",
    )
