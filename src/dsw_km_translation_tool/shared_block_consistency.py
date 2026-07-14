"""Validate canonical shared translations against expanded tree entries."""

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


def find_shared_block_consistency_issues(
    *,
    repo_root: Path,
    base_ref: str,
    head_ref: str,
    head_targets: Mapping[TranslationKey, str],
    tree_path: Path = Path("tree"),
    target_lang: str = "zh_Hant",
    runner: CommandRunner = default_command_runner,
) -> tuple[SharedBlockConsistencyIssue, ...]:
    """Return inconsistencies between canonical shared blocks and tree fields."""

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
        issues.extend(
            _compare_group_with_tree(
                path=path,
                group_key=group_key,
                shared_translation=shared_translation,
                head_targets=head_targets,
            )
        )

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

    return tuple(issues)


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


def _compare_group_with_tree(
    *,
    path: str,
    group_key: GroupKey,
    shared_translation: str,
    head_targets: Mapping[TranslationKey, str],
) -> list[SharedBlockConsistencyIssue]:
    issues: list[SharedBlockConsistencyIssue] = []
    for key in group_key:
        tree_translation = head_targets.get(key)
        if tree_translation is None:
            issues.append(
                SharedBlockConsistencyIssue(
                    path=path,
                    message=f"Referenced tree field is missing: {_format_key(key)}.",
                )
            )
        elif tree_translation != shared_translation:
            issues.append(
                SharedBlockConsistencyIssue(
                    path=path,
                    message=(
                        f"Shared translation does not match tree field {_format_key(key)}. "
                        "Run shared-string sync before merging."
                    ),
                )
            )
    return issues


def _format_keys(keys: list[TranslationKey]) -> str:
    return ", ".join(_format_key(key) for key in keys)


def _format_key(key: TranslationKey) -> str:
    entity_uuid, field = key
    return f"{entity_uuid}:{field}"
