"""DSW Registry helpers for knowledge-model version discovery."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .translation_repository_config import (
    TranslationRepositoryConfig,
    load_translation_repository_config,
    normalize_version,
    version_sort_key,
)

Downloader = Callable[[str], bytes]


class KmRegistryError(RuntimeError):
    """Raised when KM Registry data cannot be fetched or parsed."""


@dataclass(frozen=True)
class KmRegistryPackage:
    """One knowledge-model package entry returned by the DSW Registry."""

    organization_id: str
    km_id: str
    version: str
    name: str | None
    metamodel_version: int | None
    created_at: str | None

    def to_report_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable representation."""

        return {
            "organization_id": self.organization_id,
            "km_id": self.km_id,
            "version": self.version,
            "name": self.name,
            "metamodel_version": self.metamodel_version,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class KmVersionDiscoveryResult:
    """Comparison between the configured KM and Registry packages."""

    organization_id: str
    km_id: str
    registry_api_url: str
    configured_version: str
    registry_versions: tuple[str, ...]
    newer_versions: tuple[str, ...]
    configured_version_missing: bool
    latest_registry_version: str | None
    packages: tuple[KmRegistryPackage, ...]

    def to_report_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable report."""

        return {
            "organization_id": self.organization_id,
            "km_id": self.km_id,
            "registry_api_url": self.registry_api_url,
            "configured_version": self.configured_version,
            "registry_versions": list(self.registry_versions),
            "newer_versions": list(self.newer_versions),
            "configured_version_missing": self.configured_version_missing,
            "latest_registry_version": self.latest_registry_version,
            "packages": [package.to_report_dict() for package in self.packages],
        }


class KmRegistryClient:
    """Small client for the public DSW Registry package listing endpoint."""

    def __init__(self, *, api_url: str, downloader: Downloader | None = None) -> None:
        self.api_url = api_url.rstrip("/")
        self._downloader = downloader or _download_url

    def list_packages(self, *, organization_id: str, km_id: str) -> tuple[KmRegistryPackage, ...]:
        """List packages for one KM coordinate."""

        query = urllib.parse.urlencode(
            {
                "organizationId": organization_id,
                "kmId": km_id,
            }
        )
        url = f"{self.api_url}/knowledge-model-packages?{query}"
        try:
            payload = json.loads(self._downloader(url).decode("utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise KmRegistryError(f"Unable to read KM Registry response from {url}") from error
        if not isinstance(payload, list):
            raise KmRegistryError("KM Registry package listing must be a JSON list")
        return tuple(
            sorted(
                (_parse_package(item) for item in payload),
                key=lambda package: version_sort_key(package.version),
            )
        )


def discover_km_versions(
    *,
    config_path: Path,
    downloader: Downloader | None = None,
) -> KmVersionDiscoveryResult:
    """Discover upstream KM versions and compare them with repo config."""

    config = load_translation_repository_config(config_path)
    return discover_km_versions_for_config(config=config, downloader=downloader)


def discover_km_versions_for_config(
    *,
    config: TranslationRepositoryConfig,
    downloader: Downloader | None = None,
) -> KmVersionDiscoveryResult:
    """Discover upstream KM versions for an already parsed config."""

    km_config = config.knowledge_model
    client = KmRegistryClient(api_url=config.registry.api_url, downloader=downloader)
    packages = client.list_packages(
        organization_id=km_config.organization_id,
        km_id=km_config.km_id,
    )
    registry_versions = tuple(
        sorted(
            (normalize_version(package.version) for package in packages),
            key=version_sort_key,
        )
    )
    configured_version = km_config.version
    configured_key = version_sort_key(configured_version)
    newer_versions = tuple(
        version for version in registry_versions if version_sort_key(version) > configured_key
    )
    return KmVersionDiscoveryResult(
        organization_id=km_config.organization_id,
        km_id=km_config.km_id,
        registry_api_url=config.registry.api_url,
        configured_version=configured_version,
        registry_versions=registry_versions,
        newer_versions=newer_versions,
        configured_version_missing=configured_version not in registry_versions,
        latest_registry_version=registry_versions[-1] if registry_versions else None,
        packages=packages,
    )


def write_km_version_discovery_report(
    *,
    result: KmVersionDiscoveryResult,
    report_path: Path,
) -> None:
    """Write a discovery result as pretty JSON."""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(result.to_report_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def render_km_version_discovery_markdown(result: KmVersionDiscoveryResult) -> str:
    """Render KM version discovery as maintainer-readable Markdown."""

    status = "new version available" if result.newer_versions else "current"
    lines = [
        "## KM Version Monitor",
        "",
        f"Knowledge model: `{result.organization_id}:{result.km_id}`",
        f"Registry API: `{result.registry_api_url}`",
        f"Status: **{status}**",
        "",
        "| Metric | Versions |",
        "| --- | --- |",
        f"| Configured version | {_format_version(result.configured_version)} |",
        f"| Registry versions | {_format_versions(result.registry_versions)} |",
        f"| Newer versions | {_format_versions(result.newer_versions)} |",
        f"| Configured version missing | {'yes' if result.configured_version_missing else 'no'} |",
        f"| Latest registry | {_format_version(result.latest_registry_version)} |",
        "",
    ]
    if result.newer_versions:
        lines.extend(
            [
                "### Follow-up",
                "",
                (
                    "A newer published KM exists in the Registry. Run the KM update "
                    "guarded updater will retry on its next scheduled run."
                ),
                "",
            ]
        )
    if result.packages:
        lines.extend(
            [
                "### Registry Packages",
                "",
                "| Version | Name | Metamodel | Created at |",
                "| --- | --- | ---: | --- |",
            ]
        )
        for package in result.packages:
            lines.append(
                "| "
                f"{package.version} | "
                f"{_format_cell(package.name or '')} | "
                f"{package.metamodel_version if package.metamodel_version is not None else ''} | "
                f"{_format_cell(package.created_at or '')} |"
            )
    return "\n".join(lines) + "\n"


def write_km_version_discovery_markdown(
    *,
    result: KmVersionDiscoveryResult,
    report_path: Path,
) -> None:
    """Append a discovery result as Markdown."""

    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("a", encoding="utf-8") as handle:
        handle.write(render_km_version_discovery_markdown(result))


def _parse_package(payload: Any) -> KmRegistryPackage:
    if not isinstance(payload, dict):
        raise KmRegistryError("KM Registry package entry must be a JSON object")
    organization_id = _required_str(payload, "organizationId")
    km_id = _required_str(payload, "kmId")
    return KmRegistryPackage(
        organization_id=organization_id,
        km_id=km_id,
        version=normalize_version(_required_str(payload, "version")),
        name=_optional_str(payload, "name"),
        metamodel_version=_optional_int(payload, "metamodelVersion"),
        created_at=_optional_str(payload, "createdAt"),
    )


def _required_str(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise KmRegistryError(f"KM Registry package entry is missing `{key}`")
    return value.strip()


def _optional_str(payload: dict[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise KmRegistryError(f"KM Registry package entry has invalid `{key}`")
    return value.strip() or None


def _optional_int(payload: dict[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, int):
        raise KmRegistryError(f"KM Registry package entry has invalid `{key}`")
    return value


def _format_versions(versions: tuple[str, ...]) -> str:
    return ", ".join(f"`{version}`" for version in versions) if versions else "(none)"


def _format_version(version: str | None) -> str:
    return f"`{version}`" if version else "(none)"


def _format_cell(value: str) -> str:
    return " ".join(value.split()).replace("|", "\\|")


def _download_url(url: str) -> bytes:
    """Download one URL using the Python standard library."""

    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()
