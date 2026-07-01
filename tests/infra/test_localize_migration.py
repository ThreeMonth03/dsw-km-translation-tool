"""Tests for one-shot reviewed Localize/Weblate migrations."""

from __future__ import annotations

import json
from pathlib import Path

from dsw_translation_tool.localize_merge import parse_po_entry_states
from dsw_translation_tool.localize_migration import (
    build_multipart_body,
    derive_upload_url,
    prepare_reviewed_localize_migration,
)
from migrate_reviewed_to_localize import main as migrate_reviewed_to_localize_main

UUID_A = "11111111-1111-4111-8111-111111111111"
UUID_B = "22222222-2222-4222-8222-222222222222"
UUID_C = "33333333-3333-4333-8333-333333333333"
UUID_D = "44444444-4444-4444-8444-444444444444"
UUID_E = "55555555-5555-4555-8555-555555555555"
UUID_MISSING = "66666666-6666-4666-8666-666666666666"


def write_po(path: Path, entries: list[tuple[str, str, str, str]]) -> None:
    """Write a small PO fixture."""

    lines = [
        'msgid ""\n',
        'msgstr ""\n',
        "\n",
    ]
    for uuid, field, msgid, msgstr in entries:
        lines.append(f"#: question:{uuid}:{field}\n")
        lines.append(f'msgid "{msgid}"\n')
        lines.append(f'msgstr "{msgstr}"\n')
        lines.append("\n")
    path.write_text("".join(lines), encoding="utf-8")


def write_uuid(tree_dir: Path, chapter: str, uuid_value: str) -> None:
    """Write a minimal translation-tree UUID marker below one chapter."""

    uuid_path = tree_dir / f"{chapter} Example [abc]" / uuid_value / "_uuid.txt"
    uuid_path.parent.mkdir(parents=True, exist_ok=True)
    uuid_path.write_text(uuid_value, encoding="utf-8")


def test_prepare_reviewed_migration_includes_only_safe_reviewed_changes(
    workspace: Path,
) -> None:
    """Verify migration output selects only safe Ch4-6 repo translations."""

    localize_po = workspace / "localize.po"
    repo_po = workspace / "repo.po"
    out_po = workspace / "migration.po"
    report_path = workspace / "report.json"
    tree_dir = workspace / "tree"
    for chapter, uuid_value in [
        ("0004", UUID_A),
        ("0005", UUID_B),
        ("0006", UUID_C),
        ("0004", UUID_D),
        ("0007", UUID_E),
        ("0004", UUID_MISSING),
    ]:
        write_uuid(tree_dir, chapter, uuid_value)

    write_po(
        localize_po,
        [
            (UUID_A, "text", "A", "網站舊"),
            (UUID_B, "text", "B", "相同"),
            (UUID_C, "text", "C", "網站"),
            (UUID_D, "text", "D-localize", "網站"),
            (UUID_E, "text", "E", "網站舊"),
        ],
    )
    write_po(
        repo_po,
        [
            (UUID_A, "text", "A", "repo reviewed"),
            (UUID_B, "text", "B", "相同"),
            (UUID_C, "text", "C", ""),
            (UUID_D, "text", "D-repo", "repo mismatch"),
            (UUID_E, "text", "E", "repo outside reviewed chapters"),
            (UUID_MISSING, "text", "M", "repo missing localize"),
        ],
    )

    result = prepare_reviewed_localize_migration(
        localize_po_path=localize_po,
        repo_po_path=repo_po,
        tree_dir=tree_dir,
        chapters=("0004", "0005", "0006"),
        out_po_path=out_po,
        report_path=report_path,
    )

    output_states = parse_po_entry_states(out_po)
    assert output_states[(UUID_A, "text")].msgstr == "repo reviewed"
    assert output_states[(UUID_E, "text")].msgstr == "網站舊"
    assert result.total_reviewed_keys == 5
    assert result.included_entries == 1
    assert result.already_current == 1
    assert result.skipped_empty_repo == 1
    assert result.source_mismatches == 1
    assert result.missing_localize_entries == 1
    report = json.loads(report_path.read_text(encoding="utf-8"))
    decisions = {item["uuid"]: item["decision"] for item in report["decisions"]}
    assert decisions[UUID_A] == "include"
    assert decisions[UUID_B] == "already-current"
    assert decisions[UUID_C] == "empty-repo"
    assert decisions[UUID_D] == "source-mismatch"
    assert decisions[UUID_MISSING] == "missing-localize-entry"


def test_derive_upload_url_from_localize_download_url() -> None:
    """Verify Localize download URLs map to Weblate upload API URLs."""

    assert derive_upload_url(
        "https://localize.ds-wizard.org/download/knowledge-models/"
        "common-dsw-knowledge-model/zh_Hant/"
    ) == (
        "https://localize.ds-wizard.org/api/translations/knowledge-models/"
        "common-dsw-knowledge-model/zh_Hant/file/"
    )


def test_build_multipart_body_contains_method_and_file(workspace: Path) -> None:
    """Verify upload request bodies include Weblate method and PO payload."""

    po_path = workspace / "migration.po"
    po_path.write_text('msgid ""\nmsgstr ""\n', encoding="utf-8")

    body, content_type = build_multipart_body(
        fields={"method": "translate"},
        file_field="file",
        file_path=po_path,
    )

    assert content_type.startswith("multipart/form-data; boundary=")
    assert b'name="method"' in body
    assert b"translate" in body
    assert b'name="file"; filename="migration.po"' in body
    assert b'msgid ""' in body


def test_cli_can_prepare_migration_without_repository_config(
    workspace: Path,
    monkeypatch,
    capsys,
) -> None:
    """Verify first-time migrations can use explicit paths before config exists."""

    localize_po = workspace / "builds" / "localize.po"
    repo_po = workspace / "builds" / "final_translated.po"
    out_po = workspace / "reviews" / "migration.po"
    report_path = workspace / "reviews" / "report.json"
    tree_dir = workspace / "tree"
    write_uuid(tree_dir, "0004", UUID_A)
    localize_po.parent.mkdir(parents=True)
    repo_po.parent.mkdir(parents=True, exist_ok=True)

    write_po(localize_po, [(UUID_A, "text", "A", "網站舊")])
    write_po(repo_po, [(UUID_A, "text", "A", "repo reviewed")])

    monkeypatch.chdir(workspace)
    monkeypatch.setattr(
        "sys.argv",
        [
            "migrate_reviewed_to_localize.py",
            "--chapters",
            "0004",
            "--localize-po",
            str(localize_po),
            "--repo-po",
            str(repo_po),
            "--tree-dir",
            str(tree_dir),
            "--out-po",
            str(out_po),
            "--report",
            str(report_path),
        ],
    )

    migrate_reviewed_to_localize_main()

    output = capsys.readouterr().out
    assert "Included entries : 1" in output
    assert parse_po_entry_states(out_po)[(UUID_A, "text")].msgstr == "repo reviewed"
