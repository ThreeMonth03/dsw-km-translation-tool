"""Validation for PO files imported as native DSW knowledge-model locales."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from babel.messages.pofile import PoFileError, read_po

from .workflow import TranslationWorkflowService


class NativeLocaleValidationError(ValueError):
    """Raised when a PO cannot be used as the configured DSW locale."""


@dataclass(frozen=True)
class NativeLocaleValidationResult:
    """Summary of native locale syntax and KM-reference validation."""

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
        with resolved_po.open(encoding="utf-8") as handle:
            catalog = read_po(handle, abort_invalid=True)
    except PoFileError as error:
        raise NativeLocaleValidationError(f"Invalid gettext catalog: {error}") from error

    catalog_language = catalog.locale_identifier
    if catalog_language != target_language:
        raise NativeLocaleValidationError(
            "PO Language header does not match translation-config.yml: "
            f"expected {target_language!r}, got {catalog_language!r}"
        )

    workflow = TranslationWorkflowService(target_lang=target_language)
    report = workflow.validate_po_against_model(
        po_path=str(resolved_po),
        model_path=str(resolved_km),
    )
    if _has_model_errors(report):
        preview = "\n".join(_format_model_errors(report)[:50])
        raise NativeLocaleValidationError(f"PO validation against KM failed:\n{preview}")

    messages = [message for message in catalog if message.id]
    return NativeLocaleValidationResult(
        po_path=resolved_po,
        km_path=resolved_km,
        target_language=target_language,
        catalog_language=catalog_language,
        total_messages=len(messages),
        translated_messages=sum(bool(message.string) for message in messages),
        model_report=report,
    )


def _has_model_errors(report: dict[str, Any]) -> bool:
    return any(report.get(key, 0) for key in ("missingEntities", "missingFields", "mismatches"))


def _format_model_errors(report: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for detail in report.get("missingEntitiesDetails", ()):
        errors.append(f"Missing entity: {detail['uuid']}:{detail['field']}")
    for detail in report.get("missingFieldsDetails", ()):
        errors.append(f"Missing field: {detail['uuid']}:{detail['field']}")
    for detail in report.get("mismatchesDetails", ()):
        errors.append(
            "Source mismatch: "
            f"{detail['uuid']}:{detail['field']} "
            f"PO msgid={detail['msgid']!r} KM={detail['actual']!r}"
        )
    return errors or ["Unknown validation error."]
