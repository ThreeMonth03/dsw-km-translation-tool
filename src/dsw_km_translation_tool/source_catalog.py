"""Read a public upstream POT snapshot for a non-mutating source catalog audit."""

from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path

from .locale_coverage import LocaleCoverageError, compare_source_catalog


def snapshot_upstream_pot(repository: str, destination: Path) -> tuple[str, str]:
    """Fetch only the public default branch; never execute upstream scripts or hooks.

    The immutable commit and byte-for-byte POT are retained with the report.
    The URL must be a public GitHub repository URL without embedded credentials.
    No Weblate credentials, API writes, worktree checkout or pushes are involved.
    """
    match = re.fullmatch(
        r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?/?", repository
    )
    if not match:
        raise LocaleCoverageError("Source catalog audit requires a public HTTPS GitHub repository")
    url = f"https://github.com/{match[1]}"
    with tempfile.TemporaryDirectory(prefix="dsw-source-catalog-") as temp:
        command = ["git", "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null"]
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_COUNT": "0",
        }

        def git(*args: str) -> bytes:
            try:
                return subprocess.run(
                    [*command, *args],
                    env=env,
                    check=True,
                    capture_output=True,
                    timeout=60,
                ).stdout
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                raise LocaleCoverageError(
                    "Could not read the public upstream POT snapshot"
                ) from error

        clone = str(Path(temp) / "upstream.git")
        git("clone", "--bare", "--depth=1", "--", url, clone)
        commit = git("--git-dir", clone, "rev-parse", "HEAD").decode().strip()
        content = git("--git-dir", clone, "show", f"{commit}:messages.pot")
    destination.write_bytes(content)
    return commit, f"{url}/blob/{commit}/messages.pot"


def audit_source_catalog(
    *, repository: str, pot_path: Path, out: Path, package_id: str, source_language: str
) -> dict[str, object]:
    """Download an upstream snapshot and compare message identities for the same KM."""
    upstream_pot = out / "upstream.pot"
    commit, url = snapshot_upstream_pot(repository, upstream_pot)
    report = compare_source_catalog(
        pot_path=pot_path,
        upstream_pot_path=upstream_pot,
        package_id=package_id,
        source_language=source_language,
    )
    return {**report, "upstream_commit": commit, "upstream_url": url}
