"""Read a public upstream POT snapshot for a non-mutating source catalog audit."""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from .bounded_download import DOWNLOAD_SECONDS, IO_TIMEOUT_SECONDS, read_bounded_response
from .catalog_limits import MAX_CATALOG_BYTES, CatalogLimitError
from .locale_coverage import LocaleCoverageError, compare_source_catalog


class _NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LocaleCoverageError("Public POT snapshots must not redirect")


def _public_download(url: str, *, max_bytes: int, deadline: float) -> bytes:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LocaleCoverageError("Public POT snapshot exceeded its elapsed-time budget")
    request = urllib.request.Request(url, headers={"User-Agent": "dsw-km-translation-tool"})
    opener = urllib.request.build_opener(_NoRedirects())
    try:
        with opener.open(request, timeout=min(IO_TIMEOUT_SECONDS, remaining)) as response:
            return read_bounded_response(response, max_bytes=max_bytes, deadline=deadline)
    except (urllib.error.URLError, TimeoutError, CatalogLimitError) as error:
        raise LocaleCoverageError("Could not read the bounded public POT snapshot") from error


def snapshot_upstream_pot(repository: str, destination: Path) -> tuple[str, str]:
    """Fetch only the public default branch; never execute upstream scripts or hooks.

    The immutable commit and byte-for-byte POT are retained with the report.
    The URL must be a public GitHub repository URL without embedded credentials.
    No Weblate credentials, API writes, worktree checkout or pushes are involved.
    """
    match = re.fullmatch(
        r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?",
        repository,
    )
    if not match:
        raise LocaleCoverageError("Source catalog audit requires a public HTTPS GitHub repository")
    url = f"https://github.com/{match[1]}"
    deadline = time.monotonic() + DOWNLOAD_SECONDS
    metadata = _public_download(
        f"https://api.github.com/repos/{match[1]}/commits?per_page=1",
        max_bytes=1024 * 1024,
        deadline=deadline,
    )
    try:
        commits = json.loads(metadata)
        commit = commits[0]["sha"]
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-f]{40}", commit):
            raise ValueError("Invalid commit")
    except (ValueError, KeyError, IndexError, TypeError) as error:
        raise LocaleCoverageError("Public GitHub response did not identify a commit") from error
    content = _public_download(
        f"https://raw.githubusercontent.com/{match[1]}/{commit}/messages.pot",
        max_bytes=MAX_CATALOG_BYTES,
        deadline=deadline,
    )
    destination.write_bytes(content)
    return commit, f"{url}/blob/{commit}/messages.pot"


def audit_source_catalog(
    *, repository: str, pot_path: Path, out: Path, package_id: str, source_language: str
) -> dict[str, object]:
    """Download an upstream snapshot and compare message identities with the context KM."""
    upstream_pot = out / "upstream.pot"
    commit, url = snapshot_upstream_pot(repository, upstream_pot)
    report = compare_source_catalog(
        pot_path=pot_path,
        upstream_pot_path=upstream_pot,
        package_id=package_id,
        source_language=source_language,
    )
    return {**report, "upstream_commit": commit, "upstream_url": url}
