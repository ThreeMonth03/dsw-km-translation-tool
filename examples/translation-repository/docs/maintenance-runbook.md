# Maintenance Runbook

Use this runbook for routine operation of a Common DSW Knowledge Model
translation repository.

## Daily Health Check

Check the latest scheduled Weblate-to-Git sync:

```shell
gh run list --workflow localize_auto_sync.yml --branch master --limit 5
```

Expected outcomes:

- Git was already aligned with Weblate.
- The workflow committed a Weblate sync update to `master`.

Check read-only reports:

```shell
gh run list --workflow localize_status_report.yml --branch master --limit 5
gh run list --workflow localize_alignment_report.yml --branch master --limit 5
gh run list --workflow validate_translation_config.yml --branch master --limit 5
```

Check KM auto-update:

```shell
gh run list --workflow km_version_auto_update.yml --branch master --limit 5
```

Check post-merge GitHub translation imports:

```shell
gh run list --workflow github_translation_import.yml --branch master --limit 5
```

## Manual Triggers

Trigger read-only reports:

```shell
gh workflow run localize_status_report.yml --ref master
gh workflow run localize_alignment_report.yml --ref master
gh workflow run validate_translation_config.yml --ref master
```

Trigger KM auto-update immediately:

```shell
gh workflow run km_version_auto_update.yml --ref master
```

Trigger a GitHub translation import for a known commit range:

```shell
gh workflow run github_translation_import.yml \
  --ref master \
  -f base_ref=BASE_COMMIT \
  -f head_ref=HEAD_COMMIT
```

Use this only after reviewed translation changes have landed in the tracking
branch.

## KM and Config Updates

Normal Weblate sync does not refresh `translation-config.yml`. The KM
auto-update workflow may update only the active KM version after
the newer KM bundle and Weblate mirror have been downloaded, the translation
tree and locale PO have been rebuilt, and validation and alignment checks pass.
Other settings, such as branch names, Weblate URLs, and tooling refs, are
maintained manually.

## Local Checks

Use the tooling repository for local checks:

```shell
TOOL_REPO_DIR=/path/to/dsw-km-translation-tool
TRANSLATION_REPO_DIR=/path/to/translation-repo

cd "$TOOL_REPO_DIR"
make install-dev
make repo-validate TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
make repo-scaffold-check TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
make repo-sync-shared-strings TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
make repo-align TRANSLATION_REPO_DIR="$TRANSLATION_REPO_DIR"
```

After the tooling repository changes its managed docs or workflow templates,
pin `tooling.ref` to the reviewed tool release's full commit SHA, check out that
commit locally, and refresh with `make repo-scaffold-sync`. It never changes
`translation-config.yml`, translation artifacts, or custom unmanaged files.

`make repo-sync-shared-strings` updates only canonical shared-block context
files and their referenced `tree/**/translation.md` fields. It does not commit
or push. Other writer targets such as `make repo-sync` and
`make repo-km-update` may commit and push from the checkout where they run. Use
them only from a disposable checkout or when you intentionally want a Git
update.

## Publishing a Locale

**Publish Native KM Locale** runs automatically after a successful Weblate sync,
GitHub translation import, or KM update. It compares usable, non-fuzzy translations
with the newest published locale. Documentation, PO headers, references, and new
empty entries do not trigger publication. Changed or removed usable translations do.

The workflow chooses the next unused `locale-<language>-r<revision>` tag. Revisions
advance independently of KM versions. It checks Weblate alignment, uses the full
SHA in `tooling.ref`, and rebuilds the tracking branch from committed inputs.
To retry, select **Run workflow**; an unchanged locale is a successful no-op.

The release workflow rebuilds and validates the PO and refuses
uncommitted generated changes. It publishes exactly three assets: the versioned
PO, `manifest.json`, and `SHA256SUMS`. The schema-2 manifest records the official
Weblate snapshot URL/header/checksum, context KM coordinates/checksum, released PO checksum,
translation commit, tooling commit, and message counts. Release notes appear in
the release page body. The configuration is available in Git at the recorded
translation commit. The successful release becomes **Latest**.
Before publishing, CI imports the PO in disposable official DSW containers and
checks language switching. Import or rendering errors block publication.
Official POT coverage gaps produce a warning and are listed in the
`native-dsw-review` artifact; an importable partial locale can still be released.

Download all assets and run `sha256sum -c SHA256SUMS` to verify them. DSW needs
only the PO. Use a new revision tag for corrections; do not replace existing
release assets.

## Troubleshooting

- Sync or KM update reports `not yet in Weblate`: check **GitHub Translation
  Import** and resolve its error before retrying. For multiple pending reviewed
  merges, use the manual import with the last mirrored commit as `base_ref` and
  the current tracking commit as `head_ref`. Source sync leaves pending edits
  untouched; do not force-refresh the tree to bypass the check.
- Sync created no commit: the rebuild found no tracked changes. Use the alignment
  report to confirm the repository still matches live Weblate.
- Alignment failed: download `localize-alignment-report` and compare the
  generated files with the checked-in files.
- Native locale validation failed: compare `sources/localize/*/latest.po` with
  `builds/final_translated.po`, then inspect the syntax or language error.
- Native DSW acceptance failed: download `native-dsw-review` for the result and
  browser failure screenshot. An incomplete coverage warning is separate from
  an import or rendering failure; inspect `coverage.md` for missing source text.
- Upstream source catalog differs: inspect `source-catalog/source-catalog.md`
  in `native-dsw-review`. `different` lists messages found only in either catalog.
  The official Weblate/POT remains authoritative; differences from an older KM
  do not block sync. See the [source policy](sync-policy.md#shared-source-catalog).
  An audit failure means its download or catalog validation failed.
- KM auto-update failed before downloading a bundle: check `DSW_REGISTRY_TOKEN`.
- KM auto-update failed after rebuilding the translation tree and locale PO:
  inspect the validation or alignment error.
- A translation PR failed Markdown validation: download the
  `github-translation-report` artifact and restore the missing emphasis, link,
  list, code, or boundary-whitespace formatting.
- A translation PR failed shared-block validation: keep the intended wording
  in the canonical shared Translation block and restore competing individual
  field edits. Use the reported file paths; no local build is required.
- A translation PR conflicts with Weblate: resolve the reported entries before
  merging; the workflow does not choose a winner automatically.
