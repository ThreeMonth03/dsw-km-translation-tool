"""Plan immutable locale revisions from published releases and usable translations."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from .command import CommandRunner, default_command_runner, make_checked_runner
from .locale_release import LocaleReleaseError, locale_revision
from .po_support.parser import PoCatalogParser
from .translation_repository_config import load_translation_repository_config, version_paths

_run = make_checked_runner(LocaleReleaseError, include_command=True)


def effective_translations(text: str, language: str) -> dict[str, str]:
    """Ignore headers, references and untranslated/fuzzy entries when comparing locales."""
    catalog, _ = PoCatalogParser.parse_catalog(text, target_language=language)
    return {
        message.id: message.string
        for message in catalog
        if message.id and message.string and not message.fuzzy
    }


def plan_locale_release(
    *,
    repo_root: Path,
    published_tags: Iterable[str],
    reserved_tags: Iterable[str] = (),
    runner: CommandRunner = default_command_runner,
) -> dict[str, str | bool]:
    """Compare HEAD with the newest published locale and reserve no remote state."""
    config = load_translation_repository_config(repo_root / "translation-config.yml")
    language = config.translation.target_language
    po_path = version_paths(config).final_po_path.as_posix()

    def git(*args: str) -> str:
        return _run(
            runner, ["git", *args], cwd=repo_root, description="plan locale release"
        ).stdout.strip()

    def revisions(tags: Iterable[str]) -> dict[int, str]:
        result = {}
        for tag in tags:
            try:
                result[locale_revision(tag, language)] = tag
            except LocaleReleaseError:
                continue
        return result

    published = revisions(published_tags)
    existing = revisions([*git("tag", "--list").splitlines(), *reserved_tags])
    previous = published[max(published)] if published else ""
    current = effective_translations(git("show", f"HEAD:{po_path}"), language)
    old = (
        effective_translations(git("show", f"refs/tags/{previous}:{po_path}"), language)
        if previous
        else {}
    )
    changed = current != old
    revision = max([0, *existing, *published]) + 1
    return {
        "publish": changed,
        "tag": f"locale-{language}-r{revision}" if changed else "",
        "previous_tag": previous,
        "commit": git("rev-parse", "HEAD"),
    }
