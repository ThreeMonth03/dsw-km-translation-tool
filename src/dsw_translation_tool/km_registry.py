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
    sorted_versions,
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
    """Comparison between configured KM versions and Registry versions."""

    organization_id: str
    km_id: str
    registry_api_url: str
    configured_versions: tuple[str, ...]
    registry_versions: tuple[str, ...]
    new_versions: tuple[str, ...]
    missing_versions: tuple[str, ...]
    latest_configured_version: str | None
    latest_registry_version: str | None
    packages: tuple[KmRegistryPackage, ...]

    def to_report_dict(self) -> dict[str, object]:
        """Return a stable JSON-serializable report."""

        return {
            "organization_id": self.organization_id,
            "km_id": self.km_id,
            "registry_api_url": self.registry_api_url,
            "configured_versions": list(self.configured_versions),
            "registry_versions": list(self.registry_versions),
            "new_versions": list(self.new_versions),
            "missing_versions": list(self.missing_versions),
            "latest_configured_version": self.latest_configured_version,
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
    registry_versions = tuple(sorted_versions(tuple(package.version for package in packages)))
    configured_versions = km_config.supported_versions
    configured_set = set(configured_versions)
    registry_set = set(registry_versions)
    new_versions = tuple(version for version in registry_versions if version not in configured_set)
    missing_versions = tuple(
        version for version in configured_versions if version not in registry_set
    )
    return KmVersionDiscoveryResult(
        organization_id=km_config.organization_id,
        km_id=km_config.km_id,
        registry_api_url=config.registry.api_url,
        configured_versions=configured_versions,
        registry_versions=registry_versions,
        new_versions=new_versions,
        missing_versions=missing_versions,
        latest_configured_version=configured_versions[-1] if configured_versions else None,
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

    status = "new version available" if result.new_versions else "current"
    lines = [
        "## KM Version Monitor",
        "",
        f"Knowledge model: `{result.organization_id}:{result.km_id}`",
        f"Registry API: `{result.registry_api_url}`",
        f"Status: **{status}**",
        "",
        "| Metric | Versions |",
        "| --- | --- |",
        f"| Configured versions | {_format_versions(result.configured_versions)} |",
        f"| Registry versions | {_format_versions(result.registry_versions)} |",
        f"| New versions | {_format_versions(result.new_versions)} |",
        f"| Missing in registry | {_format_versions(result.missing_versions)} |",
        f"| Latest configured | {_format_version(result.latest_configured_version)} |",
        f"| Latest registry | {_format_version(result.latest_registry_version)} |",
        "",
    ]
    if result.new_versions:
        lines.extend(
            [
                "### Follow-up",
                "",
                (
                    "A newer published KM exists in the Registry. Run the KM update "
                    "runbook on a disposable branch before changing `translation-config.yml`."
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
