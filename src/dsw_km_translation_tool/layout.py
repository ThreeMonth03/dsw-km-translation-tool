"""Canonical path layout helpers for local translation workspaces."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DEFAULT_SOURCE_LANG = "en"
DEFAULT_TARGET_LANG = "zh_Hant"
DEFAULT_SOURCE_INPUTS_DIR = Path("tests/fixtures/source_inputs")
DEFAULT_PO_PATH = DEFAULT_SOURCE_INPUTS_DIR / "common_dsw_zh_Hant.po"
DEFAULT_MODEL_PATH = DEFAULT_SOURCE_INPUTS_DIR / "dsw_root_2.7.0.km"


@dataclass(frozen=True)
class TranslationOutputLayout:
    """Describe the default local output layout for one language.

    Args:
        output_root: Root directory containing local translation files.
        target_lang: Target language code for this layout.
    """

    output_root: Path
    target_lang: str = DEFAULT_TARGET_LANG

    @classmethod
    def for_target_lang(
        cls,
        target_lang: str = DEFAULT_TARGET_LANG,
    ) -> "TranslationOutputLayout":
        """Build the canonical output layout for one target language.

        Args:
            target_lang: Target language code.

        Returns:
            Layout instance rooted under `translation/<target_lang>`.
        """

        return cls(
            output_root=Path("translation") / target_lang,
            target_lang=target_lang,
        )

    @property
    def tree_dir(self) -> Path:
        """Return the translation tree directory."""

        return self.output_root / "tree"

    @property
    def outline_path(self) -> Path:
        """Return the outline markdown path inside the tree root."""

        return self.tree_dir / "outline.md"

    @property
    def shared_blocks_dir(self) -> Path:
        """Return the canonical shared-block directory inside the tree root."""

        return self.tree_dir / "shared_blocks"

    @property
    def shared_blocks_outline_path(self) -> Path:
        """Return the shared-block outline markdown path inside the tree root."""

        return self.tree_dir / "shared_blocks_outline.md"

    @property
    def final_po_path(self) -> Path:
        """Return the generated final PO path."""

        return self.output_root / "builds" / "final_translated.po"

    @property
    def final_km_path(self) -> Path:
        """Return the generated final KM path."""

        return self.output_root / "builds" / "final_translated.km"

    @property
    def diff_path(self) -> Path:
        """Return the generated review diff path."""

        return self.output_root / "reviews" / "final_translated.diff"

    @property
    def report_path(self) -> Path:
        """Return the generated validation report path."""

        return self.output_root / "reports" / "final_report.json"

    @property
    def tree_snapshot_path(self) -> Path:
        """Return the optional JSON tree snapshot path."""

        return self.output_root / "reports" / "tree_snapshot.json"

    @property
    def backup_root(self) -> Path:
        """Return the local backup root for this translation tree."""

        return self.output_root / "backups" / "tree"


DEFAULT_LAYOUT = TranslationOutputLayout.for_target_lang()
