"""Helpers for GitHub Actions step summaries and outputs."""

from __future__ import annotations

from pathlib import Path


def append_markdown_summary(*, summary_path: Path | str | None, markdown_path: Path) -> None:
    """Append a generated Markdown report to a GitHub step summary file."""

    if summary_path is None:
        return
    with Path(summary_path).open("a", encoding="utf-8") as handle:
        handle.write(markdown_path.read_text(encoding="utf-8"))


def append_github_outputs(
    *,
    output_path: Path | str | None,
    values: dict[str, str | int | bool],
) -> None:
    """Append simple scalar values to ``$GITHUB_OUTPUT``."""

    if output_path is None:
        return
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        for name, value in values.items():
            handle.write(f"{name}={_format_output_value(value)}\n")


def _format_output_value(value: str | int | bool) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)
