"""Validate Markdown formatting preserved by translated text."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from markdown_it import MarkdownIt
from markdown_it.token import Token

_MARKDOWN = MarkdownIt("commonmark")
_COUNTED_TOKENS = {
    "blockquote_open": "blockquote",
    "bullet_list_open": "bullet list",
    "code_block": "code block",
    "em_open": "emphasis",
    "fence": "fenced code block",
    "hardbreak": "hard line break",
    "list_item_open": "list item",
    "ordered_list_open": "ordered list",
    "strong_open": "strong emphasis",
}


def compare_markdown_format(source: str, translation: str) -> tuple[str, ...]:
    """Return formatting differences between source and translated Markdown.

    Text and paragraph wrapping may change during translation. Formatting that
    carries structure, an immutable destination, or boundary whitespace must
    remain equivalent.
    """

    source_features = _collect_markdown_features(source)
    translation_features = _collect_markdown_features(translation)
    issues = list(_compare_boundary_whitespace(source, translation))
    for feature in sorted(source_features.keys() | translation_features.keys()):
        source_count = source_features[feature]
        translation_count = translation_features[feature]
        if source_count == translation_count:
            continue
        issues.append(f"{feature}: source has {source_count}, translation has {translation_count}")
    return tuple(issues)


def _compare_boundary_whitespace(source: str, translation: str) -> tuple[str, ...]:
    issues: list[str] = []
    for boundary, source_value, translation_value in (
        ("leading", _leading_whitespace(source), _leading_whitespace(translation)),
        ("trailing", _trailing_whitespace(source), _trailing_whitespace(translation)),
    ):
        if source_value != translation_value:
            issues.append(
                f"{boundary} whitespace: source has {source_value!r}, "
                f"translation has {translation_value!r}"
            )
    return tuple(issues)


def _leading_whitespace(text: str) -> str:
    return text[: len(text) - len(text.lstrip())]


def _trailing_whitespace(text: str) -> str:
    stripped_length = len(text.rstrip())
    return text[stripped_length:]


def _collect_markdown_features(text: str) -> Counter[str]:
    features: Counter[str] = Counter()
    for token in _walk_tokens(_MARKDOWN.parse(text)):
        label = _COUNTED_TOKENS.get(token.type)
        if label is not None:
            features[label] += 1
        elif token.type == "heading_open":
            features[f"{token.tag} heading"] += 1
        elif token.type == "code_inline":
            features[f"inline code `{token.content}`"] += 1
        elif token.type == "link_open":
            features[f"link to `{token.attrGet('href') or ''}`"] += 1
        elif token.type == "image":
            features[f"image `{token.attrGet('src') or ''}`"] += 1
    return features


def _walk_tokens(tokens: Iterable[Token]) -> Iterable[Token]:
    for token in tokens:
        yield token
        if token.children:
            yield from _walk_tokens(token.children)
