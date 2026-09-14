"""Validation for PO files imported as native DSW knowledge-model locales."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .data_models import PoBlock
from .knowledge_model_service import KnowledgeModelService
from .po_support.parser import PoCatalogError, PoCatalogParser


class NativeLocaleValidationError(ValueError):
    """Raised when a PO cannot be used as the configured DSW locale."""


@dataclass(frozen=True)
class NativeLocaleValidationResult:
    """Catalog validation plus an informational comparison with the context KM."""

    po_path: Path
    km_path: Path
    target_language: str
    catalog_language: str
    total_messages: int
    translated_messages: int
    model_report: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        payload = asdict(self)
        payload["po_path"] = str(self.po_path)
        payload["km_path"] = str(self.km_path)
        return payload


def validate_native_locale(
    *,
    po_path: Path,
    km_path: Path,
    target_language: str,
) -> NativeLocaleValidationResult:
    """Validate a gettext catalog for DSW's native KM-locale import flow."""

    resolved_po = po_path.resolve()
    resolved_km = km_path.resolve()
    try:
        catalog, blocks = PoCatalogParser.parse_catalog(
            resolved_po.read_text(encoding="utf-8"), target_language=target_language
        )
    except PoCatalogError as error:
        raise NativeLocaleValidationError(str(error)) from error
    report = validate_locale_blocks(blocks=blocks, km_path=resolved_km)

    messages = [message for message in catalog if message.id]
    return NativeLocaleValidationResult(
        po_path=resolved_po,
        km_path=resolved_km,
        target_language=target_language,
        catalog_language=catalog.locale_identifier,
        total_messages=len(messages),
        translated_messages=sum(bool(message.string) and not message.fuzzy for message in messages),
        model_report=report,
    )


def validate_locale_blocks(*, blocks: list[PoBlock], km_path: Path) -> dict[str, Any]:
    """Report source differences; DSW imports do not require matching KM fields."""
    entries = PoCatalogParser.entries_from_blocks(blocks)
    latest_by_uuid, _ = KnowledgeModelService.load_model(str(km_path))
    return KnowledgeModelService.validate_po_entries(entries, latest_by_uuid)
