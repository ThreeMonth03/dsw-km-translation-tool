"""PO parsing services."""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path
from typing import Iterable

from babel.messages.catalog import Catalog
from babel.messages.pofile import PoFileError, read_po

from ..constants import UUID_RE
from ..data_models import PoBlock, PoEntry, PoReference
from .codec import PoStringCodec


class PoCatalogError(ValueError):
    """Raised when a catalog cannot be represented as a native DSW translation tree."""


class PoCatalogParser:
    """Parse PO files into block and field-level structures.

    Args:
        po_path: Path to the PO file being parsed.
    """

    def __init__(self, po_path: str):
        self.po_path = po_path

    def parse_blocks(self) -> list[PoBlock]:
        """Parse the PO file into message blocks.

        Returns:
            Parsed PO blocks with grouped references.
        """

        return self.parse_text(Path(self.po_path).read_text(encoding="utf-8"))

    @classmethod
    def parse_text(cls, text: str, *, target_language: str | None = None) -> list[PoBlock]:
        """Read validated DSW message blocks from text."""
        return cls.parse_catalog(text, target_language=target_language)[1]

    @classmethod
    def parse_catalog(
        cls, text: str, *, target_language: str | None = None
    ) -> tuple[Catalog, list[PoBlock]]:
        """Validate syntax and every reference before accepting a downloaded catalog.

        Keep individual blocks intact: a local review can split a shared msgid
        into multiple translations, which a gettext catalog alone would merge.
        """
        try:
            catalog = read_po(StringIO(text), abort_invalid=True)
        except (PoFileError, ValueError) as error:
            raise PoCatalogError(f"Invalid gettext catalog: {error}") from error
        if target_language is not None and catalog.locale_identifier != target_language:
            raise PoCatalogError(f"PO Language header does not match {target_language!r}")
        if any(
            message.context is not None or not isinstance(message.id, str) for message in catalog
        ):
            raise PoCatalogError("DSW tree catalogs cannot contain contexts or plural messages")
        lines = StringIO(text, newline=None).readlines()
        index = 0
        pending_tokens: list[str] = []
        pending_is_fuzzy = False
        blocks: list[PoBlock] = []

        while index < len(lines):
            line = lines[index].rstrip("\n")
            if line.startswith("#"):
                pending_tokens, pending_is_fuzzy = cls.consume_comment_line(
                    line=line,
                    pending_tokens=pending_tokens,
                    pending_is_fuzzy=pending_is_fuzzy,
                )
                index += 1
                continue

            if line.startswith("msgid "):
                block, index = cls.parse_block(
                    lines=lines,
                    start_index=index,
                    pending_tokens=pending_tokens,
                    pending_is_fuzzy=pending_is_fuzzy,
                )
                if block is not None:
                    blocks.append(block)
                pending_tokens = []
                pending_is_fuzzy = False
                continue

            if not line:
                pending_tokens = []
                pending_is_fuzzy = False
            index += 1

        if not blocks:
            raise PoCatalogError("PO contains no translatable messages with DSW references")
        return catalog, blocks

    def parse_entries(self) -> list[PoEntry]:
        """Flatten parsed PO blocks into `(uuid, field)` entries.

        Returns:
            Flattened PO entries.
        """

        return self.entries_from_blocks(self.parse_blocks())

    @staticmethod
    def entries_from_blocks(blocks: Iterable[PoBlock]) -> list[PoEntry]:
        """Flatten already parsed blocks without rereading the catalog."""
        entries: list[PoEntry] = []
        for block in blocks:
            for reference in block.references:
                entries.append(
                    PoEntry(
                        prefix=reference.prefix,
                        uuid=reference.uuid,
                        field=reference.field,
                        comment=reference.comment,
                        msgid=block.msgid,
                        msgstr=block.msgstr,
                    )
                )
        return entries

    @staticmethod
    def parse_comment_token(token: str) -> PoReference | None:
        """Parse one PO `#:` token into a structured reference.

        Args:
            token: Raw PO reference token.

        Returns:
            Structured PO reference or `None` if the token is unrelated.
        """

        match = re.fullmatch(r"([^:/\s]+)([:/])([^:/\s]+)\2([^:/\s]+)", token)
        if match is None or not UUID_RE.fullmatch(match[3]):
            return None
        return PoReference(
            prefix=match[1],
            uuid=match[3],
            field=match[4],
            comment=token,
        )

    @staticmethod
    def parse_string_block(
        lines: list[str],
        start_index: int,
    ) -> tuple[str, int]:
        """Parse one `msgid` or `msgstr` block from the PO file.

        Args:
            lines: Full PO file lines.
            start_index: Start index of the string block.

        Returns:
            Parsed string value and the next unread line index.
        """

        line = lines[start_index].rstrip("\n")
        current = line.split(" ", 1)[1]
        parts: list[str] = []
        if current != '""':
            parts.append(PoStringCodec.decode(current[1:-1]))

        index = start_index + 1
        while index < len(lines):
            current_line = lines[index].rstrip("\n")
            if not current_line.startswith('"'):
                break
            parts.append(PoStringCodec.decode(current_line[1:-1]))
            index += 1
        return "".join(parts), index

    @staticmethod
    def consume_comment_line(
        line: str,
        pending_tokens: list[str],
        pending_is_fuzzy: bool,
    ) -> tuple[list[str], bool]:
        """Update parser state from one PO comment line.

        Args:
            line: Raw PO comment line.
            pending_tokens: Tokens accumulated so far for the current block.
            pending_is_fuzzy: Whether the current block is fuzzy so far.

        Returns:
            Updated token list and fuzzy flag.
        """

        if line.startswith("#:"):
            pending_tokens.extend(line[2:].strip().split())
        elif line.startswith("#,") and "fuzzy" in line:
            pending_is_fuzzy = True
        return pending_tokens, pending_is_fuzzy

    @classmethod
    def parse_block(
        cls,
        lines: list[str],
        start_index: int,
        pending_tokens: list[str],
        pending_is_fuzzy: bool,
    ) -> tuple[PoBlock | None, int]:
        """Parse one PO message block starting at `msgid`.

        Args:
            lines: Full PO file lines.
            start_index: Index of the `msgid` line.
            pending_tokens: Reference tokens accumulated before the block.
            pending_is_fuzzy: Fuzzy flag accumulated before the block.

        Returns:
            Parsed PO block, if any, and the next unread line index.
        """

        msgid, index = cls.parse_string_block(lines, start_index)
        if index < len(lines) and lines[index].startswith("msgstr "):
            msgstr, index = cls.parse_string_block(lines, index)
        else:
            msgstr = ""

        if not msgid:
            return None, index
        references = tuple(cls.parse_references(pending_tokens))
        if not references:
            raise PoCatalogError(f"PO message at line {start_index + 1} has no DSW references")

        return (
            PoBlock(
                references=references,
                msgid=msgid,
                msgstr=msgstr,
                is_fuzzy=pending_is_fuzzy,
            ),
            index,
        )

    @staticmethod
    def parse_references(tokens: list[str]) -> Iterable[PoReference]:
        """Parse every PO reference token; never silently discard unmapped messages.

        Args:
            tokens: Raw reference tokens collected from `#:` comments.

        Yields:
            Structured PO references.
        """

        for token in tokens:
            reference = PoCatalogParser.parse_comment_token(token)
            if reference is None:
                raise PoCatalogError(f"Invalid DSW reference {token!r}; expected entity/UUID/field")
            yield reference
