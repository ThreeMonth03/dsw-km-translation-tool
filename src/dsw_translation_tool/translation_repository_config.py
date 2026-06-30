"""Configuration helpers for versioned KM translation repositories."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class TranslationRepositoryConfigError(ValueError):
    """Raised when a translation repository config is invalid."""


@dataclass(frozen=True)
class KnowledgeModelRepositoryConfig:
    """Source KM coordinates and supported package-version policy."""

    organization_id: str
    km_id: str
    upstream_repository: str
    bundle_path: Path | None
    supported_versions: tuple[str, ...]


@dataclass(frozen=True)
class TranslationLanguageConfig:
    """Target-language metadata for translated KM packages."""

    source_language: str
    target_language: str
    target_language_label: str
    translated_organization_id: str
    translated_km_id: str
    translated_name: str


@dataclass(frozen=True)
class BranchConfig:
    """Version branch naming policy."""

    version_branch_prefix: str


@dataclass(frozen=True)
class ToolingConfig:
    """Tooling repository reference used by downstream automation."""

    repository: str
    ref: str


@dataclass(frozen=True)
class LocalizeConfig:
    """Localize/Weblate source metadata for PO synchronization."""

    download_url: str
    repository: str | None


@dataclass(frozen=True)
class RegistryConfig:
    """DSW Registry endpoint used for KM version discovery."""

    api_url: str


@dataclass(frozen=True)
class MigrationConfig:
    """Cross-version and Localize merge policy."""

    mode: str
    non_exact_policy: str
    protected_chapters: tuple[str, ...]


@dataclass(frozen=True)
class KmVersionWorkspacePaths:
    """Conventional paths for one KM translation version branch."""

    version: str
    package_id: str
    source_slug: str
    source_km_path: Path
    localize_base_po_path: Path
    localize_latest_po_path: Path
    translation_tree_dir: Path
    final_po_path: Path
    final_km_path: Path
    review_diff_path: Path
    validation_report_path: Path
    localize_merge_report_path: Path
    conflicts_report_path: Path


@dataclass(frozen=True)
class TranslationRepositoryConfig:
    """Parsed translation repository configuration."""

    schema_version: int
    knowledge_model: KnowledgeModelRepositoryConfig
    translation: TranslationLanguageConfig
    branches: BranchConfig
    tooling: ToolingConfig
    localize: LocalizeConfig
    registry: RegistryConfig
    migration: MigrationConfig


VERSION_RE = re.compile(r"^v?(?P<number>\d+(?:\.\d+){1,3})$")
DEFAULT_REGISTRY_API_URL = "https://api.registry.ds-wizard.org"


def load_translation_repository_config(path: str | Path) -> TranslationRepositoryConfig:
    """Load and validate a versioned KM translation repository config.

    Args:
        path: Path to ``translation-config.yml``.

    Returns:
        Parsed config with normalized bare semantic versions such as ``2.7.0``.
    """

    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TranslationRepositoryConfigError("translation-config.yml must contain a mapping")

    schema_version = _optional_int(payload, "schema_version", default=1)
    if schema_version != 1:
        raise TranslationRepositoryConfigError(
            f"Unsupported translation-config.yml schema_version {schema_version!r}"
        )

    knowledge_model = _load_knowledge_model_config(_require_dict(payload, "knowledge_model"))
    translation = _load_translation_config(_require_dict(payload, "translation"))
    branches = BranchConfig(
        version_branch_prefix=_require_str(
            _require_dict(payload, "branches"), "version_branch_prefix"
        )
    )
    tooling = ToolingConfig(
        repository=_require_str(_require_dict(payload, "tooling"), "repository"),
        ref=_require_str(_require_dict(payload, "tooling"), "ref"),
    )
    localize = _load_localize_config(_require_dict(payload, "localize"))
    registry = _load_registry_config(_optional_dict(payload, "registry"))
    migration = _load_migration_config(_require_dict(payload, "migration"))

    return TranslationRepositoryConfig(
        schema_version=schema_version,
        knowledge_model=knowledge_model,
        translation=translation,
        branches=branches,
        tooling=tooling,
        localize=localize,
        registry=registry,
        migration=migration,
    )


def _load_knowledge_model_config(payload: dict[str, Any]) -> KnowledgeModelRepositoryConfig:
    versions = tuple(sorted_versions(_required_str_list(payload, "supported_versions")))
    if not versions:
        raise TranslationRepositoryConfigError(
            "knowledge_model.supported_versions must not be empty"
        )
    duplicates = _duplicates(versions)
    if duplicates:
        raise TranslationRepositoryConfigError(
            "knowledge_model.supported_versions contains duplicate versions: "
            + ", ".join(duplicates)
        )
    bundle_path_raw = _optional_str(payload, "bundle_path")
    return KnowledgeModelRepositoryConfig(
        organization_id=_require_str(payload, "organization_id"),
        km_id=_require_str(payload, "km_id"),
        upstream_repository=_require_str(payload, "upstream_repository"),
        bundle_path=Path(bundle_path_raw) if bundle_path_raw else None,
        supported_versions=versions,
    )


def _load_translation_config(payload: dict[str, Any]) -> TranslationLanguageConfig:
    return TranslationLanguageConfig(
        source_language=_require_str(payload, "source_language"),
        target_language=_require_str(payload, "target_language"),
        target_language_label=_require_str(payload, "target_language_label"),
        translated_organization_id=_require_str(payload, "translated_organization_id"),
        translated_km_id=_require_str(payload, "translated_km_id"),
        translated_name=_require_str(payload, "translated_name"),
    )


def _load_localize_config(payload: dict[str, Any]) -> LocalizeConfig:
    return LocalizeConfig(
        download_url=_require_str(payload, "download_url"),
        repository=_optional_str(payload, "repository"),
    )


def _load_registry_config(payload: dict[str, Any]) -> RegistryConfig:
    return RegistryConfig(
        api_url=_optional_str(payload, "api_url") or DEFAULT_REGISTRY_API_URL,
    )


def _load_migration_config(payload: dict[str, Any]) -> MigrationConfig:
    mode = _require_str(payload, "mode")
    if mode != "exact-only":
        raise TranslationRepositoryConfigError("Only migration.mode=exact-only is supported")
    non_exact_policy = _require_str(payload, "non_exact_policy")
    if non_exact_policy != "leave_empty_needs_translation":
        raise TranslationRepositoryConfigError(
            "Only migration.non_exact_policy=leave_empty_needs_translation is supported"
        )
    return MigrationConfig(
        mode=mode,
        non_exact_policy=non_exact_policy,
        protected_chapters=tuple(_optional_str_list(payload, "protected_chapters")),
    )


def version_branch(config: TranslationRepositoryConfig, version: str) -> str:
    """Return the configured translation branch name for one KM version."""

    normalized = normalize_version(version)
    validate_supported_version(config, normalized)
    return f"{config.branches.version_branch_prefix}{normalized}"


def version_paths(config: TranslationRepositoryConfig, version: str) -> KmVersionWorkspacePaths:
    """Return conventional workspace paths for one KM version branch."""

    normalized = normalize_version(version)
    validate_supported_version(config, normalized)
    package_id = format_package_id(
        organization_id=config.knowledge_model.organization_id,
        km_id=config.knowledge_model.km_id,
        version=normalized,
    )
    source_slug = (
        f"{config.knowledge_model.organization_id}-{config.knowledge_model.km_id}-{normalized}"
    )
    target_lang = config.translation.target_language
    return KmVersionWorkspacePaths(
        version=normalized,
        package_id=package_id,
        source_slug=source_slug,
        source_km_path=Path("sources") / "knowledge-models" / source_slug / f"{source_slug}.km",
        localize_base_po_path=Path("sources") / "localize" / target_lang / "base.po",
        localize_latest_po_path=Path("sources") / "localize" / target_lang / "latest.po",
        translation_tree_dir=Path("tree"),
        final_po_path=Path("builds") / "final_translated.po",
        final_km_path=Path("builds") / "final_translated.km",
        review_diff_path=Path("reviews") / "final_translated.diff",
        validation_report_path=Path("reports") / "final_report.json",
        localize_merge_report_path=Path("reviews") / "localize_merge_report.json",
        conflicts_report_path=Path("reviews") / "conflicts.json",
    )


def validate_supported_version(config: TranslationRepositoryConfig, version: str) -> None:
    """Raise if ``version`` is not configured as supported."""

    normalized = normalize_version(version)
    if normalized not in config.knowledge_model.supported_versions:
        raise TranslationRepositoryConfigError(f"Unsupported KM version: {version}")


def sorted_versions(versions: list[str] | tuple[str, ...]) -> list[str]:
    """Return normalized KM versions sorted by semantic-version order."""

    return sorted((normalize_version(version) for version in versions), key=version_sort_key)


def normalize_version(version: str) -> str:
    """Normalize a KM version to a bare semantic version string."""

    match = VERSION_RE.fullmatch(version.strip())
    if not match:
        raise TranslationRepositoryConfigError(f"Invalid semantic version: {version!r}")
    return match.group("number")


def version_sort_key(version: str) -> tuple[int, ...]:
    """Return a semantic-version sort key."""

    normalized = normalize_version(version)
    return tuple(int(part) for part in normalized.split("."))


def format_package_id(organization_id: str, km_id: str, version: str) -> str:
    """Format a DSW knowledge-model package ID."""

    return f"{organization_id}:{km_id}:{normalize_version(version)}"


def _require_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise TranslationRepositoryConfigError(f"Expected mapping at `{key}`")
    return value


def _optional_dict(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key, {})
    if not isinstance(value, dict):
        raise TranslationRepositoryConfigError(f"Expected mapping at `{key}`")
    return value


def _require_str(parent: dict[str, Any], key: str) -> str:
    value = parent.get(key)
    if not isinstance(value, str) or not value.strip():
        raise TranslationRepositoryConfigError(f"Expected non-empty string at `{key}`")
    return value.strip()


def _optional_str(parent: dict[str, Any], key: str) -> str | None:
    value = parent.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise TranslationRepositoryConfigError(f"Expected string at `{key}`")
    return value.strip()


def _optional_int(parent: dict[str, Any], key: str, default: int) -> int:
    value = parent.get(key, default)
    if not isinstance(value, int):
        raise TranslationRepositoryConfigError(f"Expected integer at `{key}`")
    return value


def _required_str_list(parent: dict[str, Any], key: str) -> list[str]:
    value = parent.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TranslationRepositoryConfigError(f"Expected string list at `{key}`")
    return [item.strip() for item in value if item.strip()]


def _optional_str_list(parent: dict[str, Any], key: str) -> list[str]:
    value = parent.get(key, [])
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TranslationRepositoryConfigError(f"Expected string list at `{key}`")
    return [item.strip() for item in value if item.strip()]


def _duplicates(values: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    return duplicates
