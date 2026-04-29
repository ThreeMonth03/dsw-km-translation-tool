"""Workflow result models used by the translation tooling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .knowledge_model import ModelInfo, TreeNode
from .po import PoEntry
from .tree import TreeValidationResult


@dataclass(frozen=True)
class WorkflowContext:
    """In-memory context needed for export and validation workflows.

    Args:
        report: PO-versus-KM validation report.
        model_info: Metadata of the loaded model.
        roots: Translation tree roots.
        entries: Flattened PO entries.
        latest_by_uuid: Latest merged KM entities keyed by UUID.
        manifest: Exported manifest when a tree was written to disk.
        shared_reference_keys: `(uuid, field)` keys that belong to a shared
            PO block and should be edited via `tree/shared_blocks/`.
    """

    report: dict[str, Any]
    model_info: ModelInfo
    roots: list[TreeNode]
    entries: list[PoEntry]
    latest_by_uuid: dict[str, dict[str, Any]]
    manifest: dict[str, Any] | None = None
    shared_reference_keys: frozenset[tuple[str, str]] = frozenset()

    @property
    def model_metadata(self) -> dict[str, str | None]:
        """Return model metadata in a JSON-friendly dictionary form."""

        return {
            "id": self.model_info.id,
            "kmId": self.model_info.km_id,
            "name": self.model_info.name,
        }


@dataclass(frozen=True)
class PoBuildResult:
    """Result of rebuilding a PO file from the translation tree.

    Args:
        po_content: Generated PO text.
        translations: `(uuid, field)` translation mapping used for the build.
        validation: Validation result of the input tree.
        output_po: Generated PO file path.
    """

    po_content: str
    translations: dict[tuple[str, str], str]
    validation: TreeValidationResult
    output_po: Path


@dataclass(frozen=True)
class KmBuildResult:
    """Result of rebuilding a KM file from a translated PO file.

    Args:
        km_content: Generated KM JSON text.
        translations: Applied non-empty `(uuid, field)` translations.
        total_entries: Total flattened PO entry count scanned from the PO file.
        translated_entries: Number of entries whose non-empty `msgstr` was
            applied to the KM output.
        preserved_entries: Number of entries that kept the original KM source
            text because the PO `msgstr` was empty.
        output_km: Generated KM file path.
        output_package_id: Generated top-level package bundle ID.
        output_organization_id: Generated organization ID.
        output_km_id: Generated KM ID.
        output_name: Generated display name.
    """

    km_content: str
    translations: dict[tuple[str, str], str]
    total_entries: int
    translated_entries: int
    preserved_entries: int
    output_km: Path
    output_package_id: str | None = None
    output_organization_id: str | None = None
    output_km_id: str | None = None
    output_name: str | None = None
