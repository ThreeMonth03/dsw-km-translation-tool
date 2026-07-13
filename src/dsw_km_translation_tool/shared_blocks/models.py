"""Data contracts used by shared-block parsing and rendering."""

from __future__ import annotations

from dataclasses import dataclass

from ..data_models import PoReference


@dataclass(frozen=True)
class SharedBlockContext:
    """One linked tree context rendered for a shared translation."""

    reference: PoReference
    badge: str
    label: str
    relative_link: str
    context_label: str


@dataclass(frozen=True)
class SharedBlockRecord:
    """One shared PO block and its linked tree contexts."""

    group_key: tuple[tuple[str, str], ...]
    source_text: str
    translation_text: str
    contexts: tuple[SharedBlockContext, ...]
    stable_id: str

    @property
    def is_translated(self) -> bool:
        """Return whether the shared block currently has a translation."""

        return bool(self.translation_text.strip())

    @property
    def field_names(self) -> tuple[str, ...]:
        """Return sorted field names represented by the shared block."""

        return tuple(
            sorted(
                {context.reference.field for context in self.contexts},
                key=str.casefold,
            )
        )
