"""Read PO source and translation state by DSW field reference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ..po import PoCatalogParser

PoKey = tuple[str, str]


@dataclass(frozen=True)
class PoEntryState:
    """Source and target state for one referenced PO entry."""

    msgid: str
    msgstr: str
    is_fuzzy: bool


def parse_po_entry_states(po_path: str | Path) -> dict[PoKey, PoEntryState]:
    """Parse a PO file into entry states keyed by ``(uuid, field)``."""

    states: dict[PoKey, PoEntryState] = {}
    for block in PoCatalogParser(str(po_path)).parse_blocks():
        state = PoEntryState(
            msgid=block.msgid,
            msgstr=block.msgstr,
            is_fuzzy=block.is_fuzzy,
        )
        for reference in block.references:
            key = (reference.uuid, reference.field)
            existing = states.get(key)
            if existing is not None and existing != state:
                raise ValueError(
                    f"Duplicate PO key with conflicting values: {reference.uuid}:{reference.field}"
                )
            states[key] = state
    return states
