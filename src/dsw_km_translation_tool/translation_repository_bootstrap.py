"""Bootstrap a dedicated KM translation repository from tooling templates."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from .km_bundle_sync import BundleDownloader, pull_km_bundle
from .km_registry import KmRegistryError
from .localize_sync import Downloader as LocalizeDownloader
from .localize_sync import pull_localize_po
from .translation_repository_config import (
    load_translation_repository_config,
    version_paths,
)
from .translation_repository_scaffold import render_translation_repository_scaffold
from .workflow import TranslationWorkflowService


class TranslationRepositoryBootstrapError(RuntimeError):
    """Raised when a translation repository cannot be bootstrapped."""


@dataclass(frozen=True)
class TranslationRepositoryBootstrapResult:
    """Summary of one translation repository bootstrap run."""

    repo_root: Path
    config_path: Path
    written_files: tuple[Path, ...]
    skipped_files: tuple[Path, ...]
    hydrated: bool
    km_version: str | None = None
    source_km_path: Path | None = None
    localize_po_path: Path | None = None
    tree_dir: Path | None = None
    final_po_path: Path | None = None
    final_km_path: Path | None = None
    skipped_reason: str | None = None


DEFAULT_CONFIG_TEMPLATE = Path("examples") / "translation-config.yml"


def bootstrap_translation_repository(
    *,
    repo_root: Path,
    tooling_repo: Path,
    config_template_path: Path | None = None,
    registry_token: str = "",
    hydrate: bool = True,
    overwrite: bool = False,
    skip_without_token: bool = False,
    bundle_downloader: BundleDownloader | None = None,
    localize_downloader: LocalizeDownloader | None = None,
) -> TranslationRepositoryBootstrapResult:
    """Create and optionally hydrate a translation repository checkout.

    Args:
        repo_root: Target repository root to create or update.
        tooling_repo: Tooling repository root containing examples and templates.
        config_template_path: Optional ``translation-config.yml`` template.
            Relative paths are resolved inside ``tooling_repo``.
        registry_token: DSW Registry token used to download KM bundles.
        hydrate: Whether to download KM/PO inputs and generate tree/builds.
        overwrite: Whether to overwrite managed scaffold files that already
            exist.
        skip_without_token: Return a scaffold-only result instead of failing
            when hydration needs a Registry token.
        bundle_downloader: Optional injectable KM bundle downloader for tests.
        localize_downloader: Optional injectable Localize/Weblate PO downloader
            for tests.

    Returns:
        Bootstrap result with written files and generated artifact paths.
    """

    tooling_root = tooling_repo.resolve()
    target_root = repo_root.resolve()
    target_root.mkdir(parents=True, exist_ok=True)

    resolved_config_template = _resolve_tooling_path(
        tooling_root,
        config_template_path or DEFAULT_CONFIG_TEMPLATE,
    )
    _require_file(resolved_config_template, "config template")

    written: list[Path] = []
    skipped: list[Path] = []

    config_path = target_root / "translation-config.yml"
    _copy_file(
        source=resolved_config_template,
        target=config_path,
        overwrite=overwrite,
        written=written,
        skipped=skipped,
    )
    config = load_translation_repository_config(config_path)

    for item in render_translation_repository_scaffold(
        tooling_repo=tooling_root,
        config=config,
    ):
        _write_text_file(
            text=item.content,
            target=target_root / item.path,
            overwrite=overwrite,
            written=written,
            skipped=skipped,
        )

    if not hydrate:
        return TranslationRepositoryBootstrapResult(
            repo_root=target_root,
            config_path=config_path,
            written_files=tuple(written),
            skipped_files=tuple(skipped),
            hydrated=False,
        )

    if not registry_token.strip():
        if skip_without_token:
            return TranslationRepositoryBootstrapResult(
                repo_root=target_root,
                config_path=config_path,
                written_files=tuple(written),
                skipped_files=tuple(skipped),
                hydrated=False,
                skipped_reason="missing-registry-token",
            )
        raise TranslationRepositoryBootstrapError(
            "Hydrating a translation repository requires DSW_REGISTRY_TOKEN."
        )

    try:
        return _hydrate_translation_repository(
            repo_root=target_root,
            config_path=config_path,
            registry_token=registry_token,
            written=written,
            skipped=skipped,
            bundle_downloader=bundle_downloader,
            localize_downloader=localize_downloader,
        )
    except (OSError, ValueError, KmRegistryError) as error:
        raise TranslationRepositoryBootstrapError(str(error)) from error


def _hydrate_translation_repository(
    *,
    repo_root: Path,
    config_path: Path,
    registry_token: str,
    written: list[Path],
    skipped: list[Path],
    bundle_downloader: BundleDownloader | None,
    localize_downloader: LocalizeDownloader | None,
) -> TranslationRepositoryBootstrapResult:
    config = load_translation_repository_config(config_path)
    km_version = config.knowledge_model.version
    paths = version_paths(config)

    bundle_result = pull_km_bundle(
        config_path=config_path,
        repo_root=repo_root,
        token=registry_token,
        downloader=bundle_downloader,
    )
    localize_result = pull_localize_po(
        config_path=config_path,
        repo_root=repo_root,
        downloader=localize_downloader,
    )

    workflow = TranslationWorkflowService(
        source_lang=config.translation.source_language,
        target_lang=config.translation.target_language,
    )
    latest_po_path = repo_root / paths.localize_latest_po_path
    source_km_path = repo_root / paths.source_km_path
    tree_dir = repo_root / paths.translation_tree_dir
    final_po_path = repo_root / paths.final_po_path
    final_km_path = repo_root / paths.final_km_path

    workflow.export_tree(
        po_path=str(latest_po_path),
        model_path=str(source_km_path),
        out_dir=str(tree_dir),
        preserve_existing_translations=False,
    )
    workflow.sync_shared_strings(
        tree_dir=str(tree_dir),
        original_po_path=str(latest_po_path),
        out_po_path=str(final_po_path),
        outline_out_path=str(tree_dir / "outline.md"),
        shared_blocks_root_path=str(tree_dir / "shared_blocks"),
        shared_blocks_outline_out_path=str(tree_dir / "shared_blocks_outline.md"),
        group_by="shared-block",
    )
    workflow.review_po_changes(
        original_po_path=str(latest_po_path),
        generated_po_path=str(final_po_path),
        diff_out_path=str(repo_root / paths.review_diff_path),
    )
    workflow.build_km_from_po(
        translated_po_path=str(final_po_path),
        original_model_path=str(source_km_path),
        out_model_path=str(final_km_path),
        output_organization_id=config.translation.translated_organization_id,
        output_km_id=config.translation.translated_km_id,
        output_name=config.translation.translated_name,
    )

    _extend_existing_artifacts(
        written,
        (
            bundle_result.target_path,
            localize_result.latest_po_path,
            tree_dir,
            final_po_path,
            final_km_path,
            repo_root / paths.review_diff_path,
        ),
    )
    return TranslationRepositoryBootstrapResult(
        repo_root=repo_root,
        config_path=config_path,
        written_files=tuple(written),
        skipped_files=tuple(skipped),
        hydrated=True,
        km_version=km_version,
        source_km_path=source_km_path,
        localize_po_path=latest_po_path,
        tree_dir=tree_dir,
        final_po_path=final_po_path,
        final_km_path=final_km_path,
    )


def _copy_file(
    *,
    source: Path,
    target: Path,
    overwrite: bool,
    written: list[Path],
    skipped: list[Path],
) -> None:
    if source.resolve() == target.resolve():
        skipped.append(target)
        return
    if target.exists() and not overwrite:
        skipped.append(target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    written.append(target)


def _write_text_file(
    *,
    text: str,
    target: Path,
    overwrite: bool,
    written: list[Path],
    skipped: list[Path],
) -> None:
    if target.exists() and not overwrite:
        skipped.append(target)
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    written.append(target)


def _extend_existing_artifacts(written: list[Path], paths: tuple[Path, ...]) -> None:
    for path in paths:
        if path.exists():
            written.append(path)


def _resolve_tooling_path(tooling_root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (tooling_root / path).resolve()


def _require_file(path: Path, label: str) -> None:
    if not path.is_file():
        raise TranslationRepositoryBootstrapError(f"Missing {label}: {path}")
