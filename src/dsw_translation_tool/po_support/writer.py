"""PO rewriting services."""

from __future__ import annotations

from ..data_models import PoReference, PoReferenceSection
from .parser import PoCatalogParser
from .render import PoSectionRenderer
from .sections import PoReferenceSectionReader


class PoCatalogWriter:
    """Rewrite translations back into an original PO template.

    Args:
        section_reader: Optional section reader used to parse existing PO
            structure around each `msgstr` block.
        section_renderer: Optional section renderer used to serialize grouped
            translations back into PO text.
    """

    def __init__(
        self,
        section_reader: PoReferenceSectionReader | None = None,
        section_renderer: PoSectionRenderer | None = None,
    ):
        self.section_reader = section_reader or PoReferenceSectionReader()
        self.section_renderer = section_renderer or PoSectionRenderer()

    def rewrite_translations(
        self,
        original_po_path: str,
        translations_by_key: dict[tuple[str, str], str],
        clear_fuzzy_for_keys: frozenset[tuple[str, str]] | None = None,
    ) -> str:
        """Rewrite PO `msgstr` values using the provided translation map.

        Args:
            original_po_path: Original PO file used as the structural template.
            translations_by_key: Mapping from `(uuid, field)` to target text.
            clear_fuzzy_for_keys: Optional keys whose PO sections should have
                fuzzy flags removed when rendering.

        Returns:
            Rewritten PO content.
        """

        with open(original_po_path, "r", encoding="utf-8") as handle:
            lines = handle.readlines()
        output_lines: list[str] = []
        index = 0

        while index < len(lines):
            line = lines[index]
            if not line.startswith("#:"):
                output_lines.append(line)
                index += 1
                continue

            section, index = self.section_reader.parse_reference_section(lines, index)
            rewritten_lines, index = self.rewrite_section(
                lines=lines,
                start_index=index,
                section=section,
                translations_by_key=translations_by_key,
                clear_fuzzy_for_keys=clear_fuzzy_for_keys or frozenset(),
            )
            output_lines.extend(rewritten_lines)

        return "".join(output_lines)

    def rewrite_section(
        self,
        lines: list[str],
        start_index: int,
        section: PoReferenceSection,
        translations_by_key: dict[tuple[str, str], str],
        clear_fuzzy_for_keys: frozenset[tuple[str, str]] = frozenset(),
    ) -> tuple[list[str], int]:
        """Rewrite one PO section following its reference comments.

        Args:
            lines: Full PO file lines.
            start_index: First unread line after the reference section.
            section: Parsed section metadata.
            translations_by_key: Mapping from `(uuid, field)` to target text.
            clear_fuzzy_for_keys: Keys whose rendered sections should no
                longer carry a fuzzy marker.

        Returns:
            Rewritten output lines and next unread line index.
        """

        index = start_index
        output_lines: list[str] = []
        parsed_tokens = list(self.section_reader.parse_section_tokens(section.comment_tokens))
        extra_comment_lines, index = self.section_reader.collect_extra_comment_lines(
            lines,
            index,
        )
        if self.section_has_key(parsed_tokens, clear_fuzzy_for_keys):
            extra_comment_lines = self.clear_fuzzy_comment_lines(extra_comment_lines)
        msgid_lines, index = self.section_reader.collect_msgid_lines(lines, index)

        if index >= len(lines) or not lines[index].startswith("msgstr "):
            output_lines.extend(section.comment_lines)
            output_lines.extend(extra_comment_lines)
            output_lines.extend(msgid_lines)
            return output_lines, index

        current_msgstr, next_index = PoCatalogParser.parse_string_block(lines, index)
        if not parsed_tokens:
            output_lines.extend(section.comment_lines)
            output_lines.extend(extra_comment_lines)
            output_lines.extend(msgid_lines)
            output_lines.extend(lines[index:next_index])
            return output_lines, next_index

        grouped_tokens = self.section_renderer.group_tokens_by_translation(
            parsed_tokens=parsed_tokens,
            translations_by_key=translations_by_key,
            fallback_msgstr=current_msgstr,
        )
        output_lines.extend(
            self.section_renderer.render_grouped_tokens(
                grouped_tokens=grouped_tokens,
                parsed_tokens=parsed_tokens,
                comment_lines=section.comment_lines,
                extra_comment_lines=extra_comment_lines,
                msgid_lines=msgid_lines,
            )
        )
        return output_lines, next_index

    @staticmethod
    def section_has_key(
        parsed_tokens: list[PoReference],
        keys: frozenset[tuple[str, str]],
    ) -> bool:
        """Return whether a PO section references any selected key."""

        return any((token.uuid, token.field) in keys for token in parsed_tokens)

    @staticmethod
    def clear_fuzzy_comment_lines(lines: list[str]) -> list[str]:
        """Remove only fuzzy flags from PO extra comment lines."""

        cleaned: list[str] = []
        for line in lines:
            if line.startswith("#,") and "fuzzy" in [part.strip() for part in line[2:].split(",")]:
                flags = [part.strip() for part in line[2:].split(",") if part.strip()]
                remaining = [flag for flag in flags if flag != "fuzzy"]
                if remaining:
                    cleaned.append(f"#, {', '.join(remaining)}\n")
                continue
            cleaned.append(line)
        return cleaned
