"""Conservative three-way merge for Localize/Weblate PO updates."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

from .po import PoCatalogParser, PoCatalogWriter

PoKey = tuple[str, str]


@dataclass(frozen=True)
class LocalizeMergeDecision:
    """One non-trivial merge decision for a PO entry."""

    uuid: str
    field: str
    decision: str
    protected: bool
    msgid: str
    base: str
    latest: str
    repo: str
    result: str


@dataclass(frozen=True)
class LocalizeMergeResult:
    """Summary of one Localize PO merge."""

    output_po_path: Path
    report_path: Path
    total_entries: int
    changed_entries: int
    accepted_latest: int
    kept_repo: int
    conflicts: int
    protected_skips: int
    empty_overwrite_skips: int
    source_mismatches: int
    fuzzy_skips: int
    missing_localize_entries: int
    decisions: tuple[LocalizeMergeDecision, ...]


@dataclass(frozen=True)
class PoEntryState:
    """Parsed source and target state for one PO key."""

    msgid: str
    msgstr: str
    is_fuzzy: bool


class LocalizePoMerger:
    """Merge Localize PO updates into the repo-generated PO conservatively."""

    def __init__(
        self,
        *,
        po_writer: PoCatalogWriter | None = None,
    ) -> None:
        self.po_writer = po_writer or PoCatalogWriter()

    def merge(
        self,
        *,
        base_po_path: str | Path,
        latest_po_path: str | Path,
        repo_po_path: str | Path,
        out_po_path: str | Path,
        report_path: str | Path,
        tree_dir: str | Path | None = None,
        protected_chapters: tuple[str, ...] = (),
        conflict_policy: str = "conservative",
    ) -> LocalizeMergeResult:
        """Merge a pulled Localize PO into the repo-generated PO.

        Args:
            base_po_path: Last accepted Localize PO snapshot.
            latest_po_path: Latest pulled Localize PO snapshot.
            repo_po_path: PO generated from the repository translation tree.
            out_po_path: Output merged PO path.
            report_path: Output JSON report path.
            tree_dir: Optional translation tree used to identify protected
                chapter UUIDs.
            protected_chapters: Chapter numeric prefixes that should keep repo
                translations.
            conflict_policy: ``conservative`` keeps repository translations
                when both the repository and Weblate changed the same entry;
                ``latest-wins`` accepts non-fuzzy Weblate text as the source of
                truth. Protected chapter entries are still kept.

        Returns:
            Merge summary.
        """

        if conflict_policy not in {"conservative", "latest-wins"}:
            raise ValueError("conflict_policy must be either 'conservative' or 'latest-wins'")
        base_entries = parse_po_entry_states(base_po_path)
        latest_entries = parse_po_entry_states(latest_po_path)
        repo_entries = parse_po_entry_states(repo_po_path)
        protected_keys = collect_protected_po_keys(
            tree_dir=Path(tree_dir) if tree_dir is not None else None,
            protected_chapters=protected_chapters,
            repo_keys=frozenset(repo_entries),
        )

        merged_translations: dict[PoKey, str] = {}
        decisions: list[LocalizeMergeDecision] = []
        for key, repo_state in repo_entries.items():
            base_state = base_entries.get(key)
            latest_state = latest_entries.get(key)
            result_text, decision = self._merge_one(
                key=key,
                base_state=base_state,
                latest_state=latest_state,
                repo_state=repo_state,
                protected=key in protected_keys,
                conflict_policy=conflict_policy,
            )
            merged_translations[key] = result_text
            if decision.decision != "unchanged":
                decisions.append(decision)

        out_po_file = Path(out_po_path)
        out_po_file.parent.mkdir(parents=True, exist_ok=True)
        out_po_file.write_text(
            self.po_writer.rewrite_translations(
                original_po_path=str(repo_po_path),
                translations_by_key=merged_translations,
            ),
            encoding="utf-8",
        )

        result = self._build_result(
            output_po_path=out_po_file,
            report_path=Path(report_path),
            total_entries=len(repo_entries),
            decisions=tuple(decisions),
        )
        write_merge_report(result)
        return result

    @staticmethod
    def _merge_one(
        *,
        key: PoKey,
        base_state: PoEntryState | None,
        latest_state: PoEntryState | None,
        repo_state: PoEntryState,
        protected: bool,
        conflict_policy: str,
    ) -> tuple[str, LocalizeMergeDecision]:
        uuid, field = key
        if base_state is None or latest_state is None:
            return repo_state.msgstr, make_decision(
                key=key,
                decision="missing-localize-entry",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr if base_state else "",
                latest=latest_state.msgstr if latest_state else "",
                repo=repo_state.msgstr,
                result=repo_state.msgstr,
            )
        if not _source_texts_match(base_state, latest_state, repo_state):
            return repo_state.msgstr, make_decision(
                key=key,
                decision="source-mismatch",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=repo_state.msgstr,
            )
        if latest_state.msgstr == base_state.msgstr:
            return repo_state.msgstr, make_decision(
                key=key,
                decision="unchanged",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=repo_state.msgstr,
            )
        if latest_state.is_fuzzy:
            return repo_state.msgstr, make_decision(
                key=key,
                decision="latest-fuzzy",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=repo_state.msgstr,
            )
        if protected:
            return repo_state.msgstr, make_decision(
                key=key,
                decision="protected",
                protected=True,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=repo_state.msgstr,
            )
        if conflict_policy == "latest-wins":
            return latest_state.msgstr, make_decision(
                key=key,
                decision="accepted-latest",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=latest_state.msgstr,
            )
        if not latest_state.msgstr and repo_state.msgstr:
            return repo_state.msgstr, make_decision(
                key=key,
                decision="empty-overwrite-skip",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=repo_state.msgstr,
            )
        if repo_state.msgstr == base_state.msgstr:
            return latest_state.msgstr, make_decision(
                key=key,
                decision="accepted-latest",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=latest_state.msgstr,
            )
        if repo_state.msgstr == latest_state.msgstr:
            return repo_state.msgstr, make_decision(
                key=key,
                decision="unchanged",
                protected=protected,
                msgid=repo_state.msgid,
                base=base_state.msgstr,
                latest=latest_state.msgstr,
                repo=repo_state.msgstr,
                result=repo_state.msgstr,
            )
        return repo_state.msgstr, make_decision(
            key=key,
            decision="conflict",
            protected=protected,
            msgid=repo_state.msgid,
            base=base_state.msgstr,
            latest=latest_state.msgstr,
            repo=repo_state.msgstr,
            result=repo_state.msgstr,
        )

    @staticmethod
    def _build_result(
        *,
        output_po_path: Path,
        report_path: Path,
        total_entries: int,
        decisions: tuple[LocalizeMergeDecision, ...],
    ) -> LocalizeMergeResult:
        counts = Counter(decision.decision for decision in decisions)
        changed_entries = counts["accepted-latest"]
        return LocalizeMergeResult(
            output_po_path=output_po_path,
            report_path=report_path,
            total_entries=total_entries,
            changed_entries=changed_entries,
            accepted_latest=counts["accepted-latest"],
            kept_repo=len(decisions) - changed_entries,
            conflicts=counts["conflict"],
            protected_skips=counts["protected"],
            empty_overwrite_skips=counts["empty-overwrite-skip"],
            source_mismatches=counts["source-mismatch"],
            fuzzy_skips=counts["latest-fuzzy"],
            missing_localize_entries=counts["missing-localize-entry"],
            decisions=decisions,
        )


def parse_po_entry_states(po_path: str | Path) -> dict[PoKey, PoEntryState]:
    """Parse one PO file into entry states keyed by ``(uuid, field)``."""

    states: dict[PoKey, PoEntryState] = {}
    for block in PoCatalogParser(str(po_path)).parse_blocks():
        for reference in block.references:
            key = (reference.uuid, reference.field)
            next_state = PoEntryState(
                msgid=block.msgid,
                msgstr=block.msgstr,
                is_fuzzy=block.is_fuzzy,
            )
            existing = states.get(key)
            if existing is not None and existing != next_state:
                raise ValueError(
                    f"Duplicate PO key with conflicting values: {reference.uuid}:{reference.field}"
                )
            states[key] = next_state
    return states


def collect_protected_po_keys(
    *,
    tree_dir: Path | None,
    protected_chapters: tuple[str, ...],
    repo_keys: frozenset[PoKey],
) -> frozenset[PoKey]:
    """Collect PO keys whose UUIDs live below protected chapter paths."""

    if tree_dir is None or not protected_chapters or not tree_dir.exists():
        return frozenset()
    protected_prefixes = tuple(f"{chapter} " for chapter in protected_chapters)
    protected_uuids: set[str] = set()
    for uuid_file in tree_dir.rglob("_uuid.txt"):
        relative_parts = uuid_file.relative_to(tree_dir).parts[:-1]
        if any(part.startswith(protected_prefixes) for part in relative_parts):
            uuid_value = uuid_file.read_text(encoding="utf-8").strip()
            if uuid_value:
                protected_uuids.add(uuid_value)
    return frozenset(key for key in repo_keys if key[0] in protected_uuids)


def write_merge_report(result: LocalizeMergeResult) -> None:
    """Write a Localize merge result as JSON."""

    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    payload["output_po_path"] = str(result.output_po_path)
    payload["report_path"] = str(result.report_path)
    result.report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def make_decision(
    *,
    key: PoKey,
    decision: str,
    protected: bool,
    msgid: str,
    base: str,
    latest: str,
    repo: str,
    result: str,
) -> LocalizeMergeDecision:
    """Build one merge decision object."""

    uuid, field = key
    return LocalizeMergeDecision(
        uuid=uuid,
        field=field,
        decision=decision,
        protected=protected,
        msgid=msgid,
        base=base,
        latest=latest,
        repo=repo,
        result=result,
    )


def _source_texts_match(
    base_state: PoEntryState,
    latest_state: PoEntryState,
    repo_state: PoEntryState,
) -> bool:
    return base_state.msgid == latest_state.msgid == repo_state.msgid
