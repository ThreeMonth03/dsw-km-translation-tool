# Maintenance Runbook

Use this runbook for routine operation of a Common DSW Knowledge Model
translation repository.

## Daily Health Check

Check the latest scheduled Weblate-to-Git sync:

```shell
gh run list --workflow localize_auto_sync.yml --branch master --limit 5
```

Healthy outcomes:

- Git was already aligned with Weblate.
- The workflow committed a Weblate sync update to `master`.

Check read-only reports:

```shell
gh run list --workflow localize_status_report.yml --branch master --limit 5
gh run list --workflow localize_alignment_report.yml --branch master --limit 5
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

Wait for the post-merge Weblate import and sync to finish and confirm the
alignment report passes. The release must be built from a clean tracking
branch, with `tooling.ref` pinned to a full commit SHA.

Use a tag of the form `km-<source KM version>-<language>-r<revision>`. For
example, the first and second translation releases for KM 2.7.0 are
`km-2.7.0-zh_Hant-r1` and `km-2.7.0-zh_Hant-r2`. Neither requires a new KM version.

```shell
git switch {{TRACKING_BRANCH}}
git pull --ff-only
TAG="km-<source-version>-{{TARGET_LANGUAGE}}-r<revision>"
git tag "$TAG"
git push origin "$TAG"
```

Replace the angle-bracket placeholders before running these commands.
**Publish Native KM Locale** rebuilds and validates the PO and refuses
uncommitted generated changes. It publishes the versioned PO, a stable PO
alias, `translation-config.yml`, `manifest.json`, release notes, and
`SHA256SUMS`. The manifest records the source KM checksum, translation commit,
tooling commit, and message counts. The successful release becomes **Latest**.
Before publishing, CI imports the PO in disposable official DSW containers and
checks language switching. Import or rendering errors block publication.
Official POT coverage gaps produce a warning and are listed in the
`native-dsw-review` artifact; an importable partial locale can still be released.

Download all assets and run `sha256sum -c SHA256SUMS` to verify them. DSW needs
only the PO. Use a new revision tag for corrections; do not replace existing
release assets.

## Troubleshooting

- Sync created no commit: Git is already aligned with Weblate.
- Alignment failed: download `localize-alignment-report` and compare the
  generated files with the checked-in files.
- Native locale validation failed: compare `sources/localize/*/latest.po` with
  `builds/final_translated.po`, then inspect the reported KM reference.
- Native DSW acceptance failed: download `native-dsw-review` for the result and
  browser failure screenshot. An incomplete coverage warning is separate from
  an import or rendering failure; inspect `coverage.md` for missing source text.
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
