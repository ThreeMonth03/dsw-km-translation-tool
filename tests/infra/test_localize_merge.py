"""Tests for conservative Localize/Weblate PO merges."""

from __future__ import annotations

import json
from pathlib import Path

from dsw_translation_tool.localize_merge import LocalizePoMerger, parse_po_entry_states

UUID_A = "11111111-1111-4111-8111-111111111111"
UUID_B = "22222222-2222-4222-8222-222222222222"


def write_po(path: Path, entries: list[tuple[str, str, str, str]], *, fuzzy: bool = False) -> None:
    """Write a small PO file for tests.

    Args:
        path: Destination PO path.
        entries: Tuples of ``(uuid, field, msgid, msgstr)``.
        fuzzy: Whether every entry should be marked fuzzy.
    """

    lines = [
        'msgid ""\n',
        'msgstr ""\n',
        "\n",
    ]
    for uuid, field, msgid, msgstr in entries:
        lines.append(f"#: question:{uuid}:{field}\n")
        if fuzzy:
            lines.append("#, fuzzy\n")
        lines.append(f'msgid "{msgid}"\n')
        lines.append(f'msgstr "{msgstr}"\n')
        lines.append("\n")
    path.write_text("".join(lines), encoding="utf-8")


def merge_workspace(
    workspace: Path,
    *,
    base_entries: list[tuple[str, str, str, str]],
    latest_entries: list[tuple[str, str, str, str]],
    repo_entries: list[tuple[str, str, str, str]],
    protected_chapters: tuple[str, ...] = (),
    latest_fuzzy: bool = False,
    conflict_policy: str = "conservative",
) -> tuple[Path, dict[str, object]]:
    """Run a PO merge and return output path plus parsed report."""

    base_po = workspace / "base.po"
    latest_po = workspace / "latest.po"
    repo_po = workspace / "repo.po"
    out_po = workspace / "merged.po"
    report_path = workspace / "merge-report.json"
    tree_dir = workspace / "tree"
    write_po(base_po, base_entries)
    write_po(latest_po, latest_entries, fuzzy=latest_fuzzy)
    write_po(repo_po, repo_entries)

    LocalizePoMerger().merge(
        base_po_path=base_po,
        latest_po_path=latest_po,
        repo_po_path=repo_po,
        out_po_path=out_po,
        report_path=report_path,
        tree_dir=tree_dir,
        protected_chapters=protected_chapters,
        conflict_policy=conflict_policy,
    )

    return out_po, json.loads(report_path.read_text(encoding="utf-8"))


def output_msgstr(path: Path, uuid: str, field: str = "text") -> str:
    """Return one merged msgstr from a PO file."""

    return parse_po_entry_states(path)[(uuid, field)].msgstr


def test_merge_accepts_latest_when_repo_still_matches_base(workspace: Path) -> None:
    """Verify Localize changes are accepted when the repo did not edit the entry."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "新")],
        repo_entries=[(UUID_A, "text", "Hello", "舊")],
    )

    assert output_msgstr(out_po, UUID_A) == "新"
    assert report["accepted_latest"] == 1
    assert report["conflicts"] == 0


def test_merge_keeps_repo_when_only_repo_changed(workspace: Path) -> None:
    """Verify local repo edits are preserved when Localize did not change."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "舊")],
        repo_entries=[(UUID_A, "text", "Hello", "本地")],
    )

    assert output_msgstr(out_po, UUID_A) == "本地"
    assert report["accepted_latest"] == 0
    assert report["decisions"] == []


def test_merge_reports_conflict_when_repo_and_latest_both_changed(workspace: Path) -> None:
    """Verify competing non-empty changes keep repo and produce conflict report."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "Weblate")],
        repo_entries=[(UUID_A, "text", "Hello", "本地")],
    )

    assert output_msgstr(out_po, UUID_A) == "本地"
    assert report["conflicts"] == 1
    assert report["decisions"][0]["decision"] == "conflict"


def test_merge_can_accept_latest_when_weblate_is_source_of_truth(workspace: Path) -> None:
    """Verify latest-wins mode accepts Weblate text over competing repo edits."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "Weblate")],
        repo_entries=[(UUID_A, "text", "Hello", "本地")],
        conflict_policy="latest-wins",
    )

    assert output_msgstr(out_po, UUID_A) == "Weblate"
    assert report["accepted_latest"] == 1
    assert report["conflicts"] == 0
    assert report["decisions"][0]["decision"] == "accepted-latest"


def test_merge_keeps_protected_repo_text_even_in_latest_wins_mode(workspace: Path) -> None:
    """Verify one-shot migration protection still overrides latest-wins mode."""

    uuid_dir = workspace / "tree" / "0001 Root" / "0003 Protected" / "0001 Node"
    uuid_dir.mkdir(parents=True)
    (uuid_dir / "_uuid.txt").write_text(UUID_A, encoding="utf-8")

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "Weblate")],
        repo_entries=[(UUID_A, "text", "Hello", "本地")],
        protected_chapters=("0003",),
        conflict_policy="latest-wins",
    )

    assert output_msgstr(out_po, UUID_A) == "本地"
    assert report["protected_skips"] == 1
    assert report["decisions"][0]["decision"] == "protected"


def test_merge_does_not_overwrite_non_empty_repo_with_empty_latest(workspace: Path) -> None:
    """Verify empty Localize updates cannot erase non-empty repo translations."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "")],
        repo_entries=[(UUID_A, "text", "Hello", "舊")],
    )

    assert output_msgstr(out_po, UUID_A) == "舊"
    assert report["empty_overwrite_skips"] == 1
    assert report["decisions"][0]["decision"] == "empty-overwrite-skip"


def test_merge_protects_configured_chapter_paths(workspace: Path) -> None:
    """Verify protected chapter UUIDs keep repo translations."""

    uuid_dir = workspace / "tree" / "0001 Root" / "0003 Protected" / "0001 Node"
    uuid_dir.mkdir(parents=True)
    (uuid_dir / "_uuid.txt").write_text(UUID_A, encoding="utf-8")

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "Weblate")],
        repo_entries=[(UUID_A, "text", "Hello", "舊")],
        protected_chapters=("0003",),
    )

    assert output_msgstr(out_po, UUID_A) == "舊"
    assert report["protected_skips"] == 1
    assert report["decisions"][0]["protected"] is True


def test_merge_reports_source_mismatch_without_accepting_latest(workspace: Path) -> None:
    """Verify source text mismatches are not merged."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Changed source", "新")],
        repo_entries=[(UUID_A, "text", "Hello", "舊")],
    )

    assert output_msgstr(out_po, UUID_A) == "舊"
    assert report["source_mismatches"] == 1
    assert report["decisions"][0]["decision"] == "source-mismatch"


def test_merge_skips_fuzzy_latest_translation(workspace: Path) -> None:
    """Verify fuzzy latest Localize entries are not accepted."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "新")],
        repo_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_fuzzy=True,
    )

    assert output_msgstr(out_po, UUID_A) == "舊"
    assert report["fuzzy_skips"] == 1
    assert report["decisions"][0]["decision"] == "latest-fuzzy"


def test_merge_ignores_fuzzy_marker_when_latest_translation_is_unchanged(
    workspace: Path,
) -> None:
    """Verify unchanged fuzzy latest entries do not create report noise."""

    out_po, report = merge_workspace(
        workspace,
        base_entries=[(UUID_A, "text", "Hello", "舊")],
        latest_entries=[(UUID_A, "text", "Hello", "舊")],
        repo_entries=[(UUID_A, "text", "Hello", "本地")],
        latest_fuzzy=True,
    )

    assert output_msgstr(out_po, UUID_A) == "本地"
    assert report["fuzzy_skips"] == 0
    assert report["decisions"] == []
