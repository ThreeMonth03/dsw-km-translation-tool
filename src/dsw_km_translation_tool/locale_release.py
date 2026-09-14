"""Prepare reproducible native locale releases independently of KM versions."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

from .command import default_command_runner, make_checked_runner
from .native_locale import validate_native_locale
from .translation_repository_build import build_translation_repository
from .translation_repository_config import load_translation_repository_config


class LocaleReleaseError(ValueError):
    """Raised when a locale release cannot be reproduced from its pinned inputs."""


_run = make_checked_runner(LocaleReleaseError, include_command=True)


def locale_revision(tag: str, km_version: str, language: str) -> int:
    """Require a tag identifying the source KM, language, and positive revision."""

    prefix = f"km-{km_version}-{language}-r"
    match = re.fullmatch(re.escape(prefix) + r"([1-9][0-9]*)", tag)
    if match is None:
        raise LocaleReleaseError(f"Expected release tag {prefix}<positive revision>, got {tag!r}")
    return int(match.group(1))


def prepare_locale_release(
    *,
    repo_root: Path,
    tooling_repo: Path,
    tag: str,
    output_dir: Path,
    config_path: Path = Path("translation-config.yml"),
) -> dict[str, object]:
    """Rebuild a clean checkout, validate it, and export PO assets with provenance.

    This writes only local build outputs and a new asset directory. Publishing
    the tag and assets is the release workflow's responsibility.
    """

    root = repo_root.resolve()
    config_file = root / config_path
    config = load_translation_repository_config(config_file)
    km = config.knowledge_model
    language = config.translation.target_language
    revision = locale_revision(tag, km.version, language)
    for value in (km.organization_id, km.km_id, language):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value):
            raise LocaleReleaseError(f"Unsafe release asset identifier: {value!r}")
    if not re.fullmatch(r"[0-9a-f]{40}", config.tooling.ref):
        raise LocaleReleaseError(
            "A locale release requires tooling.ref pinned to a full commit SHA"
        )
    tool_commit = _git(tooling_repo.resolve(), "rev-parse", "HEAD")
    if tool_commit != config.tooling.ref:
        raise LocaleReleaseError("Tooling checkout does not match tooling.ref")
    _git(tooling_repo.resolve(), "diff", "--exit-code", "HEAD")
    _git(root, "diff", "--exit-code", "HEAD")
    translation_commit = _git(root, "rev-parse", "HEAD")

    build = build_translation_repository(repo_root=root, config_path=config_path)
    _git(root, "diff", "--exit-code", "HEAD")
    package_id = f"{km.organization_id}:{km.km_id}:{km.version}"
    bundle = json.loads(build.source_km_path.read_text(encoding="utf-8"))
    if bundle.get("id") != package_id:
        raise LocaleReleaseError(f"Source KM does not match configured package {package_id}")
    validation = validate_native_locale(
        po_path=build.final_po_path,
        km_path=build.source_km_path,
        target_language=language,
    )

    output = output_dir.resolve()
    if output.exists():
        raise LocaleReleaseError(f"Release output directory already exists: {output}")
    assets = output / "assets"
    assets.mkdir(parents=True)
    stem = f"{km.organization_id}-{km.km_id}-{language}-locale"
    po_name = f"{stem}-{km.version}-r{revision}.po"
    shutil.copyfile(build.final_po_path, assets / po_name)
    manifest: dict[str, object] = {
        "schema_version": 1,
        "tag": tag,
        "knowledge_model": {
            "package_id": package_id,
            "sha256": _sha256(build.source_km_path),
        },
        "language": language,
        "revision": revision,
        "translation_commit": translation_commit,
        "tooling": {"repository": config.tooling.repository, "commit": tool_commit},
        "po": {
            "filename": po_name,
            "sha256": _sha256(assets / po_name),
            "messages": validation.total_messages,
            "translated": validation.translated_messages,
        },
    }
    (assets / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (output / "release-notes.md").write_text(
        f"Native {language} locale for `{package_id}`, translation revision {revision}.\n\n"
        f"Download `{po_name}` and import it into this Knowledge Model version using "
        "DSW's **Import locale** action (DSW 4.33 or newer). "
        "Select the questionnaire language in project settings.\n\n"
        f"Messages: {validation.total_messages}; translated: {validation.translated_messages}.\n\n"
        f"Translation commit: `{translation_commit}`.\n\n"
        f"Tooling commit: `{tool_commit}`.\n\n"
        "`manifest.json` records the source KM and PO checksums. "
        "Verify downloaded assets with `sha256sum -c SHA256SUMS`.\n",
        encoding="utf-8",
    )
    (assets / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in sorted(assets.iterdir())),
        encoding="utf-8",
    )
    return manifest


def _git(root: Path, *args: str) -> str:
    return _run(
        default_command_runner, ["git", *args], cwd=root, description="verify release checkout"
    ).stdout.strip()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
