"""Rebuild a native locale from the checked-in KM, Weblate PO, and Markdown."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .native_locale import validate_native_locale
from .translation_repository_config import (
    load_translation_repository_config,
    version_paths,
)
from .translation_repository_shared_sync import sync_translation_repository_shared_strings
from .workflow import TranslationWorkflowService


class TranslationRepositoryBuildError(RuntimeError):
    """Raised when a Git-managed translation repository cannot be rebuilt."""


@dataclass(frozen=True)
class TranslationRepositoryBuildResult:
    """Summary of one repository rebuild."""

    source_km_path: Path
    source_po_path: Path
    tree_dir: Path
    final_po_path: Path


def build_translation_repository(
    *,
    repo_root: Path,
    config_path: Path = Path("translation-config.yml"),
    preserve_existing_translations: bool = True,
) -> TranslationRepositoryBuildResult:
    """Rebuild the tree and native DSW locale PO from Git-managed inputs.

    ``preserve_existing_translations`` is intended for ordinary tree-to-output
    rebuilds. Source synchronization must disable it after carrying exact
    source matches into the catalog, otherwise stale tree text could survive a
    changed source string.
    """

    root = repo_root.resolve()
    resolved_config = config_path if config_path.is_absolute() else root / config_path
    config = load_translation_repository_config(resolved_config)
    paths = version_paths(config)
    source_km = root / paths.source_km_path
    source_po = root / paths.source_po_path
    tree_dir = root / paths.translation_tree_dir
    final_po = root / paths.final_po_path

    existing_inputs = (source_km.is_file(), source_po.is_file())
    if not all(existing_inputs):
        missing = source_km if not source_km.is_file() else source_po
        raise TranslationRepositoryBuildError(
            f"Translation repository is partially initialized; missing {missing}"
        )

    workflow = TranslationWorkflowService(
        source_lang=config.translation.source_language,
        target_lang=config.translation.target_language,
    )
    validate_native_locale(
        po_path=source_po,
        km_path=source_km,
        target_language=config.translation.target_language,
    )
    if preserve_existing_translations and (tree_dir / "shared_blocks").is_dir():
        sync_translation_repository_shared_strings(repo_root=root, config_path=config_path)
    context = workflow.export_tree(
        po_path=str(source_po),
        model_path=str(source_km),
        out_dir=str(tree_dir),
        preserve_existing_translations=preserve_existing_translations,
    )
    workflow.write_report(
        report=context.report,
        report_path=str(root / paths.validation_report_path),
    )
    workflow.build_shared_blocks_directory(
        tree_dir=str(tree_dir),
        original_po_path=str(source_po),
        out_shared_blocks_root=str(tree_dir / "shared_blocks"),
    )
    workflow.sync_shared_strings(
        tree_dir=str(tree_dir),
        original_po_path=str(source_po),
        out_po_path=str(final_po),
        outline_out_path=str(tree_dir / "outline.md"),
        shared_blocks_root_path=str(tree_dir / "shared_blocks"),
        shared_blocks_outline_out_path=str(tree_dir / "shared_blocks_outline.md"),
        group_by="shared-block",
    )
    workflow.review_po_changes(
        original_po_path=str(source_po),
        generated_po_path=str(final_po),
        diff_out_path=str(root / paths.review_diff_path),
    )
    validate_native_locale(
        po_path=final_po,
        km_path=source_km,
        target_language=config.translation.target_language,
    )
    return TranslationRepositoryBuildResult(
        source_km_path=source_km,
        source_po_path=source_po,
        tree_dir=tree_dir,
        final_po_path=final_po,
    )
