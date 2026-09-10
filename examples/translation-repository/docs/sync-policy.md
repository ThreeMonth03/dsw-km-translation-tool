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
4. Rebuilds `builds/final_translated.km`.
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
`tree/shared_blocks/*/context.md` edits must be expanded locally into every
referenced `translation.md` field and committed to the pull-request branch.
The reporter rejects any remaining inconsistency. After upload, the workflow
downloads Weblate again and fails unless every expected entry is present.

## Writer Workflows

- `localize_auto_sync.yml` commits directly to the tracking branch on scheduled
  runs when tracked files changed.
- `github_translation_import.yml` imports accepted GitHub translation edits to
  Weblate after merge, then syncs Weblate back to Git when an upload occurred.
- `km_version_auto_update.yml` updates to a newer published KM only after the
  bundle download, Weblate mirror, rebuild, validation, and alignment checks
  pass.

These writer workflows share a concurrency group and do not cancel an active
import, sync, or KM update when a later run starts.

## Read-Only Reports

- `validate_translation_config.yml` validates repository configuration and
  scaffold state. On pull requests, it also compares the exact head and base
  commits and uploads the GitHub translation report.
- `localize_status_report.yml` reports empty entries, review-state counts, and
  Weblate `has:check` items.
- `localize_alignment_report.yml` verifies that Weblate PO, checked-in PO,
  `tree/`, final PO, and final KM match.

## Translation Quality States

Resolve review-marked strings in Weblate. Git mirrors those states in reports.
