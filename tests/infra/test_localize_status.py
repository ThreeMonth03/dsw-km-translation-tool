"""Tests for Localize/Weblate PO status reporting."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from dsw_translation_tool.localize_status import (
    build_localize_po_status_report,
    render_localize_po_status_markdown,
    write_localize_po_status_json,
)


def write_status_fixture_po(path: Path) -> None:
    """Write a small PO fixture covering filled, empty, and fuzzy blocks."""

    path.write_text(
        "\n".join(
            [
                "#: questions:11111111-1111-1111-1111-111111111111:title",
                'msgid "Filled"',
                'msgstr "已翻譯"',
                "",
                "#: questions:22222222-2222-2222-2222-222222222222:title",
                "#: answers:33333333-3333-3333-3333-333333333333:label",
                'msgid "Empty"',
                'msgstr ""',
                "",
                "#: choices:44444444-4444-4444-4444-444444444444:label",
                "#, fuzzy",
                'msgid "Review me"',
                'msgstr "需要檢查"',
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_localize_po_status_counts_blocks_and_references(workspace: Path) -> None:
    """Verify PO status metrics cover both block and reference counts."""

    po_path = workspace / "latest.po"
    write_status_fixture_po(po_path)

    report = build_localize_po_status_report(po_path)

    assert report.message_blocks == 3
    assert report.references == 4
    assert report.filled_blocks == 2
    assert report.empty_blocks == 1
    assert report.fuzzy_blocks == 1
    assert report.accepted_blocks == 1
    assert report.filled_references == 2
    assert report.empty_references == 2
    assert report.fuzzy_references == 1
    assert report.accepted_references == 1
    assert report.filled_percent == 66.67
    assert report.accepted_percent == 33.33


def test_localize_po_status_renders_markdown(workspace: Path) -> None:
    """Verify the Markdown report contains maintainer-facing status rows."""

    po_path = workspace / "latest.po"
    write_status_fixture_po(po_path)

    markdown = render_localize_po_status_markdown(build_localize_po_status_report(po_path))

    assert "## Localize/Weblate PO Status" in markdown
    assert "| Filled msgstr | 2 | 2 |" in markdown
    assert "| Empty msgstr | 1 | 2 |" in markdown
    assert "| Fuzzy / needs editing | 1 | 1 |" in markdown
    assert "| Filled and not fuzzy blocks | 33.33% |" in markdown


def test_localize_po_status_writes_json(workspace: Path) -> None:
    """Verify JSON output is stable and machine readable."""

    po_path = workspace / "latest.po"
    json_path = workspace / "status.json"
    write_status_fixture_po(po_path)

    report = build_localize_po_status_report(po_path)
    write_localize_po_status_json(report, json_path)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["message_blocks"] == 3
    assert data["references"] == 4
    assert data["filledPercent"] == 66.67
    assert data["acceptedPercent"] == 33.33


def test_report_localize_status_cli_writes_outputs(
    repo_root: Path,
    workspace: Path,
) -> None:
    """Verify the status CLI writes both JSON and Markdown outputs."""

    po_path = workspace / "latest.po"
    json_path = workspace / "status.json"
    summary_path = workspace / "summary.md"
    write_status_fixture_po(po_path)

    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "src" / "report_localize_status.py"),
            "--po",
            str(po_path),
            "--json-out",
            str(json_path),
            "--summary",
            str(summary_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "## Localize/Weblate PO Status" in result.stdout
    assert json_path.exists()
    assert "## Localize/Weblate PO Status" in summary_path.read_text(encoding="utf-8")
