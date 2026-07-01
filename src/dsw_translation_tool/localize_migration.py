"""One-shot migration of reviewed repository translations to Localize/Weblate."""

from __future__ import annotations

import json
import mimetypes
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path

from .localize_merge import (
    PoEntryState,
    PoKey,
    collect_protected_po_keys,
    parse_po_entry_states,
)
from .po import PoCatalogWriter


class LocalizeMigrationError(RuntimeError):
    """Raised when a reviewed-translation migration cannot be completed."""


@dataclass(frozen=True)
class LocalizeMigrationDecision:
    """One reviewed-translation migration decision."""

    uuid: str
    field: str
    decision: str
    msgid: str
    localize: str
    repo: str
    included: bool


@dataclass(frozen=True)
class LocalizeUploadResult:
    """Summary of one Localize/Weblate upload request."""

    upload_url: str
    status_code: int
    response_preview: str


@dataclass(frozen=True)
class LocalizeMigrationResult:
    """Summary of one reviewed-translation migration preparation."""

    migration_po_path: Path
    report_path: Path
    chapters: tuple[str, ...]
    total_reviewed_keys: int
    included_entries: int
    already_current: int
    skipped_empty_repo: int
    source_mismatches: int
    missing_localize_entries: int
    upload: LocalizeUploadResult | None
    decisions: tuple[LocalizeMigrationDecision, ...]


def prepare_reviewed_localize_migration(
    *,
    localize_po_path: str | Path,
    repo_po_path: str | Path,
    tree_dir: str | Path,
    chapters: tuple[str, ...],
    out_po_path: str | Path,
    report_path: str | Path,
    po_writer: PoCatalogWriter | None = None,
) -> LocalizeMigrationResult:
    """Build a PO file containing reviewed repo translations for selected chapters.

    The generated PO uses the current Localize PO as its template and rewrites
    only reviewed chapter entries that have a non-empty repo translation,
    matching source text, and a different Localize translation. Uploading that
    PO with Weblate's ``translate`` method migrates reviewed repo text without
    replacing the whole component.
    """

    normalized_chapters = tuple(chapters)
    if not normalized_chapters:
        raise LocalizeMigrationError("At least one reviewed chapter must be provided")

    localize_po = Path(localize_po_path)
    repo_po = Path(repo_po_path)
    localize_entries = parse_po_entry_states(localize_po)
    repo_entries = parse_po_entry_states(repo_po)
    reviewed_keys = collect_protected_po_keys(
        tree_dir=Path(tree_dir),
        protected_chapters=normalized_chapters,
        repo_keys=frozenset(repo_entries),
    )

    translations_to_upload: dict[PoKey, str] = {}
    decisions: list[LocalizeMigrationDecision] = []
    for key in sorted(reviewed_keys):
        repo_state = repo_entries[key]
        localize_state = localize_entries.get(key)
        decision = decide_migration_entry(
            key=key,
            repo_state=repo_state,
            localize_state=localize_state,
        )
        decisions.append(decision)
        if decision.included:
            translations_to_upload[key] = repo_state.msgstr

    writer = po_writer or PoCatalogWriter()
    out_po = Path(out_po_path)
    out_po.parent.mkdir(parents=True, exist_ok=True)
    out_po.write_text(
        writer.rewrite_translations(
            original_po_path=str(localize_po),
            translations_by_key=translations_to_upload,
            clear_fuzzy_for_keys=frozenset(translations_to_upload),
        ),
        encoding="utf-8",
    )

    result = build_migration_result(
        migration_po_path=out_po,
        report_path=Path(report_path),
        chapters=normalized_chapters,
        decisions=tuple(decisions),
        upload=None,
    )
    write_migration_report(result)
    return result


def prepare_consolidated_localize_migration(
    *,
    localize_po_path: str | Path,
    repo_po_path: str | Path,
    tree_dir: str | Path,
    chapters: tuple[str, ...],
    out_po_path: str | Path,
    report_path: str | Path,
    po_writer: PoCatalogWriter | None = None,
) -> LocalizeMigrationResult:
    """Build a PO using repo translations for reviewed chapters and blank fills.

    Policy:
    - reviewed chapters use the repository translation when source text matches
      and the repository translation is non-empty;
    - other chapters keep every non-empty Localize/Weblate translation;
    - other chapters use the repository translation only to fill an empty
      Localize/Weblate translation.
    """

    normalized_chapters = tuple(chapters)
    if not normalized_chapters:
        raise LocalizeMigrationError("At least one reviewed chapter must be provided")

    localize_po = Path(localize_po_path)
    repo_po = Path(repo_po_path)
    localize_entries = parse_po_entry_states(localize_po)
    repo_entries = parse_po_entry_states(repo_po)
    reviewed_keys = collect_protected_po_keys(
        tree_dir=Path(tree_dir),
        protected_chapters=normalized_chapters,
        repo_keys=frozenset(repo_entries),
    )

    translations_to_upload: dict[PoKey, str] = {}
    decisions: list[LocalizeMigrationDecision] = []
    for key in sorted(reviewed_keys):
        repo_state = repo_entries[key]
        localize_state = localize_entries.get(key)
        decision = decide_migration_entry(
            key=key,
            repo_state=repo_state,
            localize_state=localize_state,
        )
        decisions.append(decision)
        if decision.included:
            translations_to_upload[key] = repo_state.msgstr

    for key in sorted(set(localize_entries) - reviewed_keys):
        localize_state = localize_entries[key]
        repo_state = repo_entries.get(key)
        decision = decide_localize_first_entry(
            key=key,
            repo_state=repo_state,
            localize_state=localize_state,
        )
        decisions.append(decision)
        if decision.included and repo_state is not None:
            translations_to_upload[key] = repo_state.msgstr

    writer = po_writer or PoCatalogWriter()
    out_po = Path(out_po_path)
    out_po.parent.mkdir(parents=True, exist_ok=True)
    out_po.write_text(
        writer.rewrite_translations(
            original_po_path=str(localize_po),
            translations_by_key=translations_to_upload,
            clear_fuzzy_for_keys=frozenset(translations_to_upload),
        ),
        encoding="utf-8",
    )

    result = build_migration_result(
        migration_po_path=out_po,
        report_path=Path(report_path),
        chapters=normalized_chapters,
        decisions=tuple(decisions),
        upload=None,
        total_reviewed_keys=len(reviewed_keys),
    )
    write_migration_report(result)
    return result


def decide_migration_entry(
    *,
    key: PoKey,
    repo_state: PoEntryState,
    localize_state: PoEntryState | None,
) -> LocalizeMigrationDecision:
    """Decide whether one reviewed repo translation should be included."""

    uuid_value, field = key
    if localize_state is None:
        return make_decision(
            key=key,
            decision="missing-localize-entry",
            msgid=repo_state.msgid,
            localize="",
            repo=repo_state.msgstr,
            included=False,
        )
    if localize_state.msgid != repo_state.msgid:
        return make_decision(
            key=key,
            decision="source-mismatch",
            msgid=repo_state.msgid,
            localize=localize_state.msgstr,
            repo=repo_state.msgstr,
            included=False,
        )
    if not repo_state.msgstr:
        return make_decision(
            key=key,
            decision="empty-repo",
            msgid=repo_state.msgid,
            localize=localize_state.msgstr,
            repo=repo_state.msgstr,
            included=False,
        )
    if localize_state.msgstr == repo_state.msgstr:
        return make_decision(
            key=key,
            decision="already-current",
            msgid=repo_state.msgid,
            localize=localize_state.msgstr,
            repo=repo_state.msgstr,
            included=False,
        )
    return LocalizeMigrationDecision(
        uuid=uuid_value,
        field=field,
        decision="include",
        msgid=repo_state.msgid,
        localize=localize_state.msgstr,
        repo=repo_state.msgstr,
        included=True,
    )


def decide_localize_first_entry(
    *,
    key: PoKey,
    repo_state: PoEntryState | None,
    localize_state: PoEntryState,
) -> LocalizeMigrationDecision:
    """Decide whether one non-reviewed entry should fill a Localize blank."""

    if localize_state.msgstr:
        return make_decision(
            key=key,
            decision="keep-localize",
            msgid=localize_state.msgid,
            localize=localize_state.msgstr,
            repo=repo_state.msgstr if repo_state is not None else "",
            included=False,
        )
    if repo_state is None:
        return make_decision(
            key=key,
            decision="empty-localize-missing-repo",
            msgid=localize_state.msgid,
            localize=localize_state.msgstr,
            repo="",
            included=False,
        )
    if repo_state.msgid != localize_state.msgid:
        return make_decision(
            key=key,
            decision="source-mismatch",
            msgid=localize_state.msgid,
            localize=localize_state.msgstr,
            repo=repo_state.msgstr,
            included=False,
        )
    if not repo_state.msgstr:
        return make_decision(
            key=key,
            decision="empty-both",
            msgid=localize_state.msgid,
            localize=localize_state.msgstr,
            repo=repo_state.msgstr,
            included=False,
        )
    return make_decision(
        key=key,
        decision="fill-localize-blank",
        msgid=localize_state.msgid,
        localize=localize_state.msgstr,
        repo=repo_state.msgstr,
        included=True,
    )


def upload_migration_po(
    *,
    upload_url: str,
    token: str,
    po_path: str | Path,
    method: str = "translate",
    auth_scheme: str = "Token",
    extra_fields: dict[str, str] | None = None,
) -> LocalizeUploadResult:
    """Upload a prepared migration PO to Localize/Weblate."""

    if not token.strip():
        raise LocalizeMigrationError("Uploading to Localize requires a token")
    fields = {"method": method}
    if extra_fields:
        fields.update(extra_fields)
    body, content_type = build_multipart_body(
        fields=fields,
        file_field="file",
        file_path=Path(po_path),
    )
    request = urllib.request.Request(
        upload_url,
        data=body,
        headers={
            "Authorization": f"{auth_scheme} {token.strip()}",
            "Content-Type": content_type,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            payload = response.read(2048).decode("utf-8", errors="replace")
            return LocalizeUploadResult(
                upload_url=upload_url,
                status_code=response.status,
                response_preview=payload,
            )
    except urllib.error.HTTPError as error:
        payload = error.read(2048).decode("utf-8", errors="replace")
        raise LocalizeMigrationError(
            f"Localize upload failed with HTTP {error.code}: {payload}"
        ) from error
    except OSError as error:
        raise LocalizeMigrationError(f"Localize upload failed: {error}") from error


def derive_upload_url(download_url: str) -> str:
    """Derive a Weblate file-upload API URL from a public PO download URL."""

    parsed = urllib.parse.urlparse(download_url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 4 or parts[0] != "download":
        raise LocalizeMigrationError(
            "Unable to derive upload URL from Localize download URL; pass --upload-url"
        )
    _, project, component, language = parts
    upload_path = f"/api/translations/{project}/{component}/{language}/file/"
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, upload_path, "", "", ""),
    )


def build_multipart_body(
    *,
    fields: dict[str, str],
    file_field: str,
    file_path: Path,
) -> tuple[bytes, str]:
    """Build a multipart/form-data request body using the standard library."""

    boundary = f"----dsw-translation-{uuid.uuid4().hex}"
    body = bytearray()
    for name, value in fields.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8"))
        body.extend(value.encode("utf-8"))
        body.extend(b"\r\n")

    filename = file_path.name
    content_type = mimetypes.guess_type(filename)[0] or "text/x-gettext-translation"
    body.extend(f"--{boundary}\r\n".encode("utf-8"))
    body.extend(
        (f'Content-Disposition: form-data; name="{file_field}"; filename="{filename}"\r\n').encode(
            "utf-8"
        )
    )
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode("utf-8"))
    body.extend(file_path.read_bytes())
    body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode("utf-8"))
    return bytes(body), f"multipart/form-data; boundary={boundary}"


def build_migration_result(
    *,
    migration_po_path: Path,
    report_path: Path,
    chapters: tuple[str, ...],
    decisions: tuple[LocalizeMigrationDecision, ...],
    upload: LocalizeUploadResult | None,
    total_reviewed_keys: int | None = None,
) -> LocalizeMigrationResult:
    """Build a migration result and derived counters."""

    counts: dict[str, int] = {}
    for decision in decisions:
        counts[decision.decision] = counts.get(decision.decision, 0) + 1
    return LocalizeMigrationResult(
        migration_po_path=migration_po_path,
        report_path=report_path,
        chapters=chapters,
        total_reviewed_keys=total_reviewed_keys
        if total_reviewed_keys is not None
        else len(decisions),
        included_entries=sum(1 for decision in decisions if decision.included),
        already_current=counts.get("already-current", 0),
        skipped_empty_repo=counts.get("empty-repo", 0),
        source_mismatches=counts.get("source-mismatch", 0),
        missing_localize_entries=counts.get("missing-localize-entry", 0),
        upload=upload,
        decisions=decisions,
    )


def write_migration_report(result: LocalizeMigrationResult) -> None:
    """Write a reviewed migration result as JSON."""

    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = asdict(result)
    payload["migration_po_path"] = str(result.migration_po_path)
    payload["report_path"] = str(result.report_path)
    result.report_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def make_decision(
    *,
    key: PoKey,
    decision: str,
    msgid: str,
    localize: str,
    repo: str,
    included: bool,
) -> LocalizeMigrationDecision:
    """Build one migration decision."""

    uuid_value, field = key
    return LocalizeMigrationDecision(
        uuid=uuid_value,
        field=field,
        decision=decision,
        msgid=msgid,
        localize=localize,
        repo=repo,
        included=included,
    )
