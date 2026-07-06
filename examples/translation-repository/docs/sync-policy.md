# Sync Policy

This repository uses a Weblate-first synchronization policy.

## Authority

The latest translation state is governed by Localize/Weblate.

GitHub mirrors the website state. Direct changes to `tree/` may be overwritten
by the next sync.

## Direction

Normal automation is one-way:

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

It does not upload translations to Weblate.

## Writer Workflows

- `localize_auto_sync.yml` commits directly to the tracking branch on scheduled
  runs when tracked files changed.
- Same-repository pull requests receive a sync commit before merge.
- `km_version_auto_update.yml` updates to a newer published KM only after the
  bundle download, Weblate mirror, rebuild, validation, and alignment checks
  pass.

## Read-Only Reports

- `localize_status_report.yml` reports empty entries, review-state counts, and
  Weblate `has:check` items.
- `localize_alignment_report.yml` verifies that Weblate PO, checked-in PO,
  `tree/`, final PO, and final KM match.

## Translation Quality States

Resolve review-marked strings in Weblate. Git mirrors those states in reports.
