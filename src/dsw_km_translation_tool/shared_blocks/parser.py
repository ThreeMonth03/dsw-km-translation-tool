"""Parser for canonical shared-block translation files."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

from ..constants import SHARED_BLOCK_CONTEXT_FILENAME

SHARED_KEY_RE = re.compile(r"^- Shared Key: `(?P<key>[^`]*)`$")

GroupKey = tuple[tuple[str, str], ...]


class SharedBlocksCatalogParser:
    """Read canonical translations from the generated shared-block directory."""

    def __init__(self, target_lang: str = "zh_Hant"):
        self.target_lang = target_lang

    def parse(
        self,
        shared_blocks_root: str | Path,
        expected_group_keys: set[GroupKey] | None = None,
    ) -> dict[GroupKey, str]:
        """Return translations keyed by their structured shared-group key."""

        root = Path(shared_blocks_root)
        if expected_group_keys is not None:
            return {
                group_key: self._parse_expected_translation(root, group_key)
                for group_key in sorted(expected_group_keys)
            }

        translations: dict[GroupKey, str] = {}
        for context_path in sorted(root.glob(f"*/{SHARED_BLOCK_CONTEXT_FILENAME}")):
            group_key = self._parse_group_key(context_path)
            translations[group_key] = self._parse_translation(context_path)
        return translations

    def _parse_expected_translation(self, root: Path, group_key: GroupKey) -> str:
        context_path = self.group_context_path(root, group_key)
        if not context_path.exists():
            raise ValueError(f"Missing shared-block context file.\nFile: {context_path}")
        return self._parse_translation(context_path)

    def _parse_group_key(self, context_path: Path) -> GroupKey:
        for line in context_path.read_text(encoding="utf-8").splitlines():
            match = SHARED_KEY_RE.fullmatch(line.strip())
            if match is not None:
                return self.deserialize_group_key(match.group("key"))
        raise ValueError(
            "Missing shared-block key metadata in generated context markdown.\n"
            f"File: {context_path}"
        )

    def _parse_translation(self, context_path: Path) -> str:
        lines = context_path.read_text(encoding="utf-8").splitlines()
        headings = {
            f"### Translation ({self.target_lang})",
            f"### Current Translation ({self.target_lang})",
        }
        for index, line in enumerate(lines):
            if line.strip() not in headings:
                continue
            block_start = self._skip_blank_lines(lines, index + 1)
            return self._read_fenced_block(lines, block_start, context_path)
        raise ValueError(
            "Missing editable translation block in shared-block context markdown.\n"
            f"File: {context_path}"
        )

    @staticmethod
    def serialize_group_key(group_key: GroupKey) -> str:
        """Serialize one group key into markdown metadata."""

        return " | ".join(f"{entity_uuid}:{field}" for entity_uuid, field in group_key)

    @classmethod
    def stable_group_id(cls, group_key: GroupKey) -> str:
        """Return a deterministic filesystem-safe identifier for one group."""

        serialized_key = cls.serialize_group_key(group_key)
        return hashlib.sha1(serialized_key.encode("utf-8")).hexdigest()[:12]

    @classmethod
    def group_dir_path(cls, shared_blocks_root: Path, group_key: GroupKey) -> Path:
        """Return the canonical directory for one shared-block group."""

        return shared_blocks_root / cls.stable_group_id(group_key)

    @classmethod
    def group_context_path(
        cls,
        shared_blocks_root: Path,
        group_key: GroupKey,
    ) -> Path:
        """Return the generated context markdown path for one group."""

        return cls.group_dir_path(shared_blocks_root, group_key) / (SHARED_BLOCK_CONTEXT_FILENAME)

    @staticmethod
    def deserialize_group_key(serialized_key: str) -> GroupKey:
        """Parse one serialized group key from markdown metadata."""

        if not serialized_key.strip():
            raise ValueError("Shared-block key is empty.")
        group_key: list[tuple[str, str]] = []
        for token in serialized_key.split(" | "):
            try:
                entity_uuid, field = token.split(":", 1)
            except ValueError as error:
                raise ValueError(f"Malformed shared-block key token: {token!r}") from error
            if not entity_uuid or not field:
                raise ValueError(f"Malformed shared-block key token: {token!r}")
            group_key.append((entity_uuid, field))
        return tuple(group_key)

    @staticmethod
    def _skip_blank_lines(lines: list[str], index: int) -> int:
        while index < len(lines) and not lines[index].strip():
            index += 1
        return index

    @staticmethod
    def _read_fenced_block(lines: list[str], index: int, path: Path) -> str:
        if index >= len(lines) or lines[index].strip() != "~~~text":
            raise ValueError(
                f"{path}: line {index + 1}: Missing opening fence for "
                "shared-block translation block."
            )

        block_lines: list[str] = []
        for line_number, line in enumerate(lines[index + 1 :], start=index + 2):
            if line.strip() == "~~~":
                return "\n".join(block_lines)
            block_lines.append(line)
        raise ValueError(
            f"{path}: line {len(lines)}: Missing closing fence for shared-block translation block."
        )
