"""Protect Git translations until the reviewed Weblate import has succeeded."""

from __future__ import annotations

from pathlib import Path

from .constants import TRANSLATION_FILENAME, UUID_FILENAME
from .path_safety import reject_symlink_path
from .po import PoCatalogParser
from .shared_blocks.parser import SharedBlocksCatalogParser
from .translation_repository_config import TranslationRepositoryConfig, version_paths
from .tree_support.document import TranslationMarkdownDocument


def ensure_no_pending_translations(
    *, repo_root: Path, config: TranslationRepositoryConfig, downloaded: bytes
) -> None:
    """Check editable files against the saved snapshot and incoming Weblate PO.

    Upstream changes are authoritative when Git still matches the saved PO.
    A Git edit may be replaced only once Weblate contains that edit. Read files
    directly: validation must not restore backups or modify translator inputs.
    """
    paths = version_paths(config)
    tree = repo_root / paths.translation_tree_dir
    reject_symlink_path(tree, repo_root)
    if not tree.exists():
        return  # Initial downloads and temporary report snapshots have no tree.
    source = repo_root / paths.source_po_path
    reject_symlink_path(source, repo_root)
    previous_blocks = PoCatalogParser(str(source)).parse_blocks()
    previous = {
        (entry.uuid, entry.field): (entry.msgid, entry.msgstr)
        for entry in PoCatalogParser.entries_from_blocks(previous_blocks)
    }
    incoming = {
        (entry.uuid, entry.field): (entry.msgid, entry.msgstr)
        for entry in PoCatalogParser.entries_from_blocks(
            PoCatalogParser.parse_text(downloaded.decode("utf-8"))
        )
    }
    document = TranslationMarkdownDocument(
        source_lang=config.translation.source_language,
        target_lang=config.translation.target_language,
    )
    current: dict[tuple[str, str], tuple[str, str]] = {}
    for path in sorted(tree.rglob(TRANSLATION_FILENAME)):
        reject_symlink_path(path, repo_root)
        uuid_path = path.with_name(UUID_FILENAME)
        reject_symlink_path(uuid_path, repo_root)
        entity_uuid = uuid_path.read_text(encoding="utf-8").strip()
        for field, state in document.parse(str(path)).items():
            key = (entity_uuid, field)
            if key in current:
                raise ValueError(f"Duplicate translation field: {entity_uuid}:{field}")
            current[key] = (state.source_text, state.target_text)

    pending = {
        key
        for key in previous.keys() | current.keys()
        if current.get(key) != previous.get(key) and current.get(key) != incoming.get(key)
    }
    parser = SharedBlocksCatalogParser(target_lang=config.translation.target_language)
    for block in previous_blocks:
        if len(block.references) < 2:
            continue
        group = tuple((ref.uuid, ref.field) for ref in block.references)
        path = parser.group_context_path(tree / "shared_blocks", group)
        reject_symlink_path(path, repo_root)
        parsed_group, target = parser.parse_document(
            path.read_text(encoding="utf-8"), source=str(path)
        )
        if parsed_group != group:
            raise ValueError(f"Shared-block key metadata changed: {path}")
        if target != block.msgstr:
            pending.update(key for key in group if incoming.get(key) != (block.msgid, target))
    if pending:
        keys = ", ".join(f"{uuid}:{field}" for uuid, field in sorted(pending)[:10])
        raise ValueError(
            f"Refusing to replace {len(pending)} Git translation fields not yet in Weblate: {keys}. "
            "Complete or retry GitHub Translation Import, or resolve its conflict report first. "
            "No source snapshot or translation files were changed."
        )
