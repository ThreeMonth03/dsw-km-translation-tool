"""Resolve canonical Markdown edits before reporting GitHub translations."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .command import CommandRunner, default_command_runner, make_checked_runner
from .constants import SHARED_BLOCK_CONTEXT_FILENAME
from .shared_blocks.parser import GroupKey, SharedBlocksCatalogParser

TranslationKey = tuple[str, str]


class SharedBlockConsistencyError(RuntimeError):
    """Raised when shared-block consistency cannot be inspected."""


_run_checked = make_checked_runner(
    SharedBlockConsistencyError,
    include_command=True,
)


@dataclass(frozen=True)
class SharedBlockConsistencyIssue:
    """One canonical shared translation that disagrees with the tree."""

    path: str
    message: str


@dataclass(frozen=True)
class SharedBlockResolution:
    """Effective base and candidate translations with unresolved edit conflicts."""

    base_targets: dict[TranslationKey, str]
    head_targets: dict[TranslationKey, str]
    issues: tuple[SharedBlockConsistencyIssue, ...]


def resolve_shared_block_translations(
    *,
    repo_root: Path,
    base_ref: str,
    head_ref: str,
    base_targets: Mapping[TranslationKey, str],
    head_targets: Mapping[TranslationKey, str],
    tree_path: Path = Path("tree"),
    target_lang: str = "zh_Hant",
    runner: CommandRunner = default_command_runner,
) -> SharedBlockResolution:
    """Expand canonical edits in memory, rejecting competing field edits.

    An unchanged expanded field may retain its base text until post-merge sync.
    A field explicitly edited to a different value must be resolved by the
    contributor instead of being silently replaced by the canonical text.
    """

    parser = SharedBlocksCatalogParser(target_lang=target_lang)
    base_documents = _read_shared_block_documents(
        repo_root=repo_root,
        ref=base_ref,
        tree_path=tree_path,
        runner=runner,
    )
    head_documents = _read_shared_block_documents(
        repo_root=repo_root,
        ref=head_ref,
        tree_path=tree_path,
        runner=runner,
    )
    issues: list[SharedBlockConsistencyIssue] = []
    head_groups: dict[GroupKey, str] = {}
    resolved_base = dict(base_targets)
    resolved_head = dict(head_targets)

    for path, text in sorted(head_documents.items()):
        try:
            group_key, shared_translation = parser.parse_document(text, source=path)
        except ValueError as error:
            issues.append(SharedBlockConsistencyIssue(path=path, message=str(error)))
            continue
        previous_path = head_groups.get(group_key)
        if previous_path is not None:
            issues.append(
                SharedBlockConsistencyIssue(
                    path=path,
                    message=f"Shared key duplicates the group in {previous_path}.",
                )
            )
            continue
        head_groups[group_key] = path
        base_translation = shared_translation
        if path in base_documents:
            try:
                base_group, base_translation = parser.parse_document(
                    base_documents[path], source=path
                )
            except ValueError as error:
                issues.append(SharedBlockConsistencyIssue(path=path, message=str(error)))
                continue
            if base_group != group_key:
                issues.append(
                    SharedBlockConsistencyIssue(
                        path=path,
                        message="Shared key metadata changed; edit only the Translation block.",
                    )
                )
                continue
        for key in group_key:
            if key not in head_targets:
                issues.append(
                    SharedBlockConsistencyIssue(
                        path=path, message=f"Referenced tree field is missing: {_format_key(key)}."
                    )
                )
                continue
            tree_changed = head_targets[key] != base_targets.get(key)
            if head_targets[key] != shared_translation and tree_changed:
                issues.append(
                    SharedBlockConsistencyIssue(
                        path=path,
                        message=(
                            f"Conflicting translation for {_format_key(key)}. "
                            "Edit the canonical shared Translation block and remove competing field edits."
                        ),
                    )
                )
                continue
            if key in base_targets:
                resolved_base[key] = base_translation
            resolved_head[key] = shared_translation

    for path in sorted(base_documents.keys() - head_documents.keys()):
        try:
            group_key, _ = parser.parse_document(base_documents[path], source=path)
        except ValueError:
            continue
        remaining_keys = [key for key in group_key if key in head_targets]
        if remaining_keys:
            issues.append(
                SharedBlockConsistencyIssue(
                    path=path,
                    message=(
                        "Canonical shared block was removed while referenced tree fields remain: "
                        f"{_format_keys(remaining_keys)}."
                    ),
                )
            )

    return SharedBlockResolution(resolved_base, resolved_head, tuple(issues))


def _read_shared_block_documents(
    *,
    repo_root: Path,
    ref: str,
    tree_path: Path,
    runner: CommandRunner,
) -> dict[str, str]:
    shared_root = tree_path / "shared_blocks"
    result = _run_checked(
        runner,
        ["git", "ls-tree", "-r", "--name-only", ref, "--", shared_root.as_posix()],
        cwd=repo_root,
        description=f"list shared blocks in {ref}",
    )
    paths = [
        path
        for path in result.stdout.splitlines()
        if path.endswith(f"/{SHARED_BLOCK_CONTEXT_FILENAME}")
    ]
    return {
        path: _run_checked(
            runner,
            ["git", "show", f"{ref}:{path}"],
            cwd=repo_root,
            description=f"read {path} from {ref}",
        ).stdout
        for path in paths
    }


def _format_keys(keys: list[TranslationKey]) -> str:
    return ", ".join(_format_key(key) for key in keys)


def _format_key(key: TranslationKey) -> str:
    entity_uuid, field = key
    return f"{entity_uuid}:{field}"
