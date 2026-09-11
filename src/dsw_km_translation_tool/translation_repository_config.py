"""Configuration contract for dedicated KM translation repositories.

The tooling repository is reusable, while each production translation
repository provides a ``translation-config.yml`` file. This module validates
that file and derives conventional artifact paths used by sync, report, and KM
update commands.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml


class TranslationRepositoryConfigError(ValueError):
    """Raised when a translation repository config is invalid."""


@dataclass(frozen=True)
class KnowledgeModelRepositoryConfig:
    """Source KM coordinates and the currently tracked package version."""

    organization_id: str
    km_id: str
    upstream_repository: str
    version: str


@dataclass(frozen=True)
class TranslationLanguageConfig:
    """Language metadata for a native DSW knowledge-model locale."""

    source_language: str
    target_language: str
    target_language_label: str


@dataclass(frozen=True)
class BranchConfig:
    """Translation branch naming policy."""

    tracking_branch: str


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
class KmVersionWorkspacePaths:
    """Conventional workspace paths for the configured KM package."""

    version: str
    package_id: str
    source_slug: str
    source_km_path: Path
    source_po_path: Path
    translation_tree_dir: Path
    final_po_path: Path
    review_diff_path: Path
    validation_report_path: Path
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


VERSION_RE = re.compile(r"^v?(?P<number>\d+(?:\.\d+){1,3})$")
DEFAULT_REGISTRY_API_URL = "https://api.registry.ds-wizard.org"
TRUSTED_TOOLING_REPOSITORY = "ThreeMonth03/dsw-km-translation-tool"
GIT_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")


def load_translation_repository_config(path: str | Path) -> TranslationRepositoryConfig:
    """Load and validate a KM translation repository config.

    Args:
        path: Path to ``translation-config.yml``.

    Returns:
        Parsed config with normalized bare semantic versions such as ``2.7.0``.
    """

    config_path = Path(path)
    payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TranslationRepositoryConfigError("translation-config.yml must contain a mapping")
    _reject_unknown_keys(
        payload,
        allowed={
            "schema_version",
            "knowledge_model",
            "translation",
            "branches",
            "tooling",
            "localize",
            "registry",
        },
        section="config",
    )

    schema_version = _require_int(payload, "schema_version")
    if schema_version != 3:
        raise TranslationRepositoryConfigError(
            f"Unsupported translation-config.yml schema_version {schema_version!r}"
        )

    knowledge_model = _load_knowledge_model_config(_require_dict(payload, "knowledge_model"))
    translation = _load_translation_config(_require_dict(payload, "translation"))
    branches = _load_branch_config(_require_dict(payload, "branches"))
    tooling = _load_tooling_config(_require_dict(payload, "tooling"))
    localize = _load_localize_config(_require_dict(payload, "localize"))
    registry = _load_registry_config(_optional_dict(payload, "registry"))

    return TranslationRepositoryConfig(
        schema_version=schema_version,
        knowledge_model=knowledge_model,
        translation=translation,
        branches=branches,
        tooling=tooling,
        localize=localize,
        registry=registry,
    )


def _load_knowledge_model_config(
    payload: dict[str, Any],
) -> KnowledgeModelRepositoryConfig:
    _reject_unknown_keys(
        payload,
        allowed={"organization_id", "km_id", "upstream_repository", "version"},
        section="knowledge_model",
    )
    return KnowledgeModelRepositoryConfig(
        organization_id=_require_identifier(payload, "organization_id"),
        km_id=_require_identifier(payload, "km_id"),
        upstream_repository=_require_str(payload, "upstream_repository"),
        version=normalize_version(_require_str(payload, "version")),
    )


def _load_translation_config(payload: dict[str, Any]) -> TranslationLanguageConfig:
    _reject_unknown_keys(
        payload,
        allowed={
            "source_language",
            "target_language",
            "target_language_label",
        },
        section="translation",
    )
    return TranslationLanguageConfig(
        source_language=_require_identifier(payload, "source_language"),
        target_language=_require_identifier(payload, "target_language"),
        target_language_label=_require_str(payload, "target_language_label"),
    )


def _load_branch_config(payload: dict[str, Any]) -> BranchConfig:
    _reject_unknown_keys(payload, allowed={"tracking_branch"}, section="branches")
    tracking = _optional_str(payload, "tracking_branch")
    if not tracking:
        raise TranslationRepositoryConfigError("branches.tracking_branch is required")
    return BranchConfig(tracking_branch=_validate_git_ref(tracking, "branches.tracking_branch"))


def _load_tooling_config(payload: dict[str, Any]) -> ToolingConfig:
    _reject_unknown_keys(payload, allowed={"repository", "ref"}, section="tooling")
    repository = _require_str(payload, "repository")
    if repository != TRUSTED_TOOLING_REPOSITORY:
        raise TranslationRepositoryConfigError(
            f"tooling.repository must be the trusted repository `{TRUSTED_TOOLING_REPOSITORY}`"
        )
    return ToolingConfig(
        repository=repository,
        ref=_validate_git_ref(_require_str(payload, "ref"), "tooling.ref"),
    )


def _validate_git_ref(value: str, field: str) -> str:
    """Reject ref names that are unsafe in generated YAML, shells, or Git."""

    invalid = (
        not GIT_REF_RE.fullmatch(value)
        or ".." in value
        or "//" in value
        or "@{" in value
        or value.endswith(("/", "."))
        or any(part.startswith(".") or part.endswith(".lock") for part in value.split("/"))
    )
    if invalid:
        raise TranslationRepositoryConfigError(f"{field} must be a safe Git ref name")
    return value


def _load_localize_config(payload: dict[str, Any]) -> LocalizeConfig:
    _reject_unknown_keys(payload, allowed={"download_url", "repository"}, section="localize")
    return LocalizeConfig(
        download_url=_validate_https_url(
            _require_str(payload, "download_url"), "localize.download_url"
        ),
        repository=_optional_str(payload, "repository"),
    )


def _validate_https_url(value: str, field: str) -> str:
    """Reject download URLs that could access runner-local resources."""

    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise TranslationRepositoryConfigError(f"{field} must be an HTTPS URL without credentials")
    return value


def _load_registry_config(payload: dict[str, Any]) -> RegistryConfig:
    _reject_unknown_keys(payload, allowed={"api_url"}, section="registry")
    return RegistryConfig(
        api_url=_optional_str(payload, "api_url") or DEFAULT_REGISTRY_API_URL,
    )


def tracking_branch(config: TranslationRepositoryConfig) -> str:
    """Return the branch that should track the configured KM."""

    return config.branches.tracking_branch


def version_paths(config: TranslationRepositoryConfig) -> KmVersionWorkspacePaths:
    """Return conventional workspace paths for the configured KM package."""

    normalized = config.knowledge_model.version
    package_id = format_package_id(
        organization_id=config.knowledge_model.organization_id,
        km_id=config.knowledge_model.km_id,
        version=normalized,
    )
    source_slug = (
        f"{config.knowledge_model.organization_id}-{config.knowledge_model.km_id}-{normalized}"
    )
    target_lang = config.translation.target_language
    weblate_po_path = Path("sources") / "localize" / target_lang / "latest.po"
    return KmVersionWorkspacePaths(
        version=normalized,
        package_id=package_id,
        source_slug=source_slug,
        source_km_path=Path("sources") / "knowledge-models" / source_slug / f"{source_slug}.km",
        source_po_path=weblate_po_path,
        translation_tree_dir=Path("tree"),
        final_po_path=Path("builds") / "final_translated.po",
        review_diff_path=Path("reviews") / "final_translated.diff",
        validation_report_path=Path("reports") / "final_report.json",
        conflicts_report_path=Path("reviews") / "conflicts.json",
    )


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


def _require_identifier(parent: dict[str, Any], key: str) -> str:
    value = _require_str(parent, key)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
        raise TranslationRepositoryConfigError(f"Expected safe identifier at `{key}`")
    return value


def _require_int(parent: dict[str, Any], key: str) -> int:
    value = parent.get(key)
    if not isinstance(value, int):
        raise TranslationRepositoryConfigError(f"Expected integer at `{key}`")
    return value


def _reject_unknown_keys(
    payload: dict[str, Any],
    *,
    allowed: set[str],
    section: str,
) -> None:
    unknown = sorted(set(payload) - allowed)
    if unknown:
        fields = ", ".join(f"{section}.{field}" for field in unknown)
        raise TranslationRepositoryConfigError(f"Unexpected configuration field(s): {fields}")
