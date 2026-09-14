"""Keep exact PO field validation separate from display-name selection."""

from __future__ import annotations

import pytest

from dsw_km_translation_tool.knowledge_model_support.display import KnowledgeModelTextResolver


@pytest.mark.parametrize(
    "content,field,expected",
    [
        ({"title": "Research project"}, "name", None),
        ({"name": None, "title": "Research project"}, "name", None),
        ({"text": "Description"}, "description", None),
        ({"advice": None, "label": "Advice"}, "advice", None),
        ({"name": "", "title": "Research project"}, "name", ""),
        ({"name": "Source name", "title": "Other title"}, "name", "Source name"),
        ({"title": "Source\u2028 title\u2029"}, "title", "Source title"),
        ({}, "title", None),
    ],
)
def test_source_text_uses_only_the_requested_field(content, field, expected):
    resolver = KnowledgeModelTextResolver()

    assert resolver.get_event_text_value({"content": content}, field) == expected


def test_missing_entity_has_no_source_text():
    assert KnowledgeModelTextResolver().get_event_text_value(None, "title") is None


def test_display_label_can_still_use_an_available_title():
    resolver = KnowledgeModelTextResolver()
    entities = {"entity": {"content": {"title": "Research project"}}}

    label, source = resolver.resolve_node_display_name("entity", entities)

    assert label == "Research project"
    assert source == {"sourceUuid": "entity", "field": "title", "relation": "self"}
