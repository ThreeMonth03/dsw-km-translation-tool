# Sync Policy

This repository uses a Weblate-first synchronization policy.

## Authority

The latest translation state is governed by Localize/Weblate.

GitHub mirrors the website state. Direct changes to `tree/` outside the
reviewed pull-request path may be overwritten by the next sync.

## Direction

Scheduled automation is one-way:

```text
Localize/Weblate -> GitHub
```

The sync writer:

1. Downloads the latest Weblate PO.
2. Refreshes `tree/` from that PO.
3. Rebuilds `builds/final_translated.po`.
4. Validates the PO for DSW's native Knowledge Model locale import.
5. Refreshes review outputs.
6. Commits and pushes only when tracked artifacts changed.

Scheduled sync does not upload translations to Weblate.

Reviewed GitHub translation pull requests use a guarded reverse path:

```text
GitHub PR -> reviewed merge -> Weblate import -> Weblate-to-Git sync
```

Only entries that are safe against the current Weblate state are imported. If
GitHub and Weblate changed the same entry differently, the import workflow
fails and writes a conflict report. It does not use timestamps or a
last-writer-wins rule to choose between reviewers. Read-only pull-request and
post-merge checks also reject translations that do not preserve source
Markdown formatting and boundary whitespace. Canonical
`tree/shared_blocks/*/context.md` edits are expanded automatically for reporting
and building; competing field edits are rejected. After upload, the workflow
downloads Weblate again and fails unless every expected entry is present.

## Writer Workflows

- `localize_auto_sync.yml` commits directly to the tracking branch on scheduled
  runs when tracked files changed.
- `github_translation_import.yml` imports accepted GitHub translation edits to
  Weblate after merge, then syncs Weblate back to Git whenever translation edits
  were detected, including edits already present in Weblate.
- `km_version_auto_update.yml` updates to a newer published KM only after the
  bundle and Weblate mirror have been downloaded, the translation tree and
  locale PO have been rebuilt, and validation and alignment checks pass.

These writer workflows share a concurrency group and do not cancel an active
import, sync, or KM update when a later run starts.

## Read-Only Reports

- `validate_translation_config.yml` validates repository configuration and
  scaffold state. On pull requests, it also compares the exact head and base
  commits and uploads the GitHub translation report and a native PO preview.
  Generated PO/review changes need not be committed by translators.
- `localize_status_report.yml` reports empty entries, review-state counts, and
  Weblate `has:check` items.
- `localize_alignment_report.yml` verifies that Weblate PO, checked-in PO,
  `tree/`, and the final PO match.

## Translation Quality States

Resolve review-marked strings in Weblate. Git mirrors those states in reports.

## Releases

`release.yml` rebuilds a tagged, clean checkout with its pinned tooling commit.
It requires generated files to be reproducible before publishing a PO,
checksums, and provenance. A translation revision is independent of the source
KM version; see [the release procedure](maintenance-runbook.md#publishing-a-locale).
