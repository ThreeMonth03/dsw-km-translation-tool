"""Status reporting for Localize/Weblate PO snapshots."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from .po import PoCatalogParser


@dataclass(frozen=True)
class LocalizePoStatusReport:
    """Summary metrics for a Localize/Weblate PO snapshot.

    Args:
        po_path: Source PO path used for the report.
        message_blocks: Number of parsed translatable PO blocks.
        references: Number of KM references covered by those blocks.
        filled_blocks: Number of blocks with a non-empty `msgstr`.
        empty_blocks: Number of blocks with an empty `msgstr`.
        fuzzy_blocks: Number of blocks marked with the PO `fuzzy` flag.
        accepted_blocks: Number of filled blocks that are not fuzzy.
        filled_references: Number of KM references covered by filled blocks.
        empty_references: Number of KM references covered by empty blocks.
        fuzzy_references: Number of KM references covered by fuzzy blocks.
        accepted_references: Number of KM references covered by accepted blocks.
    """

    po_path: str
    message_blocks: int
    references: int
    filled_blocks: int
    empty_blocks: int
    fuzzy_blocks: int
    accepted_blocks: int
    filled_references: int
    empty_references: int
    fuzzy_references: int
    accepted_references: int

    @property
    def filled_percent(self) -> float:
        """Return the percentage of PO blocks that have a non-empty translation."""

        return _percentage(self.filled_blocks, self.message_blocks)

    @property
    def accepted_percent(self) -> float:
        """Return the percentage of PO blocks that are filled and not fuzzy."""

        return _percentage(self.accepted_blocks, self.message_blocks)

    @property
    def empty_percent(self) -> float:
        """Return the percentage of PO blocks with empty translations."""

        return _percentage(self.empty_blocks, self.message_blocks)

    @property
    def fuzzy_percent(self) -> float:
        """Return the percentage of PO blocks marked as fuzzy."""

        return _percentage(self.fuzzy_blocks, self.message_blocks)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-ready dictionary with counts and percentages."""

        data = asdict(self)
        data.update(
            {
                "filledPercent": self.filled_percent,
                "acceptedPercent": self.accepted_percent,
                "emptyPercent": self.empty_percent,
                "fuzzyPercent": self.fuzzy_percent,
            }
        )
        return data


def build_localize_po_status_report(po_path: Path | str) -> LocalizePoStatusReport:
    """Build status metrics from one Localize/Weblate PO snapshot.

    Args:
        po_path: Path to the PO file to inspect.

    Returns:
        Aggregated status report.
    """

    resolved_po_path = Path(po_path).resolve()
    blocks = PoCatalogParser(str(resolved_po_path)).parse_blocks()

    filled_blocks = 0
    empty_blocks = 0
    fuzzy_blocks = 0
    accepted_blocks = 0
    filled_references = 0
    empty_references = 0
    fuzzy_references = 0
    accepted_references = 0

    for block in blocks:
        reference_count = len(block.references)
        has_translation = bool(block.msgstr.strip())
        if has_translation:
            filled_blocks += 1
            filled_references += reference_count
        else:
            empty_blocks += 1
            empty_references += reference_count

        if block.is_fuzzy:
            fuzzy_blocks += 1
            fuzzy_references += reference_count
        elif has_translation:
            accepted_blocks += 1
            accepted_references += reference_count

    return LocalizePoStatusReport(
        po_path=str(resolved_po_path),
        message_blocks=len(blocks),
        references=sum(len(block.references) for block in blocks),
        filled_blocks=filled_blocks,
        empty_blocks=empty_blocks,
        fuzzy_blocks=fuzzy_blocks,
        accepted_blocks=accepted_blocks,
        filled_references=filled_references,
        empty_references=empty_references,
        fuzzy_references=fuzzy_references,
        accepted_references=accepted_references,
    )


def render_localize_po_status_markdown(report: LocalizePoStatusReport) -> str:
    """Render a Localize/Weblate PO status report as Markdown."""

    rows = [
        ("Total parsed PO messages", report.message_blocks, report.references),
        ("Filled msgstr", report.filled_blocks, report.filled_references),
        ("Empty msgstr", report.empty_blocks, report.empty_references),
        ("Fuzzy / needs editing", report.fuzzy_blocks, report.fuzzy_references),
        ("Filled and not fuzzy", report.accepted_blocks, report.accepted_references),
    ]
    lines = [
        "## Localize/Weblate PO Status",
        "",
        f"Source PO: `{report.po_path}`",
        "",
        "| Metric | Message blocks | KM references |",
        "| --- | ---: | ---: |",
    ]
    lines.extend(
        f"| {label} | {_format_int(blocks)} | {_format_int(references)} |"
        for label, blocks, references in rows
    )
    lines.extend(
        [
            "",
            "| Rate | Value |",
            "| --- | ---: |",
            f"| Filled blocks | {_format_percent(report.filled_percent)} |",
            f"| Empty blocks | {_format_percent(report.empty_percent)} |",
            f"| Fuzzy / needs editing blocks | {_format_percent(report.fuzzy_percent)} |",
            f"| Filled and not fuzzy blocks | {_format_percent(report.accepted_percent)} |",
            "",
            (
                "Note: Weblate exports entries that need editing through the PO "
                "`fuzzy` flag, so this report treats fuzzy entries as requiring "
                "human review."
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def write_localize_po_status_json(
    report: LocalizePoStatusReport,
    output_path: Path | str,
) -> None:
    """Write a status report to JSON."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(report.to_dict(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def write_localize_po_status_markdown(
    report: LocalizePoStatusReport,
    output_path: Path | str,
) -> None:
    """Append a status report to a Markdown file."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(render_localize_po_status_markdown(report))


def _percentage(part: int, total: int) -> float:
    """Return a rounded percentage, avoiding division by zero."""

    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def _format_int(value: int) -> str:
    """Format an integer for Markdown tables."""

    return f"{value:,}"


def _format_percent(value: float) -> str:
    """Format a percentage for Markdown tables."""

    return f"{value:.2f}%"
