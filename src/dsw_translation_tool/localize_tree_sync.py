"""Refresh Git translation trees from the current Localize/Weblate PO."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .ci_sync import CiSyncCommitConfig
from .constants import SHARED_BLOCKS_FILENAME
from .workflow import TranslationWorkflowService


@dataclass(frozen=True)
class LocalizeTreeRefreshResult:
    """Summary of a Localize/Weblate-to-tree refresh."""

    version: str
    latest_po_path: Path
    source_km_path: Path
    tree_dir: Path
    outline_path: Path
    shared_blocks_dir: Path
    shared_blocks_outline_path: Path
    folder_count: int
    root_count: int
    shared_block_file_count: int


def refresh_tree_from_localize(
    *,
    config: CiSyncCommitConfig,
    km_version: str,
) -> LocalizeTreeRefreshResult:
    """Rebuild the translation tree from the latest Localize/Weblate PO.

    Localize/Weblate is the source of truth for routine syncs. Re-exporting the
    tree with ``preserve_existing_translations=False`` makes Git a mirror of the
    website translations before downstream artifacts are rebuilt and tested.

    Args:
        config: CI sync configuration with resolved source PO/KM and output
            paths.
        km_version: KM package version represented by the sync.

    Returns:
        Summary of the refreshed tree and generated helper artifacts.

    Raises:
        FileNotFoundError: If the latest Localize PO or source KM is missing.
    """

    latest_po_path = config.original_po_path
    source_km_path = config.original_model_path
    if not latest_po_path.exists():
        raise FileNotFoundError(f"Missing Localize PO snapshot: {latest_po_path}")
    if not source_km_path.exists():
        raise FileNotFoundError(f"Missing source KM bundle: {source_km_path}")

    workflow = TranslationWorkflowService(
        source_lang=config.source_lang,
        target_lang=config.target_lang,
    )
    context = workflow.export_tree(
        po_path=str(latest_po_path),
        model_path=str(source_km_path),
        out_dir=str(config.tree_dir),
        preserve_existing_translations=False,
    )
    manifest = context.manifest or {"nodes": {}, "rootPaths": []}

    outline_result = workflow.build_outline_markdown(
        tree_dir=str(config.tree_dir),
        out_outline_path=str(config.outline_path),
    )
    shared_blocks_result = workflow.build_shared_blocks_directory(
        tree_dir=str(config.tree_dir),
        original_po_path=str(latest_po_path),
        out_shared_blocks_root=str(config.shared_blocks_dir),
    )
    shared_blocks_outline_result = workflow.build_shared_blocks_outline_markdown(
        tree_dir=str(config.tree_dir),
        original_po_path=str(latest_po_path),
        out_shared_blocks_outline_path=str(config.shared_blocks_outline_path),
    )
    _remove_legacy_shared_block_index(config.tree_dir)

    return LocalizeTreeRefreshResult(
        version=km_version,
        latest_po_path=latest_po_path,
        source_km_path=source_km_path,
        tree_dir=config.tree_dir,
        outline_path=outline_result.output_outline,
        shared_blocks_dir=shared_blocks_result.output_shared_blocks_root,
        shared_blocks_outline_path=shared_blocks_outline_result.output_shared_blocks_outline,
        folder_count=len(manifest["nodes"]),
        root_count=len(manifest["rootPaths"]),
        shared_block_file_count=len(shared_blocks_result.written_paths),
    )


def _remove_legacy_shared_block_index(tree_dir: Path) -> None:
    """Remove the obsolete monolithic shared-block markdown file when present."""

    (tree_dir / SHARED_BLOCKS_FILENAME).unlink(missing_ok=True)
