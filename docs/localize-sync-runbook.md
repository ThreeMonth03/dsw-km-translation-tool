# Localize Sync Runbook

Use this runbook for production zh-Hant sync.

## Operating Model

The latest translation state is governed by Localize/Weblate. The Git
translation repository mirrors that state so maintainers can review generated
trees, publish a native DSW locale PO, and keep reproducible history.

Normal scheduled automation is one-way:

```text
Localize/Weblate -> GitHub translation repository
```

GitHub pull requests can also contribute translation edits. That path is
guarded:

```text
GitHub PR -> reviewed merge -> Weblate import -> Weblate-to-Git sync
```

## Secrets

Scheduled sync and alignment do not need Weblate write access. Configure
`LOCALIZE_API_TOKEN` in the production translation repository when enabling the
post-merge GitHub translation import workflow or when the read-only status
workflow should use authenticated Weblate checks. If it is not configured for
the status report, the check report uses anonymous access. See
[Security and Permissions](security-and-permissions.md).

## Scheduled Pull Sync

The external translation workflow should run:

- on a schedule, usually twice per day

The workflow runs the `dsw-km-sync-localize` command. That command:

1. Downloads the current Weblate PO and validates syntax, language, and native
   `entity/UUID/field` references. When a source KM exists, every referenced
   field and source string must match it before the snapshot is replaced.
2. Saves the validated snapshot to `sources/localize/zh_Hant/latest.po` and
   force-refreshes `tree/`.
3. Rebuilds `builds/final_translated.po`.
4. Validates the PO for native DSW Knowledge Model locale import.
5. Refreshes review outputs.
6. Commits and pushes only when tracked files changed.

Scheduled runs commit directly to `master` when repository policy allows it.
The writer does not run for pull requests.

Weblate and the Registry publish independently. If Weblate advances to a KM
that the Registry has not published, source validation stops the sync and
preserves the current snapshot and tree. Obtain the matching official KM before
resuming; do not change the PO header or remove unmatched messages to force a
pass. An empty catalog or unrecognized reference format is an error, not a
successful zero-message sync.

## Pull Request Validation

The read-only validation workflow compares the exact pull-request head with
the base commit recorded by the pull-request event. When a pull request edits
translation Markdown, it reports those changes and validates Weblate
conflicts, shared translations, and source Markdown formatting, including
leading and trailing whitespace. Invalid changes fail with a field-level
`github-translation-report` artifact.

The validation workflow has no secrets or write permission. It never updates
the pull-request branch. It resolves canonical shared-block edits for reporting,
then expands them in a temporary checkout to build a native PO preview.
Translators do not need to run commands or commit generated artifacts. Download
`native-locale-<head SHA>` from the Actions run to review the candidate PO.

For a local maintainer run against a checked-out translation repository, use:

```shell
make repo-sync TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

Set `TRANSLATION_REPO_DIR` as described in the
[Command Reference](command-reference.md). The target is
declared in the [`Makefile`][makefile].

## Read-Only Status and Alignment Reports

Use the status report workflow to inspect Weblate PO health without changing
Git or Weblate. It:

1. Checks out the translation repository.
2. Pulls the latest Weblate PO into the ephemeral workflow checkout.
3. Runs `dsw-km-report-localize-status`.
4. Writes a GitHub step summary and uploads
   `reviews/localize_status_report.json` and
   `reviews/localize_status_report.md` as artifacts.

The status report includes Weblate review-state counts from the PO export as
part of current translation health.

The same workflow can also run `dsw-km-report-weblate-checks` with the Weblate
query `has:check`. That catches website-side quality-check warnings that are
not always visible from PO state alone. The check report is diagnostic and uses
`--allow-api-failure` so Weblate API rate limits are captured in the report
while Git sync monitoring continues.

It requires only `contents: read`.

Use the alignment report workflow to verify output consistency without
changing Git or Weblate. It:

1. Downloads the latest Weblate PO into a temporary file.
2. Compares it with `sources/localize/zh_Hant/latest.po`.
3. Rebuilds `builds/final_translated.po` from `tree/`.
4. Validates the final PO against the configured KM and target language.
5. Uploads JSON, Markdown, and the generated PO comparison artifact.

The alignment report is allowed to fail when drift is detected. That failure
means a pull sync or tree rebuild should run before maintainers
trust the repository outputs. It also requires only `contents: read` and does
not change translations.

To run the same alignment check from your machine, use:

```shell
make repo-align TRANSLATION_REPO_DIR=/path/to/dsw-root-locales-zh_Hant
```

## PR Gate and Post-Merge Import

Before merge, the read-only pull-request check fails when the checked-in
Weblate state conflicts, source Markdown formatting is lost, or individual
field edits disagree with the canonical shared translation. After merge, the GitHub translation import workflow
downloads the latest Weblate PO and repeats all checks before any upload. This
post-merge validation catches Weblate changes that land after the PR check:

- GitHub changed an entry and Weblate still matches the base: import GitHub to
  Weblate.
- GitHub and Weblate already match: no import is needed.
- GitHub and Weblate changed the same entry differently: fail and write a
  conflict report.
- The translated Markdown lost source formatting: fail and write a format
  report.

After upload, the workflow downloads Weblate again and verifies every imported
entry. It fails if Weblate did not apply the expected content. A verified
import then runs normal Weblate-to-Git sync so the repository returns to being
a Weblate mirror. Detected edits already present in Weblate also trigger sync,
so stale generated fields are refreshed even when no upload is necessary.

Use forward commits for sync and workflow corrections on public branches.

## Conflict Policy

Normal sync is Weblate-first:

- Weblate entries that are ready for use win.
- Checked-in tree translations that differ from Weblate are replaced during
  force-refresh.
- Entries marked for review stay in Weblate for translators to resolve on the
  website.

GitHub translation import is not last-write-wins. It imports only entries that
are safe against the current Weblate state. Conflicts require human review.

Writer workflows use the same concurrency group with
`cancel-in-progress: false`. This prevents a later push or scheduled run from
cancelling an active writer job.

## KM Updates

The current production policy is latest-only. Use
[KM Update Runbook](km-update-runbook.md) when the DSW Registry publishes a new
Common DSW KM.

## Troubleshooting

- If sync commits nothing, Weblate and Git outputs are already aligned.
- If `translation-config.yml` fails validation, fix config before running sync.
- If tree parsing fails in CI, the writer may restore malformed files from the
  tracking branch once and retry.
- If Weblate has untranslated strings after sync, check whether they are empty,
  marked for review, or missing from the current KM source.

[makefile]: https://github.com/ThreeMonth03/dsw-km-translation-tool/blob/master/Makefile
