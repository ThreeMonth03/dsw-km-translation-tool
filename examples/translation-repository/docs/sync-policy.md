# Sync Policy

This repository uses a Weblate-first synchronization policy.

## Authority

The latest translation state is governed by Localize/Weblate.

GitHub mirrors the website state. Submit changes to `tree/` through reviewed
pull requests. Source sync stops if edits have not yet reached Weblate; it
does not discard pending translations to restore alignment.

## Direction

Scheduled automation is one-way:

```text
Localize/Weblate -> GitHub
```

The sync writer:

1. Downloads the latest Weblate PO.
2. Checks Git edits against the saved and downloaded PO before refreshing `tree/`.
3. Rebuilds `builds/final_translated.po`.
4. Validates the PO for DSW's native Knowledge Model locale import.
5. Refreshes review outputs.
6. Commits and pushes only when tracked artifacts changed.

Scheduled sync does not upload translations to Weblate.

Weblate and the Registry publish independently. The official PO controls source
strings, translations and fuzzy flags even when the context KM is older. Sync
never waits for a matching KM. The KM supplies known hierarchy and browser tests;
catalog-only entities appear as root folders with no invented parents.

Upstream removals and coverage regressions are mirrored, not repaired locally.
Syntax, language, reproducibility and genuine import failures still block CI.
Differences from the context KM are reported without blocking sync or release.

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

A full tree refresh matching every current Weblate source and translation is
recognized as an upstream mirror, not a new translation submission. Upstream
removals and formatting are accepted; human proposals still receive conflict,
shared-block and Markdown checks.

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

Before replacing inputs, source sync and KM updates also check individual and
canonical shared translations against the saved Weblate snapshot. If Git has
an edit that the incoming PO does not contain, they stop without changing files.
This protects reviewed translations when an import fails or another writer runs
first. Complete or retry the import, resolving conflicts if necessary; see the
[maintenance runbook](maintenance-runbook.md#troubleshooting).

## Read-Only Reports

- `validate_translation_config.yml` validates repository configuration and
  scaffold state. On pull requests, it also compares the exact head and base
  commits and uploads the GitHub translation report and a native PO preview.
  Daily native verification also compares the official DSW POT with Weblate's
  shared repository POT. Generated PO/review changes need not be committed by translators.
- `localize_status_report.yml` reports empty entries, review-state counts, and
  Weblate `has:check` items.
- `localize_alignment_report.yml` verifies that Weblate PO, checked-in PO,
  `tree/`, and the final PO match.

## Shared Source Catalog

The official Weblate upstream repository owns the shared POT. This repository
does not maintain a separate canonical POT or upload new source strings.
The `native-dsw-review` artifact includes `source-catalog/source-catalog.md`,
the upstream POT snapshot and its exact commit. The audit checks the configured
KM version and reports missing or differing sources without changing any language.

Official maintainers decide extraction and POT-to-PO updates. An updated POT
alone does not ensure every language PO has been refreshed. Once official PO
exports include the changes, normal sync brings them here, including additions,
removals and review flags. We do not generate source entries ahead of upstream,
restore removed translations automatically or change other language catalogs.

## Translation Quality States

Resolve review-marked strings in Weblate. Git mirrors those states in reports.

## Releases

`release.yml` rebuilds a tagged, clean checkout with its pinned tooling commit.
It requires generated files to be reproducible before publishing a PO,
checksums, and provenance. A translation revision is independent of the source
KM version; see [the release procedure](maintenance-runbook.md#publishing-a-locale).
