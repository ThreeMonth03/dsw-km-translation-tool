"""Helpers for pulling KM bundle snapshots from the DSW Registry."""

from __future__ import annotations

import hashlib
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .km_registry import KmRegistryError
from .translation_repository_config import (
    format_package_id,
    load_translation_repository_config,
    normalize_version,
    version_paths,
)

BundleDownloader = Callable[[str, str], bytes]


@dataclass(frozen=True)
class KmBundlePullResult:
    """Summary of one KM bundle pull."""

    version: str
    coordinate: str
    url: str
    target_path: Path
    changed: bool
    initialized: bool
    bytes_downloaded: int
    sha256: str
    previous_sha256: str | None


def pull_km_bundle(
    *,
    config_path: Path,
    repo_root: Path,
    token: str,
    km_version: str | None = None,
    downloader: BundleDownloader | None = None,
    allow_existing_change: bool = False,
) -> KmBundlePullResult:
    """Pull one KM bundle snapshot into the configured source path.

    Existing bundle snapshots are treated as immutable by default. If the
    Registry returns different bytes for a version that already exists locally,
    this function raises instead of overwriting the source snapshot.
    """

    if not token.strip():
        raise KmRegistryError("Pulling KM bundles from the DSW Registry requires a token")

    repository_config = load_translation_repository_config(config_path)
    version = normalize_version(
        km_version or repository_config.knowledge_model.supported_versions[-1]
    )
    paths = version_paths(repository_config, version)
    target_path = repo_root / paths.source_km_path
    coordinate = format_package_id(
        organization_id=repository_config.knowledge_model.organization_id,
        km_id=repository_config.knowledge_model.km_id,
        version=version,
    )
    url = _bundle_url(repository_config.registry.api_url, coordinate)
    download = downloader or _download_bundle
    downloaded = download(url, token)
    downloaded_hash = _sha256(downloaded)
    previous_bytes = target_path.read_bytes() if target_path.exists() else None
    previous_hash = _sha256(previous_bytes) if previous_bytes is not None else None

    if previous_bytes == downloaded:
        return KmBundlePullResult(
            version=version,
            coordinate=coordinate,
            url=url,
            target_path=target_path,
            changed=False,
            initialized=False,
            bytes_downloaded=len(downloaded),
            sha256=downloaded_hash,
            previous_sha256=previous_hash,
        )

    if previous_bytes is not None and not allow_existing_change:
        raise KmRegistryError(
            "Registry returned a different KM bundle for an existing version "
            f"{coordinate}. Refusing to overwrite {target_path}."
        )

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(downloaded)
    return KmBundlePullResult(
        version=version,
        coordinate=coordinate,
        url=url,
        target_path=target_path,
        changed=True,
        initialized=previous_bytes is None,
        bytes_downloaded=len(downloaded),
        sha256=downloaded_hash,
        previous_sha256=previous_hash,
    )


def _bundle_url(api_url: str, coordinate: str) -> str:
    encoded_coordinate = urllib.parse.quote(coordinate, safe="")
    return f"{api_url.rstrip('/')}/knowledge-model-packages/{encoded_coordinate}/bundle"


def _download_bundle(url: str, token: str) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "Authorization": _authorization_header(token),
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            return response.read()
    except OSError as error:
        raise KmRegistryError(f"Unable to download KM bundle from {url}") from error


def _authorization_header(token: str) -> str:
    stripped = token.strip()
    if stripped.lower().startswith(("bearer ", "token ")):
        return stripped
    return f"Bearer {stripped}"


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()
